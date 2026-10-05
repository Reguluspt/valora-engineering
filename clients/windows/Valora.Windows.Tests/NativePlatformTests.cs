using Valora.Windows.App;
using Valora.Windows.Bridge;
using Windows.Storage;
using Xunit;

namespace Valora.Windows.Tests;

public sealed class NativePlatformTests
{
    [Fact]
    public async Task ProductionCatalogEnablesBoundedArtifactsButKeepsPackagingActivationAndExternalAuthorityDeferred()
    {
        var platform = new WindowsNativePlatform(0);
        Assert.Equal(new[] { "pickExcelFile", "pickDocumentFile", "openInExcel", "openInWord", "dragDrop",
            "saveDownloadedArtifact", "prepareSelectedFileTransfer", "prepareArtifactCapture" }, platform.EnabledCapabilities);
        var bridge = new NativeBridgeSession(platform);
        bridge.Enable(); await bridge.DispatchAsync(NativeBridgeTests.Request());
        foreach (var (capability, payload) in new (string, object)[]
        {
            ("showNotification", new { title = "Valora", body = "Notice" }),
            ("deepLink", new { }),
            ("openExternalUrl", new { url = "https://example.com" })
        }) { NativeBridgeTests.Error(await bridge.DispatchAsync(NativeBridgeTests.Request(capability, payload)), NativeError.CAPABILITY_UNAVAILABLE); }
        NativeBridgeTests.Error(await bridge.DispatchAsync(NativeBridgeTests.Request("saveDownloadedArtifact",
            new { artifactHandle = new string('a', 48), suggestedFilename = "result.xlsx" })), NativeError.HANDLE_INVALID);
        var error = await Assert.ThrowsAsync<NativeBridgeException>(() => platform.OpenExternalAsync("https://example.com", bridge.CurrentGeneration!));
        Assert.Equal(NativeError.CAPABILITY_UNAVAILABLE, error.Code);
    }

    [Theory]
    [InlineData("https://allowed.test/path", true)]
    [InlineData("https://allowed.test:443/path", true)]
    [InlineData("https://allowed.test:8443/path", false)]
    [InlineData("https://child.allowed.test/path", false)]
    [InlineData("https://allowed.test.evil.test/path", false)]
    [InlineData("https://allowed.test@evil.test/path", false)]
    [InlineData("http://allowed.test/path", false)]
    [InlineData("file:///C:/private", false)]
    [InlineData("https://allowed.test./path", false)]
    [InlineData("https://allowed.test\\@evil.test", false)]
    [InlineData("https://foreign.test/path", false)]
    public void ExternalUrlsUseExactHttpsOriginWithoutWildcardOrAuthorityCoercion(string url, bool allowed)
    {
        Assert.Equal(allowed, new ExternalUrlPolicy(new[] { "https://allowed.test" }).Allows(url));
        Assert.False(new ExternalUrlPolicy(Array.Empty<string>()).Allows(url));
    }

    [Theory]
    [InlineData("https://*.allowed.test")]
    [InlineData("http://allowed.test")]
    [InlineData("https://allowed.test/path")]
    [InlineData("https://user@allowed.test")]
    public void InvalidNativeExternalCatalogCannotEnableDestinations(string origin) =>
        Assert.Throws<ArgumentException>(() => new ExternalUrlPolicy(new[] { origin }));

    [Fact]
    public async Task RealStorageFileMetadataIsBoundedAndCannotReturnAPath()
    {
        var path = Path.Combine(Path.GetTempPath(), "Valora.Win3." + Guid.NewGuid().ToString("N") + ".docx");
        try
        {
            await File.WriteAllBytesAsync(path, new byte[] { 1, 2, 3 });
            var file = await StorageFile.GetFileFromPathAsync(path);
            var selected = new WindowsNativeFile(file);
            var info = await selected.InspectAsync(CancellationToken.None);
            Assert.Equal(Path.GetFileName(path), info.Name);
            Assert.Equal(".docx", info.Extension);
            Assert.Equal(3UL, info.SizeBytes);
            BridgeGeneration.ValidateFile(info);
            var generation = new BridgeGeneration();
            var id = generation.Register(selected, info);
            Assert.Same(selected, generation.Resolve(id, false));
            generation.Revoke();
            Assert.Throws<NativeBridgeException>(() => generation.Resolve(id, false));
        }
        finally { File.Delete(path); }
    }

    [Fact]
    public async Task WinRtResponseProjectionSupportsRandomAccessAndGenerationRevocation()
    {
        var platform = new TestNativePlatform
        {
            EnabledCapabilities = NativeProtocol.V2Capabilities, Selection = new ReadableTestFile([1, 2, 3])
        };
        var bridge = new NativeBridgeSession(platform);
        bridge.Enable();
        await bridge.DispatchAsync(NativeTransferTests.Request());
        var owner = bridge.CurrentGeneration!;
        var selected = NativeBridgeTests.Parse(await bridge.DispatchAsync(NativeTransferTests.Request("pickExcelFile"))).GetProperty("result");
        var prepared = NativeBridgeTests.Parse(await bridge.DispatchAsync(NativeTransferTests.Request("prepareSelectedFileTransfer",
            new { handle = selected.GetProperty("handle").GetString() }))).GetProperty("result").GetProperty("url").GetString()!;
        var response = await owner.Transfers.HandleAsync("GET", prepared, "", null);
        using var random = response.Content.AsRandomAccessStream();
        Assert.Equal(3UL, random.Size);
        using (var reader = new global::Windows.Storage.Streams.DataReader(random))
        {
            Assert.Equal(3U, await reader.LoadAsync(3));
            var bytes = new byte[3];
            reader.ReadBytes(bytes);
            Assert.Equal(new byte[] { 1, 2, 3 }, bytes);
            reader.DetachStream();
        }
        random.Seek(0);
        var native = WinRT.MarshalInterface<global::Windows.Storage.Streams.IRandomAccessStream>.FromManaged(random);
        nint converted = 0;
        try
        {
            var iid = typeof(System.Runtime.InteropServices.ComTypes.IStream).GUID;
            System.Runtime.InteropServices.Marshal.ThrowExceptionForHR(CreateStreamOverRandomAccessStream(native, ref iid, out converted));
            var com = (System.Runtime.InteropServices.ComTypes.IStream)System.Runtime.InteropServices.Marshal.GetObjectForIUnknown(converted);
            var bytes = new byte[3];
            com.Read(bytes, bytes.Length, 0);
            Assert.Equal(new byte[] { 1, 2, 3 }, bytes);
            System.Runtime.InteropServices.Marshal.ReleaseComObject(com);
        }
        finally
        {
            if (converted != 0) System.Runtime.InteropServices.Marshal.Release(converted);
            WinRT.MarshalInterface<global::Windows.Storage.Streams.IRandomAccessStream>.DisposeAbi(native);
        }
        bridge.Revoke();
        Assert.ThrowsAny<Exception>(() => response.Content.ReadByte());
    }

    [System.Runtime.InteropServices.DllImport("shcore.dll", ExactSpelling = true)]
    private static extern int CreateStreamOverRandomAccessStream(nint stream, ref Guid iid, out nint result);

    [Fact]
    public async Task PlatformLauncherCannotAcceptAnInjectedNonStorageFile()
    {
        var platform = new WindowsNativePlatform(0);
        var generation = new BridgeGeneration();
        await Assert.ThrowsAsync<NativeBridgeException>(() => platform.OpenAsync(new TestNativeFile(), true, generation));
        await Assert.ThrowsAsync<NativeBridgeException>(() => platform.SaveAsync(new TestNativeFile(), "result.xlsx", generation));
    }
}
