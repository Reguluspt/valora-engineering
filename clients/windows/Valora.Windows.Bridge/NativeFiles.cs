using System.Security.Cryptography;

namespace Valora.Windows.Bridge;

public sealed record NativeFileInfo(string Name, string Extension, ulong SizeBytes);

public interface INativeFile
{
    Task<NativeFileInfo> InspectAsync(CancellationToken cancellation);
}

public interface INativePlatform : INativeCapabilityCatalog
{
    Task<INativeFile?> PickAsync(bool excel, BridgeGeneration generation);
    Task<bool> OpenAsync(INativeFile file, bool excel, BridgeGeneration generation);
    Task<bool?> SaveAsync(INativeFile artifact, string suggestedFilename, BridgeGeneration generation);
    Task<bool> NotifyAsync(string title, string body, BridgeGeneration generation);
    Task<bool> OpenExternalAsync(string url, BridgeGeneration generation);
}

public sealed class BridgeGeneration
{
    public const ulong FileLimit = 64 * 1024 * 1024;
    public const int HandleLimit = 32;
    private readonly object gate = new();
    private readonly CancellationTokenSource cancellation = new();
    private readonly Dictionary<string, (INativeFile File, NativeFileInfo Info, bool Artifact)> handles = new();
    private readonly Dictionary<string, TaskCompletionSource<string>> pending = new();
    private readonly HashSet<string> seen = new(StringComparer.Ordinal);
    private bool active = true;
    private bool interactive;
    internal bool Negotiated { get; set; }
    public CancellationToken Cancellation => cancellation.Token;
    public bool Active { get { lock (gate) { return active; } } }

    public T Start<T>(Func<T> operation)
    {
        lock (gate)
        {
            if (!active) { throw new NativeBridgeException(NativeError.BRIDGE_REVOKED); }
            return operation();
        }
    }

    internal TaskCompletionSource<string> Admit(string id, bool needsInteraction)
    {
        return Start(() =>
        {
            if (seen.Contains(id)) { throw new NativeBridgeException(NativeError.BAD_MESSAGE); }
            // Bound replay memory without allowing evicted IDs to repeat an OS action.
            if (pending.Count >= NativeProtocol.PendingLimit || seen.Count >= 4096 || needsInteraction && interactive)
            {
                throw new NativeBridgeException(NativeError.BUSY);
            }
            var completion = new TaskCompletionSource<string>(TaskCreationOptions.RunContinuationsAsynchronously);
            pending.Add(id, completion);
            seen.Add(id);
            if (needsInteraction) { interactive = true; }
            return completion;
        });
    }

    internal void Complete(string id, bool wasInteractive, string response)
    {
        lock (gate)
        {
            if (pending.Remove(id, out var completion)) { completion.TrySetResult(response); }
            if (wasInteractive) { interactive = false; }
        }
    }

    public void Revoke()
    {
        lock (gate)
        {
            if (!active) { return; }
            active = false;
            handles.Clear();
            interactive = false;
            foreach (var (id, completion) in pending) { completion.TrySetResult(NativeProtocol.Failure(id, NativeError.BRIDGE_REVOKED)); }
            pending.Clear();
            seen.Clear();
        }
        cancellation.Cancel();
    }

    public string Register(INativeFile file, NativeFileInfo info, bool artifact = false)
    {
        ValidateFile(info);
        return Start(() =>
        {
            if (handles.Count >= HandleLimit) { throw new NativeBridgeException(NativeError.BUSY); }
            var id = Convert.ToHexStringLower(RandomNumberGenerator.GetBytes(24));
            handles.Add(id, (file, info, artifact));
            return id;
        });
    }

    public INativeFile Resolve(string id, bool excel, bool artifact = false) => Start(() =>
    {
        if (!handles.TryGetValue(id, out var entry) || entry.Artifact != artifact)
        {
            throw new NativeBridgeException(NativeError.HANDLE_INVALID);
        }
        if (!artifact && (excel ? entry.Info.Extension is not (".xls" or ".xlsx") : entry.Info.Extension != ".docx"))
        {
            throw new NativeBridgeException(NativeError.TYPE_NOT_ALLOWED);
        }
        return entry.File;
    });

    public static void ValidateFile(NativeFileInfo info)
    {
        if (!NativeProtocol.SafeName(info.Name) || info.Extension is not (".xls" or ".xlsx" or ".docx") ||
            !info.Name.EndsWith(info.Extension, StringComparison.OrdinalIgnoreCase))
        {
            throw new NativeBridgeException(NativeError.TYPE_NOT_ALLOWED);
        }
        if (info.SizeBytes > FileLimit) { throw new NativeBridgeException(NativeError.SIZE_LIMIT); }
    }
}
