using System.Security.Cryptography;
using System.Text.Json;
using Valora.Windows.Bridge;
using Xunit;

namespace Valora.Windows.Tests;

internal sealed class ReadableTestFile(byte[] bytes, string extension = ".xlsx", ulong? reportedSize = null) : INativeReadableFile
{
    public Task<NativeFileInfo> InspectAsync(CancellationToken cancellation) =>
        Task.FromResult(new NativeFileInfo("selection" + extension, extension, reportedSize ?? (ulong)bytes.Length));
    public Task<Stream> OpenReadAsync(CancellationToken cancellation) => Task.FromResult<Stream>(new MemoryStream(bytes, false));
}

public sealed class NativeTransferTests
{
    internal static string Request(string capability = "hello", object? payload = null) => JsonSerializer.Serialize(new
    {
        protocol = NativeProtocol.V2, type = "request", requestId = Guid.NewGuid().ToString("D"), capability, payload = payload ?? new { }
    });
    internal static JsonElement Metadata(byte[] bytes, string? hash = null, ulong? size = null, string? mime = null) =>
        JsonSerializer.SerializeToElement(new
        {
            resultId = "47fa8032-58e4-4860-9243-077f0cb13327", resultVersion = 3,
            contentType = mime ?? NativeTransfers.XlsxMime, extension = ".xlsx", sizeBytes = size ?? (ulong)bytes.Length,
            sha256 = hash ?? Convert.ToHexStringLower(SHA256.HashData(bytes))
        });
    private static async Task<NativeBridgeSession> Ready(TestNativePlatform platform)
    {
        platform.EnabledCapabilities = NativeProtocol.V2Capabilities;
        var session = new NativeBridgeSession(platform);
        session.Enable();
        var result = NativeBridgeTests.Parse(await session.DispatchAsync(Request())).GetProperty("result");
        Assert.Equal(new[] { "protocol", "capabilities", "clientCompatibility" }, result.EnumerateObject().Select(p => p.Name));
        Assert.Equal(1, result.GetProperty("clientCompatibility").GetInt32());
        return session;
    }
    private static async Task<string> Selected(NativeBridgeSession bridge)
    {
        var picked = NativeBridgeTests.Parse(await bridge.DispatchAsync(Request("pickExcelFile"))).GetProperty("result");
        var prepared = NativeBridgeTests.Parse(await bridge.DispatchAsync(Request("prepareSelectedFileTransfer",
            new { handle = picked.GetProperty("handle").GetString() })));
        Assert.DoesNotContain("path", prepared.GetRawText(), StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("base64", prepared.GetRawText(), StringComparison.OrdinalIgnoreCase);
        return prepared.GetProperty("result").GetProperty("url").GetString()!;
    }
    private static async Task<byte[]> Read(NativeResourceResponse response)
    {
        using var content = response.Content;
        using var output = new MemoryStream();
        await content.CopyToAsync(output);
        return output.ToArray();
    }

    [Fact]
    public async Task V1ShapeAndNewCapabilityIsolationRemainExact()
    {
        var bridge = await Ready(new TestNativePlatform());
        var hello = NativeBridgeTests.Parse(await bridge.DispatchAsync(NativeBridgeTests.Request())).GetProperty("result");
        Assert.Equal(new[] { "protocol", "capabilities" }, hello.EnumerateObject().Select(p => p.Name));
        Assert.DoesNotContain("prepareArtifactCapture", hello.GetRawText());
        NativeBridgeTests.Error(await bridge.DispatchAsync(NativeBridgeTests.Request("prepareArtifactCapture", Metadata([1]))),
            NativeError.CAPABILITY_UNAVAILABLE);
    }

    [Theory]
    [InlineData(".xls")]
    [InlineData(".xlsx")]
    public async Task ExcelTransferIsByteIdenticalOneShotAndRelative(string extension)
    {
        byte[] bytes = [0, 255, 1, 99];
        var bridge = await Ready(new TestNativePlatform { Selection = new ReadableTestFile(bytes, extension) });
        var url = await Selected(bridge);
        Assert.Matches("^/api/v1/\\.valora-native/v2/selected/[a-f0-9]{48}$", url);
        var response = await bridge.CurrentGeneration!.Transfers.HandleAsync("GET", url, "", null);
        Assert.Equal(200, response.Status);
        Assert.Equal(extension == ".xlsx" ? NativeTransfers.XlsxMime : NativeTransfers.XlsMime, response.ContentType);
        Assert.Equal(bytes, await Read(response));
        var replay = await bridge.CurrentGeneration.Transfers.HandleAsync("GET", url, "", null);
        Assert.Equal(404, replay.Status); Assert.Empty(await Read(replay));
    }

    [Fact]
    public async Task TenMiBBoundaryAndGrowingSelectionAreEnforcedWithoutChangingV1Ceiling()
    {
        var platform = new TestNativePlatform { Selection = new ReadableTestFile(new byte[NativeTransfers.ProductLimit]) };
        var bridge = await Ready(platform);
        var response = await bridge.CurrentGeneration!.Transfers.HandleAsync("GET", await Selected(bridge), "", null);
        Assert.Equal((int)NativeTransfers.ProductLimit, (await Read(response)).Length);
        platform.Selection = new ReadableTestFile([1], reportedSize: NativeTransfers.ProductLimit + 1);
        NativeBridgeTests.Error(await bridge.DispatchAsync(Request("pickExcelFile")), NativeError.SIZE_LIMIT);
        await bridge.DispatchAsync(NativeBridgeTests.Request());
        Assert.True(NativeBridgeTests.Parse(await bridge.DispatchAsync(NativeBridgeTests.Request("pickExcelFile"))).GetProperty("ok").GetBoolean());
        platform.Selection = new ReadableTestFile([1, 2], reportedSize: 1);
        var grown = await bridge.CurrentGeneration.Transfers.HandleAsync("GET", await Selected(bridge), "", null);
        Assert.Equal(400, grown.Status); Assert.Empty(await Read(grown));
        platform.Selection = new ReadableTestFile([1], ".docx");
        NativeBridgeTests.Error(await bridge.DispatchAsync(Request("pickExcelFile")), NativeError.TYPE_NOT_ALLOWED);
    }

    [Fact]
    public async Task WrongMethodConsumesTokenAndRevocationInvalidatesTokensAndStreams()
    {
        var bridge = await Ready(new TestNativePlatform { Selection = new ReadableTestFile([1]) });
        var owner = bridge.CurrentGeneration!;
        var url = await Selected(bridge);
        Assert.Equal(404, (await owner.Transfers.HandleAsync("POST", url, "", null)).Status);
        Assert.Equal(404, (await owner.Transfers.HandleAsync("GET", url, "", null)).Status);
        var pending = await Selected(bridge);
        var active = await owner.Transfers.HandleAsync("GET", await Selected(bridge), "", null);
        bridge.Revoke();
        Assert.Equal(404, (await owner.Transfers.HandleAsync("GET", pending, "", null)).Status);
        Assert.ThrowsAny<Exception>(() => active.Content.ReadByte());
        bridge.Enable();
        Assert.Equal(404, (await bridge.CurrentGeneration!.Transfers.HandleAsync("GET", pending, "", null)).Status);
        active.Content.Dispose();
    }

    private sealed class TestTime : TimeProvider
    {
        public DateTimeOffset Now = DateTimeOffset.UtcNow;
        public override DateTimeOffset GetUtcNow() => Now;
    }
    [Fact]
    public async Task CaptureTenMiBBoundaryRejectsLargerBodyAndRequiresV2Save()
    {
        var bridge = await Ready(new TestNativePlatform());
        var owner = bridge.CurrentGeneration!;
        var bytes = new byte[NativeTransfers.ProductLimit];
        var url = owner.Transfers.PrepareCapture(Metadata(bytes));
        var response = await owner.Transfers.HandleAsync("POST", url, NativeTransfers.XlsxMime, new MemoryStream(bytes));
        Assert.Equal(201, response.Status);
        var handle = JsonDocument.Parse(await Read(response)).RootElement.GetProperty("artifactHandle").GetString()!;
        await bridge.DispatchAsync(NativeBridgeTests.Request());
        NativeBridgeTests.Error(await bridge.DispatchAsync(NativeBridgeTests.Request("saveDownloadedArtifact",
            new { artifactHandle = handle, suggestedFilename = "result.xlsx" })), NativeError.BAD_PROTOCOL);
        var oversized = await owner.Transfers.HandleAsync("POST", owner.Transfers.PrepareCapture(Metadata(bytes)),
            NativeTransfers.XlsxMime, new MemoryStream(new byte[NativeTransfers.ProductLimit + 1]));
        Assert.Equal(400, oversized.Status); Assert.Empty(await Read(oversized));
        bridge.Revoke();
    }
    [Fact]
    public async Task ExpiryAndOutstandingBoundAreDeterministic()
    {
        var time = new TestTime();
        var bridge = new NativeBridgeSession(new TestNativePlatform { EnabledCapabilities = NativeProtocol.V2Capabilities }, time);
        bridge.Enable();
        await bridge.DispatchAsync(Request());
        var owner = bridge.CurrentGeneration!;
        var token = owner.Transfers.PrepareCapture(Metadata([1]));
        time.Now = time.Now.AddMinutes(1);
        Assert.Equal(404, (await owner.Transfers.HandleAsync("POST", token, NativeTransfers.XlsxMime, new MemoryStream([1]))).Status);
        for (var i = 0; i < NativeTransfers.OutstandingLimit; i++) owner.Transfers.PrepareCapture(Metadata([1]));
        Assert.Equal(NativeError.BUSY, Assert.Throws<NativeBridgeException>(() => owner.Transfers.PrepareCapture(Metadata([1]))).Code);
        owner.Revoke();
    }

    [Theory]
    [InlineData("hash")]
    [InlineData("size")]
    [InlineData("mime")]
    [InlineData("method")]
    public async Task CaptureRejectsWrongIntegrityAndNeverCreatesArtifact(string failure)
    {
        var bridge = await Ready(new TestNativePlatform());
        var owner = bridge.CurrentGeneration!;
        var metadata = Metadata([1, 2], failure == "hash" ? new string('0', 64) : null, failure == "size" ? 3UL : null);
        var url = owner.Transfers.PrepareCapture(metadata);
        var response = await owner.Transfers.HandleAsync(failure == "method" ? "GET" : "POST", url,
            failure == "mime" ? "application/octet-stream" : NativeTransfers.XlsxMime, new MemoryStream([1, 2]));
        Assert.True(response.Status >= 400); Assert.Empty(await Read(response));
        Assert.Equal(404, (await owner.Transfers.HandleAsync("POST", url, NativeTransfers.XlsxMime, new MemoryStream([1, 2]))).Status);
        Assert.Throws<NativeBridgeException>(() => owner.Transfers.PrepareCapture(Metadata([1], size: NativeTransfers.ProductLimit + 1)));
        Assert.Throws<NativeBridgeException>(() => owner.Transfers.PrepareCapture(Metadata([1], mime: "application/octet-stream")));
        bridge.Revoke();
    }

    [Theory]
    [InlineData(true)]
    [InlineData(false)]
    public async Task VerifiedCaptureSavesOrCancelsAndDeletesTempFile(bool saved)
    {
        var platform = new TestNativePlatform { SaveResult = saved };
        var bridge = await Ready(platform);
        var owner = bridge.CurrentGeneration!;
        var response = await owner.Transfers.HandleAsync("POST", owner.Transfers.PrepareCapture(Metadata([1, 2])),
            NativeTransfers.XlsxMime, new MemoryStream([1, 2]));
        Assert.Equal(201, response.Status);
        var handle = JsonDocument.Parse(await Read(response)).RootElement.GetProperty("artifactHandle").GetString()!;
        var artifact = Assert.IsType<CapturedNativeArtifact>(owner.Resolve(handle, false, true));
        // Test-only reflection proves deletion of the retained OS file without adding a production path API.
        var stream = (FileStream)typeof(CapturedNativeArtifact).GetField("retained",
            System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance)!.GetValue(artifact)!;
        var path = stream.Name;
        Assert.True(File.Exists(path));
        using (var input = await artifact.OpenReadAsync(default)) Assert.Equal([1, 2], await Read(new(200, "", input)));
        var result = NativeBridgeTests.Parse(await bridge.DispatchAsync(Request("saveDownloadedArtifact",
            new { artifactHandle = handle, suggestedFilename = "result.xlsx" }))).GetProperty("result");
        Assert.Equal(saved, result.GetProperty("saved").GetBoolean());
        Assert.Equal(1, platform.Saves); Assert.False(artifact.Retained); Assert.False(File.Exists(path));
        Assert.Throws<NativeBridgeException>(() => owner.Resolve(handle, false, true));
        bridge.Revoke();
    }

    [Fact]
    public async Task RevokeDeletesCapturedArtifactBeforeItCanBeSaved()
    {
        var bridge = await Ready(new TestNativePlatform());
        var owner = bridge.CurrentGeneration!;
        var response = await owner.Transfers.HandleAsync("POST", owner.Transfers.PrepareCapture(Metadata([7])),
            NativeTransfers.XlsxMime, new MemoryStream([7]));
        var handle = JsonDocument.Parse(await Read(response)).RootElement.GetProperty("artifactHandle").GetString()!;
        var artifact = Assert.IsType<CapturedNativeArtifact>(owner.Resolve(handle, false, true));
        var stream = (FileStream)typeof(CapturedNativeArtifact).GetField("retained",
            System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance)!.GetValue(artifact)!;
        var path = stream.Name;
        bridge.Revoke();
        Assert.False(File.Exists(path)); Assert.False(artifact.Retained);
    }
}
