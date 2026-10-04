using System.Text.Json;
using Valora.Windows.Bridge;
using Xunit;

namespace Valora.Windows.Tests;

internal sealed class TestNativeFile(string name = "selection.xlsx", ulong size = 12) : INativeFile
{
    internal NativeFileInfo Info { get; set; } = new(name, Path.GetExtension(name).ToLowerInvariant(), size);
    internal TaskCompletionSource<NativeFileInfo>? Delayed;
    public Task<NativeFileInfo> InspectAsync(CancellationToken cancellation) => Delayed?.Task ?? Task.FromResult(Info);
}

internal sealed class TestNativePlatform : INativePlatform
{
    public IReadOnlyCollection<string> EnabledCapabilities { get; set; } = NativeProtocol.Capabilities;
    internal INativeFile? Selection;
    internal TaskCompletionSource<INativeFile?>? DelayedPicker;
    internal TaskCompletionSource<bool>? DelayedOpen;
    internal Exception? Failure;
    internal int Picks, Opens, Saves, Notifications, External;
    internal bool? SaveResult = true;
    public Task<INativeFile?> PickAsync(bool excel, BridgeGeneration generation) => generation.Start(() =>
    {
        Picks++;
        if (Failure is not null) { throw Failure; }
        return DelayedPicker?.Task ?? Task.FromResult(Selection);
    });
    public Task<bool> OpenAsync(INativeFile file, bool excel, BridgeGeneration generation) => generation.Start(() =>
    {
        Opens++;
        return DelayedOpen?.Task ?? Task.FromResult(true);
    });
    public Task<bool?> SaveAsync(INativeFile file, string name, BridgeGeneration generation) => generation.Start(() => { Saves++; return Task.FromResult(SaveResult); });
    public Task<bool> NotifyAsync(string title, string body, BridgeGeneration generation) => generation.Start(() => { Notifications++; return Task.FromResult(true); });
    public Task<bool> OpenExternalAsync(string url, BridgeGeneration generation) => generation.Start(() => { External++; return Task.FromResult(true); });
}

public sealed class NativeBridgeTests
{
    internal static string Request(string capability = "hello", object? payload = null, string? id = null) => JsonSerializer.Serialize(new
    {
        protocol = NativeProtocol.Id, type = "request", requestId = id ?? Guid.NewGuid().ToString("D"), capability, payload = payload ?? new { }
    });
    internal static JsonElement Parse(string response) => JsonDocument.Parse(response).RootElement.Clone();
    private static async Task<NativeBridgeSession> Ready(TestNativePlatform platform)
    {
        var bridge = new NativeBridgeSession(platform);
        bridge.Enable();
        Assert.True(Parse(await bridge.DispatchAsync(Request())).GetProperty("ok").GetBoolean());
        return bridge;
    }
    internal static void Error(string response, NativeError expected)
    {
        var value = Parse(response);
        Assert.False(value.GetProperty("ok").GetBoolean());
        Assert.Equal(expected.ToString(), value.GetProperty("error").GetProperty("code").GetString());
        Assert.Equal("Native operation unavailable or rejected.", value.GetProperty("error").GetProperty("message").GetString());
    }

    [Fact]
    public async Task TrustAndHelloAreRequiredAndDiscoveryContainsOnlyEnabledCapabilities()
    {
        var platform = new TestNativePlatform { EnabledCapabilities = new[] { "pickExcelFile" } };
        var bridge = new NativeBridgeSession(platform);
        Error(await bridge.DispatchAsync(Request()), NativeError.NOT_TRUSTED);
        bridge.Enable();
        Error(await bridge.DispatchAsync(Request("pickExcelFile")), NativeError.BAD_PROTOCOL);
        var hello = Parse(await bridge.DispatchAsync(Request())).GetProperty("result");
        Assert.Equal(NativeProtocol.Id, hello.GetProperty("protocol").GetString());
        Assert.Equal(new[] { "pickExcelFile" }, hello.GetProperty("capabilities").EnumerateArray().Select(v => v.GetString()));
        Error(await bridge.DispatchAsync(Request("openInWord", new { handle = new string('a', 48) })), NativeError.CAPABILITY_UNAVAILABLE);
        Assert.Equal(0, platform.Opens);
    }

