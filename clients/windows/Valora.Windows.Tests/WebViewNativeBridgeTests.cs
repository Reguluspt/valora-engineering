using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;
using System.Text;
using System.Text.Json;
using System.Runtime.CompilerServices;
using Valora.Windows.App;
using Valora.Windows.Bridge;
using Xunit;

namespace Valora.Windows.Tests;

[Collection(nameof(WebViewCollection))]
public sealed class WebViewNativeBridgeTests
{
    private const string HelloId = "1be17b37-6f4d-4335-8a74-83c56d40f0e4";
    private const string PickId = "0e7dc4f2-431f-44ef-a33f-d7c29cdce01b";
    private static readonly string Fixture = """
        <script>
        const hello = {protocol:'valora.native/1',type:'request',requestId:'1be17b37-6f4d-4335-8a74-83c56d40f0e4',capability:'hello',payload:{}};
        const pick = {...hello,requestId:'0e7dc4f2-431f-44ef-a33f-d7c29cdce01b',capability:'pickExcelFile'};
        chrome.webview.addEventListener('message', e => {
          if(e.data.requestId === hello.requestId && e.data.ok) chrome.webview.postMessage(pick);
          if(e.data.requestId === pick.requestId) chrome.webview.postMessage({fixtureAck:e.data});
        });
        addEventListener('load',()=>setTimeout(()=>chrome.webview.postMessage(hello),50));
        </script>
        """;

    private static async Task FixtureTest(Func<WebView2, ShellSession, NativeBridgeSession, WebViewNativeBridge, Task> test,
        TestNativePlatform platform, string html = "", Func<bool>? isCurrent = null, Action<Action>? enqueue = null,
        [CallerMemberName] string testName = "")
    {
        await WebViewBoundaryTests.OnWebView(async view =>
        {
            var core = view.CoreWebView2;
            var session = new ShellSession(); session.Begin("https://valora.test");
            var bridge = new NativeBridgeSession(platform);
            var context = SynchronizationContext.Current!;
            using var native = new WebViewNativeBridge(core, session, bridge, isCurrent ?? (() => true), enqueue ?? (action => context.Post(_ => action(), null)));
            var loaded = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
            new TrustedWebViewBoundary(core, session, () => { if (session.State == ShellState.Loaded) loaded.TrySetResult(); }, native);
            Assert.False(core.Settings.IsWebMessageEnabled); Assert.False(bridge.Enabled);
            core.AddWebResourceRequestedFilter("*", CoreWebView2WebResourceContext.Document, CoreWebView2WebResourceRequestSourceKinds.All);
            core.WebResourceRequested += (_, args) =>
            {
                if (new Uri(args.Request.Uri).AbsolutePath.StartsWith(NativeTransfers.Prefix, StringComparison.Ordinal)) return;
                args.Response = core.Environment.CreateWebResourceResponse(
                    new MemoryStream(Encoding.UTF8.GetBytes(args.Request.Uri.EndsWith("/next") ? "next document" : html)),
                    200, "OK", "Content-Type: text/html\r\n");
            };
            core.Navigate("https://valora.test/");
            await loaded.Task.WaitAsync(TimeSpan.FromSeconds(10));
            Assert.True(bridge.Enabled); Assert.True(core.Settings.IsWebMessageEnabled);
            await test(view, session, bridge, native);
        }, testName);
    }

