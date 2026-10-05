using Valora.Windows.App;
using Valora.Windows.Bridge;
using Windows.Storage;
using Xunit;

namespace Valora.Windows.Tests;

public sealed class NativePlatformTests
{
    [Fact]
    public async Task ProductionCatalogDoesNotAdvertiseMissingArtifactPackagingActivationOrExternalAuthority()
    {
        var platform = new WindowsNativePlatform(0);
        Assert.Equal(new[] { "pickExcelFile", "pickDocumentFile", "openInExcel", "openInWord", "dragDrop" }, platform.EnabledCapabilities);
        var bridge = new NativeBridgeSession(platform);
        bridge.Enable(); await bridge.DispatchAsync(NativeBridgeTests.Request());
        foreach (var (capability, payload) in new (string, object)[]
        {
            ("saveDownloadedArtifact", new { artifactHandle = new string('a', 48), suggestedFilename = "result.xlsx" }),
            ("showNotification", new { title = "Valora", body = "Notice" }),
            ("deepLink", new { }),
            ("openExternalUrl", new { url = "https://example.com" })
        }) { NativeBridgeTests.Error(await bridge.DispatchAsync(NativeBridgeTests.Request(capability, payload)), NativeError.CAPABILITY_UNAVAILABLE); }
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
    public async Task PlatformLauncherCannotAcceptAnInjectedNonStorageFile()
    {
        var platform = new WindowsNativePlatform(0);
        var generation = new BridgeGeneration();
        await Assert.ThrowsAsync<NativeBridgeException>(() => platform.OpenAsync(new TestNativeFile(), true, generation));
        await Assert.ThrowsAsync<NativeBridgeException>(() => platform.SaveAsync(new TestNativeFile(), "result.xlsx", generation));
    }
}