    [Theory]
    [InlineData("{", NativeError.BAD_MESSAGE)]
    [InlineData("[]", NativeError.BAD_MESSAGE)]
    [InlineData("null", NativeError.BAD_MESSAGE)]
    [InlineData("{\"protocol\":\"valora.native/2\",\"type\":\"request\",\"requestId\":\"00000000-0000-0000-0000-000000000000\",\"capability\":\"hello\",\"payload\":{}}", NativeError.BAD_PROTOCOL)]
    [InlineData("{\"protocol\":\"valora.native/1\",\"type\":\"event\",\"requestId\":\"00000000-0000-0000-0000-000000000000\",\"capability\":\"hello\",\"payload\":{}}", NativeError.BAD_MESSAGE)]
    public async Task MalformedEnvelopesAreRejected(string json, NativeError code)
    {
        var bridge = await Ready(new TestNativePlatform());
        Error(await bridge.DispatchAsync(json), code);
    }

    [Fact]
    public async Task UnknownFieldsDuplicatesIdentifiersCapabilitiesAndByteLimitAreStrict()
    {
        var bridge = await Ready(new TestNativePlatform());
        var json = Request();
        Error(await bridge.DispatchAsync(json.Replace("\"payload\":{}", "\"payload\":{},\"path\":\"C:/private\"")), NativeError.BAD_MESSAGE);
        Error(await bridge.DispatchAsync(json.Replace("\"type\":\"request\"", "\"type\":\"request\",\"type\":\"request\"")), NativeError.BAD_MESSAGE);
        Error(await bridge.DispatchAsync(Request(id: "not-a-uuid")), NativeError.BAD_MESSAGE);
        Error(await bridge.DispatchAsync(Request(id: Guid.NewGuid().ToString("N"))), NativeError.BAD_MESSAGE);
        Error(await bridge.DispatchAsync(Request("execute_process")), NativeError.CAPABILITY_UNAVAILABLE);
        Error(await bridge.DispatchAsync(Request("pickExcelFile", new { path = "C:/private" })), NativeError.BAD_MESSAGE);
        var sized = json.PadRight(NativeProtocol.MessageLimit);
        Assert.True(Parse(await bridge.DispatchAsync(sized)).GetProperty("ok").GetBoolean());
        Error(await bridge.DispatchAsync(sized + " "), NativeError.SIZE_LIMIT);
        Error(await bridge.DispatchAsync(Request("showNotification", new { title = new string('界', 24_000), body = "body" })), NativeError.SIZE_LIMIT);
    }

    [Fact]
    public async Task CancelledPickerIsNormalAndSelectedMetadataContainsNoPath()
    {
        var platform = new TestNativePlatform();
        var bridge = await Ready(platform);
        Assert.False(Parse(await bridge.DispatchAsync(Request("pickExcelFile"))).GetProperty("result").GetProperty("selected").GetBoolean());
        platform.Selection = new TestNativeFile();
        var selected = Parse(await bridge.DispatchAsync(Request("pickExcelFile"))).GetProperty("result");
        var handle = selected.GetProperty("handle").GetString()!;
        Assert.True(NativeProtocol.IsHandle(handle));
        Assert.Equal(48, handle.Length);
        Assert.Equal("selection.xlsx", selected.GetProperty("name").GetString());
        Assert.Equal(12UL, selected.GetProperty("sizeBytes").GetUInt64());
        Assert.False(selected.TryGetProperty("path", out _));
        Assert.True(Parse(await bridge.DispatchAsync(Request("openInExcel", new { handle }))).GetProperty("ok").GetBoolean());
        Error(await bridge.DispatchAsync(Request("openInWord", new { handle })), NativeError.TYPE_NOT_ALLOWED);
        Error(await bridge.DispatchAsync(Request("openInExcel", new { handle = new string('b', 48) })), NativeError.HANDLE_INVALID);
        Assert.Equal(1, platform.Opens);
    }