    [Fact]
    public Task RealFetchTransfersAndCapturesWithoutNetworkOrAuthentication() => FixtureTest(async (view, _, bridge, native) =>
    {
        var core = view.CoreWebView2;
        Assert.True(NativeBridgeTests.Parse(await bridge.DispatchAsync(NativeTransferTests.Request())).GetProperty("ok").GetBoolean());
        var owner = bridge.CurrentGeneration!;
        var picked = NativeBridgeTests.Parse(await bridge.DispatchAsync(NativeTransferTests.Request("pickExcelFile"))).GetProperty("result");
        var prepared = NativeBridgeTests.Parse(await bridge.DispatchAsync(NativeTransferTests.Request("prepareSelectedFileTransfer",
            new { handle = picked.GetProperty("handle").GetString() }))).GetProperty("result").GetProperty("url").GetString()!;
        var capture = owner.Transfers.PrepareCapture(NativeTransferTests.Metadata([0, 255, 1, 99]));
        var requests = new List<string>();
        core.WebResourceRequested += (_, args) =>
        {
            if (new Uri(args.Request.Uri).AbsolutePath.StartsWith(NativeTransfers.Prefix, StringComparison.Ordinal))
            {
                requests.Add(args.Request.Uri);
                Assert.False(args.Request.Headers.Contains("Cookie"));
                Assert.False(args.Request.Headers.Contains("Authorization"));
                Assert.False(args.Request.Headers.Contains("X-CSRF-Token"));
            }
        };
        var script = $$"""
            (async()=>{
              const opts={credentials:'omit',mode:'same-origin',redirect:'error',cache:'no-store',referrer:location.href,referrerPolicy:'same-origin'};
              const selected=await fetch({{JsonSerializer.Serialize(prepared)}},{...opts,method:'GET'});
              const bytes=Array.from(new Uint8Array(await selected.arrayBuffer()));
              const replay=await fetch({{JsonSerializer.Serialize(prepared)}},{...opts,method:'GET'});
              const captured=await fetch({{JsonSerializer.Serialize(capture)}},{...opts,method:'POST',
                headers:{'Content-Type':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'},body:new Uint8Array(bytes)});
              return {selected:selected.status,bytes,replay:replay.status,replaySize:(await replay.arrayBuffer()).byteLength,
                captured:captured.status,artifact:await captured.json(),cache:selected.headers.get('Cache-Control')};
            })()
            """;
        // ExecuteScriptAsync does not await JavaScript promises; the result is returned through a fixture message.
        var ack = new TaskCompletionSource<JsonElement>(TaskCreationOptions.RunContinuationsAsynchronously);
        core.WebMessageReceived += (_, args) =>
        {
            var value = NativeBridgeTests.Parse(args.WebMessageAsJson);
            if (value.TryGetProperty("transferAck", out var result)) ack.TrySetResult(result);
            if (value.TryGetProperty("transferError", out var error)) ack.TrySetException(new Exception(error.GetString()));
        };
        await core.ExecuteScriptAsync(script + ".then(value=>chrome.webview.postMessage({transferAck:value})).catch(error=>chrome.webview.postMessage({transferError:String(error)}));");
        var actual = await ack.Task.WaitAsync(TimeSpan.FromSeconds(15));
        Assert.Equal(200, actual.GetProperty("selected").GetInt32());
        Assert.Equal(new[] { 0, 255, 1, 99 }, actual.GetProperty("bytes").EnumerateArray().Select(v => v.GetInt32()));
        Assert.Equal(404, actual.GetProperty("replay").GetInt32());
        Assert.Equal(0, actual.GetProperty("replaySize").GetInt32());
        Assert.Equal(201, actual.GetProperty("captured").GetInt32());
        Assert.Equal("no-store", actual.GetProperty("cache").GetString());
        Assert.Equal(3, requests.Count);
        var handle = actual.GetProperty("artifact").GetProperty("artifactHandle").GetString()!;
        Assert.IsType<CapturedNativeArtifact>(owner.Resolve(handle, false, true));
        Assert.True(native.AllowsResource(core, "https://valora.test" + prepared, core.Source, CoreWebView2WebResourceRequestSourceKinds.Document));
        bridge.Revoke();
        Assert.Throws<NativeBridgeException>(() => owner.Resolve(handle, false, true));
    }, new TestNativePlatform
    {
        EnabledCapabilities = NativeProtocol.V2Capabilities,
        Selection = new ReadableTestFile([0, 255, 1, 99])
    });

