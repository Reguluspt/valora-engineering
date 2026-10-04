namespace Valora.Windows.App;

internal enum ShellState
{
    NoConfiguration, InvalidConfiguration, Initializing, Loading, Loaded,
    NavigationBlocked, NetworkFailure, CertificateFailure, NavigationFailure,
    InitializationFailure, Suspended, NetworkUnavailable, Revalidating, Closed
}

internal sealed class ShellSession
{
    private ulong? navigationId;
    private readonly object gate = new();
    private TrustedOrigin? origin;
    private ShellState state = ShellState.NoConfiguration;
    internal TrustedOrigin? Origin { get { lock (gate) { return origin; } } }
    internal ShellState State { get { lock (gate) { return state; } } }
    internal bool CanNavigate { get { lock (gate) { return origin is not null &&
        state is ShellState.Initializing or ShellState.Loading or ShellState.Loaded; } } }

    internal bool Begin(string? configuration)
    {
        lock (gate)
        {
            if (state == ShellState.Closed) { return false; }
            origin = null;
            navigationId = null;
            if (configuration is null)
            {
                state = ShellState.NoConfiguration;
                return false;
            }
            if (!TrustedOrigin.TryParse(configuration, out var parsed))
            {
                state = ShellState.InvalidConfiguration;
                return false;
            }
            origin = parsed;
            state = ShellState.Initializing;
            return true;
        }
    }

    internal bool NavigationStarting(string? destination, ulong id)
    {
        lock (gate)
        {
            if (!CanNavigate) { return false; }
            if (!origin!.Allows(destination))
            {
                Fail(ShellState.NavigationBlocked);
                return false;
            }
            navigationId = id;
            state = ShellState.Loading;
            return true;
        }
    }

    internal void NavigationCompleted(ulong id, ShellState result)
    {
        lock (gate)
        {
            if (CanNavigate && navigationId == id) { state = result; }
        }
    }

    internal void Fail(ShellState failure)
    {
        lock (gate)
        {
            if (state != ShellState.Closed)
            {
                state = failure;
                navigationId = null;
            }
        }
    }

    internal void Close()
    {
        lock (gate)
        {
            origin = null;
            navigationId = null;
            state = ShellState.Closed;
        }
    }
}