    [Theory]
    [InlineData("malware.exe", 10, NativeError.TYPE_NOT_ALLOWED)]
    [InlineData("wrong.docx", 10, NativeError.TYPE_NOT_ALLOWED)]
    [InlineData("large.xlsx", 67108865, NativeError.SIZE_LIMIT)]
    [InlineData("C:\\private.xlsx", 10, NativeError.TYPE_NOT_ALLOWED)]
    public async Task PickerTypeSizeAndPathMetadataAreDenied(string name, long size, NativeError error)
    {
        var platform = new TestNativePlatform { Selection = new TestNativeFile(name, (ulong)size) };
        var bridge = await Ready(platform);
        Error(await bridge.DispatchAsync(Request("pickExcelFile")), error);
        Assert.Equal(0, platform.Opens);
    }

    [Fact]
    public async Task HandleCapGenerationAndFreshSizeAreEnforced()
    {
        var platform = new TestNativePlatform { Selection = new TestNativeFile("edge.docx", BridgeGeneration.FileLimit) };
        var bridge = await Ready(platform);
        var generation = bridge.CurrentGeneration!;
        var handles = new HashSet<string>();
        for (var i = 0; i < BridgeGeneration.HandleLimit; i++)
        {
            var result = Parse(await bridge.DispatchAsync(Request("pickDocumentFile"))).GetProperty("result");
            Assert.True(handles.Add(result.GetProperty("handle").GetString()!));
        }
        Error(await bridge.DispatchAsync(Request("pickDocumentFile")), NativeError.BUSY);
        var first = handles.First();
        ((TestNativeFile)platform.Selection).Info = new("edge.docx", ".docx", BridgeGeneration.FileLimit + 1);
        Error(await bridge.DispatchAsync(Request("openInWord", new { handle = first })), NativeError.SIZE_LIMIT);
        bridge.Revoke();
        Assert.Throws<NativeBridgeException>(() => generation.Resolve(first, false));
        bridge.Enable();
        await bridge.DispatchAsync(Request());
        Error(await bridge.DispatchAsync(Request("openInWord", new { handle = first })), NativeError.HANDLE_INVALID);
        Assert.Equal(0, platform.Opens);
    }

    [Fact]
    public async Task PickerInteractionAndDuplicateIdsCannotRepeatAnAction()
    {
        var platform = new TestNativePlatform { DelayedPicker = new(TaskCreationOptions.RunContinuationsAsynchronously) };
        var bridge = await Ready(platform);
        var id = Guid.NewGuid().ToString("D");
        var first = bridge.DispatchAsync(Request("pickExcelFile", id: id));
        Error(await bridge.DispatchAsync(Request("pickExcelFile", id: id)), NativeError.BAD_MESSAGE);
        Error(await bridge.DispatchAsync(Request("pickDocumentFile")), NativeError.BUSY);
        platform.DelayedPicker.SetResult(null);
        await first;
        Error(await bridge.DispatchAsync(Request("pickExcelFile", id: id)), NativeError.BAD_MESSAGE);
        Assert.Equal(1, platform.Picks);
    }

    [Fact]
    public async Task EightPendingCallsRevokeImmediatelyAndOldCompletionCannotActOrClearNewInteraction()
    {
        var platform = new TestNativePlatform { DelayedOpen = new(TaskCreationOptions.RunContinuationsAsynchronously), Selection = new TestNativeFile() };
        var bridge = await Ready(platform);
        var handle = Parse(await bridge.DispatchAsync(Request("pickExcelFile"))).GetProperty("result").GetProperty("handle").GetString()!;
        var pending = Enumerable.Range(0, 8).Select(_ => bridge.DispatchAsync(Request("openInExcel", new { handle }))).ToArray();
        Assert.All(pending, task => Assert.False(task.IsCompleted));
        Error(await bridge.DispatchAsync(Request()), NativeError.BUSY);
        bridge.Revoke();
        foreach (var task in pending) { Error(await task.WaitAsync(TimeSpan.FromSeconds(1)), NativeError.BRIDGE_REVOKED); }
        platform.DelayedOpen.SetResult(true);
        bridge.Enable();
        await bridge.DispatchAsync(Request());
        Error(await bridge.DispatchAsync(Request("openInExcel", new { handle })), NativeError.HANDLE_INVALID);
        Assert.Equal(8, platform.Opens);
    }

