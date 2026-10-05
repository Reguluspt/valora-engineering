using Microsoft.Web.WebView2.Core;
using Valora.Windows.Bridge;

namespace Valora.Windows.App;

internal sealed class WebViewNativeBridge : IDisposable
{
    private readonly CoreWebView2 core;
    private readonly ShellSession session;
    private readonly NativeBridgeSession bridge;
    private readonly Func<bool> isCurrent;
    private readonly Action<Action> enqueue;
    private bool disposed;

    internal WebViewNativeBridge(CoreWebView2 core, ShellSession session, NativeBridgeSession bridge,
        Func<bool> isCurrent, Action<Action> enqueue)
    {
        this.core = core;
        this.session = session;
        this.bridge = bridge;
        this.isCurrent = isCurrent;
        this.enqueue = enqueue;
        core.WebMessageReceived += Received;
        session.Revoked += Revoke;
        bridge.NativeEvent += QueueEvent;
    }

    private bool Trusted
    {
        get
        {
            try { return !disposed && isCurrent() && session.State == ShellState.Loaded && session.Origin?.Allows(core.Source) == true; }
            catch (Exception error) when (error is System.Runtime.InteropServices.COMException or InvalidOperationException)
            {
                bridge.Revoke();
                return false;
            }
        }
    }

    internal void Enable()
    {
        if (!Trusted) { Revoke(); return; }
        bridge.Enable();
        core.Settings.IsWebMessageEnabled = true;
    }

    internal void Revoke()
    {
        bridge.Revoke();
        enqueue(() => { if (!disposed && !bridge.Enabled) { core.Settings.IsWebMessageEnabled = false; } });
    }

    private async void Received(object? sender, CoreWebView2WebMessageReceivedEventArgs args)
    {
        try
        {
            var generation = bridge.CurrentGeneration;
            if (!AllowsSender(sender, args.Source)) { return; }
            var response = await bridge.DispatchAsync(args.WebMessageAsJson, generation);
            enqueue(() =>
            {
                if (Trusted && bridge.Enabled && ReferenceEquals(generation, bridge.CurrentGeneration)) { Post(response); }
            });
        }
        catch (Exception error) when (error is System.Runtime.InteropServices.COMException or InvalidOperationException) { Revoke(); }
    }

    internal bool AllowsSender(object? sender, string source)
    {
        try { return ReferenceEquals(sender, core) && Trusted && bridge.Enabled && session.Origin?.Allows(source) == true &&
            string.Equals(source, core.Source, StringComparison.Ordinal); }
        catch (Exception error) when (error is System.Runtime.InteropServices.COMException or InvalidOperationException) { Revoke(); return false; }
    }

    private void QueueEvent(string message, BridgeGeneration generation) => enqueue(() =>
    {
        if (Trusted && ReferenceEquals(generation, bridge.CurrentGeneration)) { Post(message); }
    });

    private void Post(string json)
    {
        try { core.PostWebMessageAsJson(json); }
        catch (Exception error) when (error is System.Runtime.InteropServices.COMException or InvalidOperationException)
        {
            bridge.Revoke();
        }
    }

    public void Dispose()
    {
        if (disposed) { return; }
        disposed = true;
        session.Revoked -= Revoke;
        bridge.NativeEvent -= QueueEvent;
        core.WebMessageReceived -= Received;
        bridge.Revoke();
        core.Settings.IsWebMessageEnabled = false;
    }
}
