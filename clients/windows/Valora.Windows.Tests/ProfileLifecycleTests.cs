using Valora.Windows.App;
using Xunit;

namespace Valora.Windows.Tests;

public sealed class ProfileLifecycleTests
{
    private static TrustedOrigin Origin(string value)
    {
        Assert.True(TrustedOrigin.TryParse(value, out var origin));
        return origin!;
    }

    [Theory]
    [InlineData("https://valora.test", "https://VALORA.test:443/", true)]
    [InlineData("https://valora.test", "https://other.test", false)]
    [InlineData("https://valora.test", "https://valora.test:8443", false)]
    [InlineData("https://valora.test:8443", "https://valora.test:8444", false)]
    public void ProfileUsesCanonicalExactOrigin(string first, string second, bool same)
    {
        Assert.Equal(same, BrowserProfile.PathFor(Origin(first), "user-root") ==
            BrowserProfile.PathFor(Origin(second), "user-root"));
    }

    [Fact]
    public void ProfileIsUserScopedAndContainsOnlyOriginDigest()
    {
        var origin = Origin("https://valora.test:8443");
        var path = BrowserProfile.PathFor(origin, "user-one");
        Assert.NotEqual(path, BrowserProfile.PathFor(origin, "user-two"));
        Assert.StartsWith(Path.Combine("user-one", "Valora", "WindowsClient", "WebView2"), path);
        Assert.Matches("^[0-9A-F]{64}$", Path.GetFileName(path));
        Assert.DoesNotContain("valora.test", path);
    }

    [Theory]
    [InlineData((int)LifecycleSignal.Suspend, (int)LifecycleSignal.Resume, (int)ShellState.Suspended)]
    [InlineData((int)LifecycleSignal.Disconnect, (int)LifecycleSignal.Reconnect, (int)ShellState.NetworkUnavailable)]
    public void LostFreshnessRequiresNewSessionAndCurrentConfiguration(int loss, int recovery, int unavailable)
    {
        var configuration = "https://valora.test";
        var reads = 0;
        var lifecycle = new ShellLifecycle(() => { reads++; return configuration; });
        var old = lifecycle.Begin(lifecycle.Session)!;
        old.NavigationStarting(configuration + "/workbench", 7);
        old.NavigationCompleted(7, ShellState.Loaded);
        Assert.Equal(ShellState.Loaded, old.State);
        var waiting = lifecycle.Signal((LifecycleSignal)loss);
        Assert.False(lifecycle.IsCurrent(old));
        Assert.Equal(ShellState.Closed, old.State);
        Assert.Equal((ShellState)unavailable, waiting.State);
        Assert.Null(lifecycle.Begin(waiting));
        configuration = "https://replacement.test:8443";
        var revalidating = lifecycle.Signal((LifecycleSignal)recovery);
        Assert.Equal(ShellState.Revalidating, revalidating.State);
        Assert.False(revalidating.CanNavigate);
        var fresh = lifecycle.Begin(revalidating)!;
        Assert.Equal(2, reads);
        Assert.NotSame(old, fresh);
        Assert.True(lifecycle.IsCurrent(fresh));
        Assert.Equal(configuration, fresh.Origin!.Value);
        old.NavigationCompleted(7, ShellState.Loaded);
        old.Fail(ShellState.CertificateFailure);
        Assert.False(old.NavigationStarting(configuration, 8));
        Assert.Equal(ShellState.Closed, old.State);
        Assert.Equal(ShellState.Initializing, fresh.State);
        fresh.NavigationStarting(configuration + "/", 1);
        fresh.NavigationCompleted(1, ShellState.Loaded);
        Assert.Equal(ShellState.Loaded, fresh.State);
    }

