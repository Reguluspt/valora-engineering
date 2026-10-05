using System.Security.Cryptography;
using System.Text.Json;

namespace Valora.Windows.Bridge;

public sealed record NativeResourceResponse(int Status, string ContentType, Stream Content);

public sealed class NativeTransfers(BridgeGeneration owner, TimeProvider time)
{
    public const string Prefix = "/api/v1/.valora-native/v2/";
    public const ulong ProductLimit = 10 * 1024 * 1024;
    public const string XlsxMime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
    public const string XlsMime = "application/vnd.ms-excel";
    public const int OutstandingLimit = 8;
    private sealed record Ticket(string Kind, DateTimeOffset Expires, INativeReadableFile? File,
        NativeFileInfo? Info, JsonElement Metadata);
    private readonly Dictionary<string, Ticket> tickets = new(StringComparer.Ordinal);
    private readonly HashSet<Stream> responses = new();
    private int inFlight;

    public static void ValidateMetadata(JsonElement value)
    {
        NativeProtocol.Shape(value, "resultId", "resultVersion", "contentType", "extension", "sizeBytes", "sha256");
        if (!Guid.TryParseExact(NativeProtocol.Text(value, "resultId"), "D", out var id) ||
            id.ToString("D") != NativeProtocol.Text(value, "resultId") ||
            value.GetProperty("resultVersion").ValueKind != JsonValueKind.Number ||
            !value.GetProperty("resultVersion").TryGetInt32(out var version) || version < 1 ||
            NativeProtocol.Text(value, "contentType") != XlsxMime || NativeProtocol.Text(value, "extension") != ".xlsx" ||
            value.GetProperty("sizeBytes").ValueKind != JsonValueKind.Number ||
            !value.GetProperty("sizeBytes").TryGetUInt64(out var size) || size is 0 or > ProductLimit ||
            NativeProtocol.Text(value, "sha256") is not { Length: 64 } hash ||
            !hash.All(c => c is >= '0' and <= '9' or >= 'a' and <= 'f'))
        {
            throw new NativeBridgeException(NativeError.INVALID_ARGUMENT);
        }
    }

    public async Task<string> PrepareSelectedAsync(string handle)
    {
        if (owner.Resolve(handle, true) is not INativeReadableFile file)
        {
            throw new NativeBridgeException(NativeError.HANDLE_INVALID);
        }
        var info = await owner.Start(() => file.InspectAsync(owner.Cancellation));
        BridgeGeneration.ValidateFile(info);
        if (info.Extension is not (".xls" or ".xlsx")) { throw new NativeBridgeException(NativeError.TYPE_NOT_ALLOWED); }
        if (info.SizeBytes is 0 or > ProductLimit) { throw new NativeBridgeException(NativeError.SIZE_LIMIT); }
        return Add(new Ticket("selected", time.GetUtcNow().AddMinutes(1), file, info, default));
    }

    public string PrepareCapture(JsonElement metadata)
    {
        ValidateMetadata(metadata);
        return Add(new Ticket("capture", time.GetUtcNow().AddMinutes(1), null, null, metadata.Clone()));
    }

    private string Add(Ticket ticket) => owner.Start(() =>
    {
        foreach (var key in tickets.Where(pair => pair.Value.Expires <= time.GetUtcNow()).Select(pair => pair.Key).ToArray())
        {
            tickets.Remove(key);
        }
        if (tickets.Count + responses.Count + inFlight >= OutstandingLimit) { throw new NativeBridgeException(NativeError.BUSY); }
        var token = Convert.ToHexStringLower(RandomNumberGenerator.GetBytes(24));
        var url = Prefix + ticket.Kind + "/" + token;
        tickets.Add(url, ticket);
        return url;
    });