    [Fact]
    public Task ResourceBoundaryRejectsForeignOriginWorkerStaleControlAndClosedSession() => FixtureTest((view, session, bridge, native) =>
    {
        var core = view.CoreWebView2;
        var url = "https://valora.test" + NativeTransfers.Prefix + "selected/" + new string('a', 48);
        Assert.True(native.AllowsResource(core, url, core.Source, CoreWebView2WebResourceRequestSourceKinds.Document));
        Assert.False(native.AllowsResource(new object(), url, core.Source, CoreWebView2WebResourceRequestSourceKinds.Document));
        foreach (var origin in new[] { "http://valora.test", "https://foreign.test", "https://valora.test:8443" })
            Assert.False(native.AllowsResource(core, origin + NativeTransfers.Prefix, core.Source, CoreWebView2WebResourceRequestSourceKinds.Document));
        Assert.False(native.AllowsResource(core, url, "https://valora.test/old", CoreWebView2WebResourceRequestSourceKinds.Document));
        Assert.False(native.AllowsResource(core, url + "?extra=1", core.Source, CoreWebView2WebResourceRequestSourceKinds.Document));
        Assert.False(native.AllowsResource(core, url, core.Source, CoreWebView2WebResourceRequestSourceKinds.ServiceWorker));
        Assert.False(native.AllowsResource(core, url, core.Source, CoreWebView2WebResourceRequestSourceKinds.SharedWorker));
        session.Close();
        Assert.False(bridge.Enabled);
        Assert.False(native.AllowsResource(core, url, core.Source, CoreWebView2WebResourceRequestSourceKinds.Document));
        return Task.CompletedTask;
    }, new TestNativePlatform());

    [Fact]
    public Task RealTrustedDocumentNegotiatesAndReceivesNormalPickerCancellation() => FixtureTest(async (view, _, bridge, _) =>
    {
        var ack = new TaskCompletionSource<JsonElement>(TaskCreationOptions.RunContinuationsAsynchronously);
        view.CoreWebView2.WebMessageReceived += (_, args) =>
        {
            var value = NativeBridgeTests.Parse(args.WebMessageAsJson);
            if (value.TryGetProperty("fixtureAck", out var result)) ack.TrySetResult(result);
        };
        var response = await ack.Task.WaitAsync(TimeSpan.FromSeconds(10));
        Assert.Equal(PickId, response.GetProperty("requestId").GetString());
        Assert.False(response.GetProperty("result").GetProperty("selected").GetBoolean());
        Assert.True(bridge.CurrentGeneration!.Active);
    }, new TestNativePlatform(), Fixture);

    [Fact]
    public Task SenderChecksRequireCurrentControlSessionDocumentAndExactHttpsOrigin() => FixtureTest((view, session, bridge, native) =>
    {
        var core = view.CoreWebView2;
        Assert.True(native.AllowsSender(core, "https://valora.test/"));
        foreach (var source in new[] { "http://valora.test/", "https://foreign.test/", "https://valora.test:8443/", "https://valora.test/old", "https://valora.test@evil.test/" })
        {
            Assert.False(native.AllowsSender(core, source));
        }
        Assert.False(native.AllowsSender(new object(), "https://valora.test/"));
        session.Close();
        Assert.False(bridge.Enabled);
        Assert.False(native.AllowsSender(core, "https://valora.test/"));
        native.Enable(); Assert.False(bridge.Enabled);
        return Task.CompletedTask;
    }, new TestNativePlatform());

    [Fact]
    public Task NavigationRevokesInFlightRequestAndCannotAdoptStalePickerCompletion()
    {
        var platform = new TestNativePlatform { DelayedPicker = new(TaskCreationOptions.RunContinuationsAsynchronously) };
        return FixtureTest(async (view, session, bridge, _) =>
        {
            var deadline = DateTime.UtcNow.AddSeconds(10);
            while (platform.Picks == 0 && DateTime.UtcNow < deadline) await Task.Delay(10);
            Assert.Equal(1, platform.Picks);
            var old = bridge.CurrentGeneration!;
            var revoked = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
            view.CoreWebView2.NavigationStarting += (_, _) =>
            {
                Assert.False(old.Active); Assert.False(bridge.Enabled);
                Assert.False(view.CoreWebView2.Settings.IsWebMessageEnabled);
                revoked.TrySetResult();
            };
            view.CoreWebView2.Navigate("https://valora.test/next");
            await revoked.Task.WaitAsync(TimeSpan.FromSeconds(10));
            platform.DelayedPicker.SetResult(new TestNativeFile());
            await Task.Delay(50);
            Assert.Throws<NativeBridgeException>(() => old.Register(new TestNativeFile(), new("a.xlsx", ".xlsx", 1)));
            Assert.Equal(0, platform.Opens);
            Assert.NotEqual(ShellState.NavigationBlocked, session.State);
        }, platform, Fixture);
    }