    [Fact]
    public void DisconnectDuringInitializationInvalidatesContinuationAndObsoleteRecovery()
    {
        var lifecycle = new ShellLifecycle(() => "https://valora.test");
        var initializing = lifecycle.Begin(lifecycle.Session)!;
        var lost = lifecycle.Signal(LifecycleSignal.Disconnect);
        var recovered = lifecycle.Signal(LifecycleSignal.Reconnect);
        Assert.False(lifecycle.IsCurrent(initializing));
        Assert.Null(lifecycle.Begin(lost));
        Assert.Equal(ShellState.Closed, initializing.State);
        var fresh = lifecycle.Begin(recovered)!;
        initializing.Fail(ShellState.InitializationFailure);
        Assert.Equal(ShellState.Initializing, fresh.State);
    }

    [Fact]
    public void ResumeCannotBootstrapWhileDisconnectedAndReconnectCannotBootstrapWhileSuspended()
    {
        var lifecycle = new ShellLifecycle(() => "https://valora.test");
        lifecycle.Signal(LifecycleSignal.Suspend);
        lifecycle.Signal(LifecycleSignal.Disconnect);
        var reconnected = lifecycle.Signal(LifecycleSignal.Reconnect);
        Assert.Equal(ShellState.Suspended, reconnected.State);
        Assert.Null(lifecycle.Begin(reconnected));
        lifecycle.Signal(LifecycleSignal.Disconnect);
        var resumed = lifecycle.Signal(LifecycleSignal.Resume);
        Assert.Equal(ShellState.NetworkUnavailable, resumed.State);
        Assert.Null(lifecycle.Begin(resumed));
        Assert.NotNull(lifecycle.Begin(lifecycle.Signal(LifecycleSignal.Reconnect)));
    }

    [Theory]
    [InlineData(null, (int)ShellState.NoConfiguration)]
    [InlineData("http://valora.test", (int)ShellState.InvalidConfiguration)]
    public void RecoveryFailsClosedWhenMachineConfigurationChanges(string? value, int state)
    {
        string? configuration = "https://valora.test";
        var lifecycle = new ShellLifecycle(() => configuration);
        lifecycle.Begin(lifecycle.Session);
        configuration = value;
        var fresh = lifecycle.Begin(lifecycle.Signal(LifecycleSignal.Resume))!;
        Assert.Equal((ShellState)state, fresh.State);
        Assert.False(fresh.CanNavigate);
        Assert.Null(fresh.Origin);
    }

    [Fact]
    public void CloseIsTerminalIncludingPendingRecoveryAndPlatformEvents()
    {
        var lifecycle = new ShellLifecycle(() => throw new InvalidOperationException("Must not read after close"));
        var pending = lifecycle.Signal(LifecycleSignal.Resume);
        lifecycle.Close();
        Assert.Null(lifecycle.Begin(pending));
        foreach (var signal in Enum.GetValues<LifecycleSignal>())
        {
            Assert.Equal(ShellState.Closed, lifecycle.Signal(signal).State);
        }
        Assert.False(lifecycle.IsCurrent(pending));
    }

    [Fact]
    public void StartupWithoutNetworkDoesNotReadConfigurationOrCreateSession()
    {
        var lifecycle = new ShellLifecycle(() => throw new InvalidOperationException("Offline"), false);
        Assert.Equal(ShellState.NetworkUnavailable, lifecycle.Session.State);
        Assert.Null(lifecycle.Begin(lifecycle.Session));
    }

    [Fact]
    public async Task ConcurrentCompletionCannotReviveRevokedSession()
    {
        var lifecycle = new ShellLifecycle(() => "https://valora.test");
        var old = lifecycle.Begin(lifecycle.Session)!;
        old.NavigationStarting("https://valora.test/", 1);
        await Task.WhenAll(Task.Run(() => old.NavigationCompleted(1, ShellState.Loaded)),
            Task.Run(() => lifecycle.Signal(LifecycleSignal.Suspend)));
        Assert.Equal(ShellState.Closed, old.State);
        Assert.Equal(ShellState.Suspended, lifecycle.Session.State);
    }
}
