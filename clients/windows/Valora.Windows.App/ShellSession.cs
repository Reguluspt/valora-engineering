namespace Valora.Windows.App;

internal enum ShellState
{
    NoConfiguration, InvalidConfiguration, Initializing, Loading, Loaded,
    NavigationBlocked, NetworkFailure, CertificateFailure, NavigationFailure,
    InitializationFailure, Closed
}

internal sealed class ShellSession
{
    private ulong? navigationId;
    internal TrustedOrigin? Origin { get; private set; }
    internal ShellState State { get; private set; } = ShellState.NoConfiguration;
    internal bool CanNavigate => Origin is not null &&
        State is ShellState.Initializing or ShellState.Loading or ShellState.Loaded;

    internal bool Begin(string? configuration)
    {
        if (State == ShellState.Closed) { return false; }
        Origin = null;
        navigationId = null;
        if (configuration is null)
        {
            State = ShellState.NoConfiguration;
            return false;
        }
        if (!TrustedOrigin.TryParse(configuration, out var origin))
        {
            State = ShellState.InvalidConfiguration;
            return false;
        }
        Origin = origin;
        State = ShellState.Initializing;
        return true;
    }

    internal bool NavigationStarting(string? destination, ulong id)
    {
        if (!CanNavigate) { return false; }
        if (!Origin!.Allows(destination))
        {
            Fail(ShellState.NavigationBlocked);
            return false;
        }
        navigationId = id;
        State = ShellState.Loading;
        return true;
    }

    internal void NavigationCompleted(ulong id, ShellState result)
    {
        if (CanNavigate && navigationId == id) { State = result; }
    }

    internal void Fail(ShellState failure)
    {
        if (State != ShellState.Closed)
        {
            State = failure;
            navigationId = null;
        }
    }

    internal void Close()
    {
        Origin = null;
        navigationId = null;
        State = ShellState.Closed;
    }
}
