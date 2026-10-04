using System.Net.NetworkInformation;
using Microsoft.Windows.System.Power;

namespace Valora.Windows.App;

internal sealed class WindowsLifecycleEvents : ILifecycleEvents
{
    public bool NetworkAvailable => NetworkInterface.GetIsNetworkAvailable();
    public event Action<LifecycleSignal>? Changed;

    internal WindowsLifecycleEvents()
    {
        PowerManager.SystemSuspendStatusChanged += PowerChanged;
        NetworkChange.NetworkAvailabilityChanged += NetworkChanged;
    }

    private void PowerChanged(object? sender, object args)
    {
        switch (PowerManager.SystemSuspendStatus)
        {
            case SystemSuspendStatus.Entering: Changed?.Invoke(LifecycleSignal.Suspend); break;
            case SystemSuspendStatus.AutoResume:
            case SystemSuspendStatus.ManualResume: Changed?.Invoke(LifecycleSignal.Resume); break;
        }
    }

    private void NetworkChanged(object? sender, NetworkAvailabilityEventArgs args) =>
        Changed?.Invoke(args.IsAvailable ? LifecycleSignal.Reconnect : LifecycleSignal.Disconnect);

    public void Dispose()
    {
        NetworkChange.NetworkAvailabilityChanged -= NetworkChanged;
        PowerManager.SystemSuspendStatusChanged -= PowerChanged;
    }
}