    [Fact]
    public Task LifecycleThreadRevokesBeforeQueuedBrowserContinuation() => FixtureTest(async (_, session, bridge, _) =>
    {
        await bridge.DispatchAsync(NativeBridgeTests.Request(id: HelloId));
        var old = bridge.CurrentGeneration!;
        await Task.Run(session.Close);
        Assert.False(old.Active); Assert.False(bridge.Enabled);
        NativeBridgeTests.Error(await bridge.DispatchAsync(NativeBridgeTests.Request("pickExcelFile")), NativeError.NOT_TRUSTED);
    }, new TestNativePlatform());

    [Fact]
    public Task ReplacedControlCannotDispatchOrReenableEvenWithSameLoadedOrigin()
    {
        var current = true;
        return FixtureTest((view, _, bridge, native) =>
        {
            current = false;
            Assert.False(native.AllowsSender(view.CoreWebView2, "https://valora.test/"));
            native.Enable();
            Assert.False(bridge.Enabled);
            return Task.CompletedTask;
        }, new TestNativePlatform(), isCurrent: () => current);
    }

    [Fact]
    public Task QueuedNativeEventsCannotReachAReplacementGeneration()
    {
        var queued = new Queue<Action>();
        const string html = "<script>chrome.webview.addEventListener('message',e=>{if(e.data.type==='event')chrome.webview.postMessage({seenEvent:e.data})})</script>";
        return FixtureTest(async (view, _, bridge, native) =>
        {
            var received = new List<JsonElement>();
            view.CoreWebView2.WebMessageReceived += (_, args) =>
            {
                var value = NativeBridgeTests.Parse(args.WebMessageAsJson);
                if (value.TryGetProperty("seenEvent", out var message)) received.Add(message.Clone());
            };
            await bridge.DispatchAsync(NativeBridgeTests.Request(id: HelloId));
            await bridge.MediateDropAsync(new[] { new TestNativeFile("old.xlsx") }, bridge.CurrentGeneration!);
            bridge.Revoke();
            native.Enable();
            await bridge.DispatchAsync(NativeBridgeTests.Request(id: HelloId));
            while (queued.TryDequeue(out var action)) action();
            await Task.Delay(75);
            Assert.Empty(received);
            await bridge.MediateDropAsync(new[] { new TestNativeFile("current.xlsx") }, bridge.CurrentGeneration!);
            while (queued.TryDequeue(out var action)) action();
            var deadline = DateTime.UtcNow.AddSeconds(10);
            while (received.Count == 0 && DateTime.UtcNow < deadline) await Task.Delay(10);
            var current = Assert.Single(received);
            Assert.Equal("filesDropped", current.GetProperty("event").GetString());
            Assert.Equal("current.xlsx", current.GetProperty("payload").GetProperty("name").GetString());
        }, new TestNativePlatform(), html, enqueue: queued.Enqueue);
    }

    [Theory]
    [InlineData("https://valora.test/frame")]
    [InlineData("https://foreign.test/frame")]
    public Task ChildFrameRevokesPreviouslyLoadedNativeCapabilitySurface(string source)
    {
        var platform = new TestNativePlatform();
        var html = "<body><script>addEventListener('load',()=>setTimeout(()=>{const f=document.createElement('iframe');f.src='" + source + "';document.body.appendChild(f)},75));</script></body>";
        return FixtureTest(async (view, session, bridge, _) =>
        {
            var deadline = DateTime.UtcNow.AddSeconds(10);
            while (session.State == ShellState.Loaded && DateTime.UtcNow < deadline) await Task.Delay(10);
            Assert.Equal(ShellState.NavigationBlocked, session.State);
            Assert.False(bridge.Enabled);
            Assert.Equal(0, platform.Picks);
            await Task.Delay(10);
            Assert.False(view.CoreWebView2.Settings.IsWebMessageEnabled);
        }, platform, html);
    }
}