    public async Task<NativeResourceResponse> HandleAsync(string method, string relativeUrl, string contentType, Stream? body)
    {
        Ticket ticket;
        try
        {
            ticket = owner.Start(() =>
            {
                if (!owner.NegotiatedV2 || !tickets.Remove(relativeUrl, out var admitted) ||
                    admitted.Expires <= time.GetUtcNow() || inFlight + responses.Count >= OutstandingLimit)
                {
                    throw new NativeBridgeException(NativeError.HANDLE_INVALID);
                }
                inFlight++;
                return admitted;
            });
        }
        catch (NativeBridgeException) { return Reject(404); }
        try
        {
            if (ticket.Kind == "selected")
            {
                if (method != "GET" || body is not null) { return Reject(404); }
                var latest = await owner.Start(() => ticket.File!.InspectAsync(owner.Cancellation));
                if (latest.Extension != ticket.Info!.Extension || latest.SizeBytes != ticket.Info.SizeBytes ||
                    latest.Extension is not (".xls" or ".xlsx") || latest.SizeBytes is 0 or > ProductLimit)
                    return Reject(400);
                using var input = await owner.Start(() => ticket.File!.OpenReadAsync(owner.Cancellation));
                var bytes = await ReadBoundedAsync(input, ticket.Info!.SizeBytes);
                return Respond(200, ticket.Info.Extension == ".xlsx" ? XlsxMime : XlsMime, bytes);
            }
            if (method != "POST" || body is null || contentType != XlsxMime) { return Reject(404); }
            var metadata = ticket.Metadata;
            var content = await ReadBoundedAsync(body, metadata.GetProperty("sizeBytes").GetUInt64());
            var actual = Convert.ToHexStringLower(SHA256.HashData(content));
            if (actual != NativeProtocol.Text(metadata, "sha256")) { return Reject(400); }
            var artifact = await CapturedNativeArtifact.CreateAsync(content,
                metadata.GetProperty("resultVersion").GetInt32(), owner.Cancellation);
            string handle;
            try { handle = owner.Register(artifact, await artifact.InspectAsync(owner.Cancellation), true); }
            catch { artifact.Dispose(); throw; }
            return Respond(201, "application/json", JsonSerializer.SerializeToUtf8Bytes(new { artifactHandle = handle }));
        }
        catch (NativeBridgeException) { return Reject(400); }
        catch (OperationCanceledException) { return Reject(410); }
        catch (IOException) { return Reject(400); }
        finally { owner.Cleanup(() => inFlight--); }
    }

    private async Task<byte[]> ReadBoundedAsync(Stream input, ulong expectedSize)
    {
        using var output = new MemoryStream();
        var buffer = new byte[64 * 1024];
        int count;
        while ((count = await owner.Start(() => input.ReadAsync(buffer, owner.Cancellation).AsTask())) != 0)
        {
            if ((ulong)output.Length + (ulong)count > ProductLimit || (ulong)output.Length + (ulong)count > expectedSize)
            {
                throw new NativeBridgeException(NativeError.SIZE_LIMIT);
            }
            output.Write(buffer, 0, count);
        }
        if ((ulong)output.Length != expectedSize) { throw new NativeBridgeException(NativeError.INVALID_ARGUMENT); }
        return output.ToArray();
    }

    private NativeResourceResponse Respond(int status, string mime, byte[] bytes) => owner.Start(() =>
    {
        var stream = new GenerationResponseStream(owner, bytes, value => owner.Cleanup(() => responses.Remove(value)));
        responses.Add(stream);
        return new NativeResourceResponse(status, mime, stream);
    });

    public static NativeResourceResponse Reject(int status) => new(status, "text/plain", new MemoryStream());

    internal void Clear()
    {
        tickets.Clear();
        foreach (var response in responses.ToArray()) { response.Dispose(); }
        responses.Clear();
    }