    [Fact]
    public async Task RevocationDuringMetadataLookupPreventsLaterOfficeLaunch()
    {
        var file = new TestNativeFile();
        var platform = new TestNativePlatform { Selection = file };
        var bridge = await Ready(platform);
        var handle = Parse(await bridge.DispatchAsync(Request("pickExcelFile"))).GetProperty("result").GetProperty("handle").GetString()!;
        file.Delayed = new(TaskCreationOptions.RunContinuationsAsynchronously);
        var opening = bridge.DispatchAsync(Request("openInExcel", new { handle }));
        bridge.Revoke();
        Error(await opening, NativeError.BRIDGE_REVOKED);
        file.Delayed.SetResult(file.Info);
        await Task.Delay(20);
        Assert.Equal(0, platform.Opens);
    }

    [Fact]
    public async Task PlatformExceptionsNeverLeakNativePathsOrRawMessages()
    {
        var platform = new TestNativePlatform { Failure = new IOException("C:\\private\\file.xlsx secret machine failure") };
        var bridge = await Ready(platform);
        var response = await bridge.DispatchAsync(Request("pickExcelFile"));
        Error(response, NativeError.FAILED);
        Assert.DoesNotContain("private", response);
        Assert.DoesNotContain("machine", response);
        Assert.DoesNotContain("IOException", response);
    }

    [Fact]
    public async Task SaveOnlyAcceptsNativeArtifactHandlesAndSafeSameTypeUserNames()
    {
        var platform = new TestNativePlatform();
        var bridge = await Ready(platform);
        var file = new TestNativeFile("result.xlsx");
        var ordinary = bridge.CurrentGeneration!.Register(file, file.Info);
        Error(await bridge.DispatchAsync(Request("saveDownloadedArtifact", new { artifactHandle = ordinary, suggestedFilename = "result.xlsx" })), NativeError.HANDLE_INVALID);
        var artifact = bridge.CurrentGeneration.Register(file, file.Info, true);
        Error(await bridge.DispatchAsync(Request("saveDownloadedArtifact", new { artifactHandle = artifact, suggestedFilename = "C:\\result.xlsx" })), NativeError.INVALID_ARGUMENT);
        Error(await bridge.DispatchAsync(Request("saveDownloadedArtifact", new { artifactHandle = artifact, suggestedFilename = "run.exe" })), NativeError.TYPE_NOT_ALLOWED);
        Assert.True(Parse(await bridge.DispatchAsync(Request("saveDownloadedArtifact", new { artifactHandle = artifact, suggestedFilename = "result.xlsx" }))).GetProperty("result").GetProperty("saved").GetBoolean());
        platform.SaveResult = null;
        Assert.False(Parse(await bridge.DispatchAsync(Request("saveDownloadedArtifact", new { artifactHandle = artifact, suggestedFilename = "result.xlsx" }))).GetProperty("result").GetProperty("saved").GetBoolean());
        Assert.Equal(2, platform.Saves);
    }

    [Fact]
    public async Task DropsAreSingleTypedBoundedEventsAndCannotMoveAcrossGenerations()
    {
        var bridge = await Ready(new TestNativePlatform());
        var events = new List<string>();
        bridge.NativeEvent += (json, _) => events.Add(json);
        var generation = bridge.CurrentGeneration!;
        await bridge.MediateDropAsync(new[] { new TestNativeFile() }, generation);
        var message = Parse(Assert.Single(events));
        Assert.Equal("filesDropped", message.GetProperty("event").GetString());
        Assert.True(NativeProtocol.IsHandle(message.GetProperty("payload").GetProperty("handle").GetString()!));
        await Assert.ThrowsAsync<NativeBridgeException>(() => bridge.MediateDropAsync(new[] { new TestNativeFile(), new TestNativeFile() }, generation));
        await Assert.ThrowsAsync<NativeBridgeException>(() => bridge.MediateDropAsync(new[] { new TestNativeFile("bad.exe") }, generation));
        await Assert.ThrowsAsync<NativeBridgeException>(() => bridge.MediateDropAsync(new[] { new TestNativeFile("big.xlsx", BridgeGeneration.FileLimit + 1) }, generation));
        bridge.Revoke(); bridge.Enable(); await bridge.DispatchAsync(Request());
        var error = await Assert.ThrowsAsync<NativeBridgeException>(() => bridge.MediateDropAsync(new[] { new TestNativeFile() }, generation));
        Assert.Equal(NativeError.BRIDGE_REVOKED, error.Code);
        Assert.Equal(2, events.Count);
    }

