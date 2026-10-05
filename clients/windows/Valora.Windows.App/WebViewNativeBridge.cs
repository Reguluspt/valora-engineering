using Microsoft.Web.WebView2.Core;
using Valora.Windows.Bridge;
#if VALORA_WINUI
using NativeResponseStream = Windows.Storage.Streams.IRandomAccessStream;
#else
using NativeResponseStream = System.IO.Stream;
#endif

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
        core.AddWebResourceRequestedFilter("*" + NativeTransfers.Prefix + "*", CoreWebView2WebResourceContext.All,
            CoreWebView2WebResourceRequestSourceKinds.All);
        core.WebResourceRequested += ResourceRequested;
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

    internal bool AllowsResource(object? sender, string requestUri, string referrer,
        CoreWebView2WebResourceRequestSourceKinds sourceKind)
    {
        if (!ReferenceEquals(sender, core) || !Trusted || !bridge.Enabled ||
            sourceKind != CoreWebView2WebResourceRequestSourceKinds.Document ||
            session.Origin?.Allows(requestUri) != true ||
            !Uri.TryCreate(requestUri, UriKind.Absolute, out var uri) ||
            uri.Query.Length != 0 || uri.Fragment.Length != 0 ||
            !uri.AbsolutePath.StartsWith(NativeTransfers.Prefix, StringComparison.Ordinal)) { return false; }
        var document = new Uri(core.Source).GetLeftPart(UriPartial.Query);
        return string.Equals(referrer, document, StringComparison.Ordinal);
    }

    private async void ResourceRequested(object? sender, CoreWebView2WebResourceRequestedEventArgs args)
    {
        if (!Uri.TryCreate(args.Request.Uri, UriKind.Absolute, out var uri) ||
            !uri.AbsolutePath.StartsWith(NativeTransfers.Prefix, StringComparison.Ordinal)) { return; }
        // Seed a synthetic rejection before any deferral: this namespace never falls through to network.
        args.Response = core.Environment.CreateWebResourceResponse(ResponseStream(new MemoryStream()), 404, "Not Found",
            "Cache-Control: no-store\r\nX-Content-Type-Options: nosniff\r\n");
        using var deferral = args.GetDeferral();
        try
        {
            var request = args.Request;
            var referrer = request.Headers.Contains("Referer") ? request.Headers.GetHeader("Referer") : "";
            var generation = bridge.CurrentGeneration;
            if (!AllowsResource(sender, request.Uri, referrer, args.RequestedSourceKind) ||
                generation is null || request.Method is not ("GET" or "POST")) { return; }
            if (request.Method == "POST" && (!request.Headers.Contains("Origin") ||
                request.Headers.GetHeader("Origin") != session.Origin!.Value)) { return; }
            var mime = request.Headers.Contains("Content-Type") ? request.Headers.GetHeader("Content-Type") : "";
            var response = await generation.Transfers.HandleAsync(request.Method, uri.AbsolutePath, mime,
                request.Method == "POST" ? RequestStream(args) : null);
            if (!Trusted || !bridge.Enabled || !ReferenceEquals(generation, bridge.CurrentGeneration))
            {
                response.Content.Dispose();
                return;
            }
            generation.Start(() =>
            {
                args.Response = core.Environment.CreateWebResourceResponse(ResponseStream(response.Content), response.Status,
                    response.Status < 400 ? "OK" : "Rejected",
                    $"Content-Type: {response.ContentType}\r\nCache-Control: no-store\r\nX-Content-Type-Options: nosniff\r\n");
                return true;
            });
        }
        catch { Revoke(); }
        finally { deferral.Complete(); }
    }

    // WinUI uses the WinRT projection; the linked WinForms test host uses the .NET projection.
    private static NativeResponseStream ResponseStream(Stream value)
    {
#if VALORA_WINUI
        return value.AsRandomAccessStream();
#else
        return value;
#endif
    }

    private static Stream? RequestStream(CoreWebView2WebResourceRequestedEventArgs args)
    {
#if VALORA_WINUI
        return args.Request.Content?.AsStreamForRead();
#else
        return args.Request.Content;
#endif
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
        core.WebResourceRequested -= ResourceRequested;
        core.RemoveWebResourceRequestedFilter("*" + NativeTransfers.Prefix + "*", CoreWebView2WebResourceContext.All,
            CoreWebView2WebResourceRequestSourceKinds.All);
        bridge.Revoke();
        core.Settings.IsWebMessageEnabled = false;
    }
}
