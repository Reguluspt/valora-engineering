namespace Valora.Windows.App;

internal enum LifecycleSignal { Suspend, Resume, Disconnect, Reconnect }

internal interface ILifecycleEvents : IDisposable
{
    bool NetworkAvailable { get; }
    event Action<LifecycleSignal>? Changed;
}

internal sealed class ShellLifecycle
{
    private readonly object gate = new();
    private readonly Func<string?> readConfiguration;
    private ShellSession session = new();
    private bool suspended;
    private bool networkAvailable;
    private bool closed;

    internal ShellLifecycle(Func<string?> readConfiguration, bool networkAvailable = true)
    {
        this.readConfiguration = readConfiguration;
        this.networkAvailable = networkAvailable;
        if (!networkAvailable) { session.Fail(ShellState.NetworkUnavailable); }
    }

    internal ShellSession Session { get { lock (gate) { return session; } } }

    internal bool IsCurrent(ShellSession candidate)
    {
        lock (gate) { return !closed && ReferenceEquals(session, candidate); }
    }

    internal ShellSession? Begin(ShellSession expected)
    {
        lock (gate)
        {
            if (closed || suspended || !networkAvailable || !ReferenceEquals(session, expected)) { return null; }
            session.Close();
            session = new ShellSession();
            session.Begin(readConfiguration());
            return session;
        }
    }

    // Called on the platform event thread: revoke before any queued UI/browser continuation.
    internal ShellSession Signal(LifecycleSignal signal)
    {
        lock (gate)
        {
            if (closed) { return session; }
            switch (signal)
            {
                case LifecycleSignal.Suspend: suspended = true; break;
                case LifecycleSignal.Resume: suspended = false; break;
                case LifecycleSignal.Disconnect: networkAvailable = false; break;
                case LifecycleSignal.Reconnect: networkAvailable = true; break;
            }
            session.Close();
            session = new ShellSession();
            session.Fail(suspended ? ShellState.Suspended :
                networkAvailable ? ShellState.Revalidating : ShellState.NetworkUnavailable);
            return session;
        }
    }

    internal void Close()
    {
        lock (gate)
        {
            closed = true;
            session.Close();
        }
    }
}
