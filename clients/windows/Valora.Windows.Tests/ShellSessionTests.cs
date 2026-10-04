using Valora.Windows.App;
using Xunit;

namespace Valora.Windows.Tests;

public sealed class ShellSessionTests
{
    [Fact]
    public void MissingAndInvalidConfigurationNeverPermitNavigation()
    {
        var session = new ShellSession();
        Assert.False(session.Begin(null));
        Assert.Equal(ShellState.NoConfiguration, session.State);
        Assert.False(session.NavigationStarting("https://valora.example", 1));
        Assert.False(session.Begin("https://user:secret@valora.example"));
        Assert.Equal(ShellState.InvalidConfiguration, session.State);
        Assert.Null(session.Origin);
    }

    [Fact]
    public void InitializationLoadingAndCompletionAreSeparateStates()
    {
        var session = new ShellSession();
        Assert.True(session.Begin("https://valora.example"));
        Assert.Equal(ShellState.Initializing, session.State);
        Assert.True(session.NavigationStarting("https://valora.example/login", 1));
        Assert.Equal(ShellState.Loading, session.State);
        session.NavigationCompleted(1, ShellState.Loaded);
        Assert.Equal(ShellState.Loaded, session.State);
    }

    [Theory]
    [InlineData("http://valora.example")]
    [InlineData("https://other.example")]
    [InlineData("https://valora.example:8443")]
    public void RedirectRevokesNavigationAndLateSuccessCannotRestoreIt(string redirect)
    {
        var session = new ShellSession();
        session.Begin("https://valora.example");
        Assert.True(session.NavigationStarting("https://valora.example", 1));
        Assert.False(session.NavigationStarting(redirect, 1));
        Assert.Equal(ShellState.NavigationBlocked, session.State);
        session.NavigationCompleted(1, ShellState.Loaded);
        Assert.Equal(ShellState.NavigationBlocked, session.State);
        Assert.False(session.NavigationStarting("https://valora.example", 2));
    }

    [Theory]
    [InlineData((int)ShellState.NetworkFailure)]
    [InlineData((int)ShellState.CertificateFailure)]
    [InlineData((int)ShellState.NavigationFailure)]
    [InlineData((int)ShellState.InitializationFailure)]
    public void RetryRevalidatesCurrentConfigurationAndRevokesPreviousOrigin(int failureValue)
    {
        var failure = (ShellState)failureValue;
        var session = new ShellSession();
        session.Begin("https://valora.example");
        session.Fail(failure);
        Assert.Equal(failure, session.State);
        Assert.False(session.Begin("http://valora.example"));
        Assert.Null(session.Origin);
        Assert.True(session.Begin("https://replacement.example:8443"));
        Assert.False(session.NavigationStarting("https://valora.example", 1));
    }

    [Fact]
    public void StaleNavigationCompletionCannotOverwriteCurrentLoadingState()
    {
        var session = new ShellSession();
        session.Begin("https://valora.example");
        session.NavigationStarting("https://valora.example/one", 1);
        session.NavigationStarting("https://valora.example/two", 2);
        session.NavigationCompleted(1, ShellState.NetworkFailure);
        Assert.Equal(ShellState.Loading, session.State);
        session.NavigationCompleted(2, ShellState.Loaded);
        Assert.Equal(ShellState.Loaded, session.State);
    }

    [Fact]
    public void ClosedWindowCannotRestartOrAcceptLateEvents()
    {
        var session = new ShellSession();
        session.Begin("https://valora.example");
        session.Close();
        Assert.False(session.Begin("https://valora.example"));
        session.Fail(ShellState.InitializationFailure);
        Assert.Equal(ShellState.Closed, session.State);
        Assert.Null(session.Origin);
    }
}