    [Theory]
    [InlineData("https://foreign.test")]
    [InlineData("//foreign.test/path")]
    [InlineData("/\\foreign")]
    [InlineData("/../command")]
    [InlineData("/%2f%2fforeign")]
    [InlineData("/x\ncommand")]
    public void DeepLinkValidatorRejectsAuthorityAndAmbiguity(string route) => Assert.False(NativeProtocol.SafeRoute(route));

    [Fact]
    public async Task DeepLinkEventIsNavigationOnlyAndDisabledSourceIsUnavailable()
    {
        var bridge = await Ready(new TestNativePlatform());
        string? received = null;
        bridge.NativeEvent += (json, _) => received = json;
        bridge.MediateDeepLink("/workbench/projects", bridge.CurrentGeneration!);
        Assert.Equal("/workbench/projects", Parse(received!).GetProperty("payload").GetProperty("route").GetString());
        Assert.False(NativeProtocol.SafeRoute("/" + new string('a', 2048)));
        var unavailable = await Ready(new TestNativePlatform { EnabledCapabilities = Array.Empty<string>() });
        Assert.Throws<NativeBridgeException>(() => unavailable.MediateDeepLink("/workbench", unavailable.CurrentGeneration!));
    }

    [Fact]
    public async Task NotificationLimitsCountUnicodeScalarsAndRejectAddedActions()
    {
        var bridge = await Ready(new TestNativePlatform());
        Assert.True(Parse(await bridge.DispatchAsync(Request("showNotification", new { title = string.Concat(Enumerable.Repeat("😀", 80)), body = new string('a', 256) }))).GetProperty("ok").GetBoolean());
        Error(await bridge.DispatchAsync(Request("showNotification", new { title = new string('a', 81), body = "body" })), NativeError.INVALID_ARGUMENT);
        Error(await bridge.DispatchAsync(Request("showNotification", new { title = "title", body = new string('a', 257) })), NativeError.INVALID_ARGUMENT);
        Error(await bridge.DispatchAsync(Request("showNotification", new { title = "title", body = "body", url = "https://foreign.test" })), NativeError.BAD_MESSAGE);
    }

    [Fact]
    public async Task ReplayHistoryIsBoundedWithoutEvictingIdsThatCouldRepeatAnAction()
    {
        var bridge = await Ready(new TestNativePlatform());
        var initialId = Guid.NewGuid().ToString("D");
        await bridge.DispatchAsync(Request(id: initialId));
        for (var i = 0; i < 4094; i++) Assert.True(Parse(await bridge.DispatchAsync(Request())).GetProperty("ok").GetBoolean());
        Error(await bridge.DispatchAsync(Request()), NativeError.BUSY);
        Error(await bridge.DispatchAsync(Request(id: initialId)), NativeError.BAD_MESSAGE);
        bridge.Revoke(); bridge.Enable();
        Assert.True(Parse(await bridge.DispatchAsync(Request())).GetProperty("ok").GetBoolean());
    }

    [Fact]
    public async Task OldDispatchGenerationCannotBeAdmittedToAnAlreadyLoadedReplacement()
    {
        var platform = new TestNativePlatform();
        var bridge = await Ready(platform);
        var old = bridge.CurrentGeneration!;
        bridge.Revoke(); bridge.Enable(); await bridge.DispatchAsync(Request());
        Error(await bridge.DispatchAsync(Request("pickExcelFile"), old), NativeError.BRIDGE_REVOKED);
        Assert.Equal(0, platform.Picks);
    }
}