    private sealed class GenerationResponseStream(BridgeGeneration generation, byte[] bytes, Action<Stream> released)
        : Stream
    {
        private readonly MemoryStream content = new(bytes, false);
        public override bool CanRead => content.CanRead;
        public override bool CanSeek => false;
        public override bool CanWrite => false;
        public override long Length => generation.Start(() => content.Length);
        public override long Position { get => generation.Start(() => content.Position); set => throw new NotSupportedException(); }
        public override void Flush() { }
        public override long Seek(long offset, SeekOrigin origin) => throw new NotSupportedException();
        public override void SetLength(long value) => throw new NotSupportedException();
        public override void Write(byte[] buffer, int offset, int count) => throw new NotSupportedException();
        public override int Read(byte[] buffer, int offset, int count) => generation.Start(() =>
        {
            var read = content.Read(buffer, offset, count);
            if (content.Position == content.Length) { Array.Clear(bytes); released(this); }
            return read;
        });
        public override int Read(Span<byte> buffer)
        {
            var copy = new byte[buffer.Length];
            var count = Read(copy, 0, copy.Length);
            copy.AsSpan(0, count).CopyTo(buffer);
            return count;
        }
        public override ValueTask<int> ReadAsync(Memory<byte> buffer, CancellationToken cancellationToken = default)
        {
            cancellationToken.ThrowIfCancellationRequested();
            return ValueTask.FromResult(Read(buffer.Span));
        }
        public override Task<int> ReadAsync(byte[] buffer, int offset, int count, CancellationToken cancellationToken)
        {
            cancellationToken.ThrowIfCancellationRequested();
            return Task.FromResult(Read(buffer, offset, count));
        }
        public override int ReadByte() => generation.Start(() =>
        {
            var read = content.ReadByte();
            if (content.Position == content.Length) { Array.Clear(bytes); released(this); }
            return read;
        });
        protected override void Dispose(bool disposing)
        {
            if (disposing) generation.Cleanup(() => { content.Dispose(); Array.Clear(bytes); released(this); });
            base.Dispose(disposing);
        }
    }
}

public sealed class CapturedNativeArtifact : INativeReadableFile, IDisposable
{
    private readonly FileStream retained;
    private readonly NativeFileInfo info;
    private bool disposed;
    private CapturedNativeArtifact(FileStream retained, int version, ulong size)
    {
        this.retained = retained;
        info = new NativeFileInfo($"result-v{version}.xlsx", ".xlsx", size);
    }
    public bool Retained => !disposed;

    internal static async Task<CapturedNativeArtifact> CreateAsync(byte[] bytes, int version, CancellationToken cancellation)
    {
        var directory = Path.Combine(Path.GetTempPath(), "Valora.WindowsClient.Artifacts");
        Directory.CreateDirectory(directory);
        if (File.GetAttributes(directory).HasFlag(FileAttributes.ReparsePoint)) { throw new IOException("Invalid artifact storage."); }
        var path = Path.Combine(directory, Guid.NewGuid().ToString("N") + ".xlsx");
        var file = new FileStream(path, FileMode.CreateNew, FileAccess.ReadWrite, FileShare.Read | FileShare.Delete,
            64 * 1024, FileOptions.Asynchronous | FileOptions.DeleteOnClose);
        try
        {
            await file.WriteAsync(bytes, cancellation);
            await file.FlushAsync(cancellation);
            return new CapturedNativeArtifact(file, version, (ulong)bytes.Length);
        }
        catch { file.Dispose(); throw; }
    }

    public Task<NativeFileInfo> InspectAsync(CancellationToken cancellation)
    {
        cancellation.ThrowIfCancellationRequested();
        ObjectDisposedException.ThrowIf(disposed, this);
        return Task.FromResult(info);
    }

    public Task<Stream> OpenReadAsync(CancellationToken cancellation)
    {
        cancellation.ThrowIfCancellationRequested();
        ObjectDisposedException.ThrowIf(disposed, this);
        return Task.FromResult<Stream>(new FileStream(retained.Name, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete));
    }

    public void Dispose() { if (disposed) { return; } disposed = true; retained.Dispose(); }
}
