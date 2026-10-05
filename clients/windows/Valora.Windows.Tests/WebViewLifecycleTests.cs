using System.Runtime.InteropServices;
using System.Text;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;
using Valora.Windows.App;
using Xunit;
using Xunit.Abstractions;

namespace Valora.Windows.Tests;

[Collection(nameof(WebViewCollection))]
public sealed class WebViewLifecycleTests
{
    private readonly ITestOutputHelper output;

    public WebViewLifecycleTests(ITestOutputHelper output) { this.output = output; }

    [Fact]
    public async Task OwningTaskWaitsForControlDisposalAndBrowserRelease()
    {
        using var releaseClose = new ManualResetEventSlim();
        var closing = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        WebView2? ownedView = null;
        System.Diagnostics.Process? browser = null;
        var running = WebViewBoundaryTests.OnWebView(view =>
        {
            ownedView = view;
            browser = System.Diagnostics.Process.GetProcessById(checked((int)view.CoreWebView2.BrowserProcessId));
            view.FindForm()!.FormClosed += (_, _) =>
            {
                closing.TrySetResult();
                releaseClose.Wait(TimeSpan.FromSeconds(10));
            };
            return Task.CompletedTask;
        });
        try
        {
            await closing.Task.WaitAsync(TimeSpan.FromSeconds(10));
            try { Assert.False(running.IsCompleted, "The owning task completed while form teardown was blocked."); }
            finally { releaseClose.Set(); }
            await running;
            Assert.True(ownedView!.IsDisposed);
            Assert.True(browser!.HasExited);
        }
        finally { releaseClose.Set(); browser?.Dispose(); }
    }

    [Theory]
    [InlineData((int)LifecycleSignal.Suspend, (int)LifecycleSignal.Resume)]
    [InlineData((int)LifecycleSignal.Disconnect, (int)LifecycleSignal.Reconnect)]
    public Task RebootstrapAfterFormMutationUsesFreshControlAndOnlyRootGet(int loss, int recovery) =>
        WebViewBoundaryTests.OnWebView(async oldView =>
        {
            var events = new WebViewTestDiagnostics();
            try
            {
                var lifecycle = new ShellLifecycle(() => "https://valora.test");
                var oldSession = lifecycle.Begin(lifecycle.Session)!;
                var mutation = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
                var oldRequests = new List<string>();
                new TrustedWebViewBoundary(oldView.CoreWebView2, oldSession, () => events.Capture(() =>
                    events.Record($"old state={oldSession.State}")));
                oldView.CoreWebView2.NavigationStarting += (_, args) => events.Capture(() =>
                    events.Record($"old NavigationStarting id={args.NavigationId} uri={args.Uri}"));
                oldView.CoreWebView2.NavigationCompleted += (_, args) => events.Capture(() =>
                    events.Record($"old NavigationCompleted id={args.NavigationId} success={args.IsSuccess}"));
                oldView.CoreWebView2.WebResourceResponseReceived += (_, args) => events.Capture(() =>
                    events.Record($"old response received uri={args.Request.Uri} status={args.Response.StatusCode}"));
                oldView.CoreWebView2.AddWebResourceRequestedFilter("*", CoreWebView2WebResourceContext.Document,
                    CoreWebView2WebResourceRequestSourceKinds.All);
                oldView.CoreWebView2.WebResourceRequested += (_, args) => events.Capture(() =>
                {
                    events.Record($"old request {args.Request.Method} {args.Request.Uri}");
                    oldRequests.Add(args.Request.Method);
                    var isMutation = args.Request.Uri.EndsWith("/unknown-write", StringComparison.Ordinal);
                    if (isMutation)
                    {
                        Assert.Equal("POST", args.Request.Method);
                        using var body = new StreamReader(args.Request.Content, Encoding.UTF8, true, 1024, leaveOpen: true);
                        // The browser page reads the public cookie before submitting, proving commit before loss.
                        Assert.Equal("value=fixture&cookie_proof=lifecycle_fixture=present",
                            Uri.UnescapeDataString(body.ReadToEnd()));
                        events.Record("old browser page proved cookie commit in POST body");
                        args.Response = Response(oldView.CoreWebView2, "<p>Unknown outcome</p>", 200);
                        events.Record("old mutation response constructed without Set-Cookie");
                        lifecycle.Signal((LifecycleSignal)loss);
                        events.Record($"loss={(LifecycleSignal)loss}; old state={oldSession.State}");
                        mutation.TrySetResult();
                    }
                    else
                    {
                        Assert.Equal("GET", args.Request.Method);
                        Assert.Equal("https://valora.test/form", args.Request.Uri);
                        var html = "<form id='write' method='post' action='/unknown-write'>" +
                            "<input name='value' value='fixture'><input id='cookie' name='cookie_proof'></form>" +
                            "<script>document.getElementById('cookie').value=document.cookie;" +
                            "document.getElementById('write').submit()</script>";
                        args.Response = Response(oldView.CoreWebView2, html, 200,
                            "Content-Type: text/html\r\nSet-Cookie: lifecycle_fixture=present; Secure; SameSite=Strict; Path=/; Max-Age=300\r\n");
                        events.Record("old form response constructed with Set-Cookie");
                    }
                });
                oldView.CoreWebView2.Navigate("https://valora.test/form");
                await events.Wait(mutation.Task);
                Assert.Equal(ShellState.Closed, oldSession.State);
                var environment = oldView.CoreWebView2.Environment;
                var browserExited = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
                EventHandler<CoreWebView2BrowserProcessExitedEventArgs> onBrowserExited = (_, args) => events.Capture(() =>
                {
                    events.Record($"old browser exited pid={args.BrowserProcessId} kind={args.BrowserProcessExitKind}");
                    Assert.Equal(CoreWebView2BrowserProcessExitKind.Normal, args.BrowserProcessExitKind);
                    browserExited.TrySetResult();
                });
                var profile = environment.UserDataFolder;
                var parent = oldView.Parent!;
                environment.BrowserProcessExited += onBrowserExited;
                try
                {
                    parent.Controls.Remove(oldView);
                    events.Record("old control removed");
                    oldView.Dispose();
                    events.Record("old control disposed");
                    // The isolated fixture owns the last control; wait for profile resources to be released.
                    await events.Wait(browserExited.Task);
                }
                finally { environment.BrowserProcessExited -= onBrowserExited; }

                var freshSession = lifecycle.Begin(lifecycle.Signal((LifecycleSignal)recovery))!;
                events.Record($"recovery={(LifecycleSignal)recovery}; fresh Begin state={freshSession.State}");
                Assert.NotSame(oldSession, freshSession);
                using var freshView = new WebView2 { Dock = System.Windows.Forms.DockStyle.Fill };
                parent.Controls.Add(freshView);
                var freshEnvironment = await events.Wait(CoreWebView2Environment.CreateAsync(null, profile,
                    new CoreWebView2EnvironmentOptions { ReleaseChannels = CoreWebView2ReleaseChannels.Stable }));
                Assert.Equal(profile, freshEnvironment.UserDataFolder);
                await freshView.EnsureCoreWebView2Async(freshEnvironment);
                WebViewFixtureTrace.Current!.TrackBrowser(freshView.CoreWebView2);
                events.Record($"fresh control initialized pid={freshView.CoreWebView2.BrowserProcessId}");
                Assert.NotSame(oldView, freshView);
                var loaded = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
                new TrustedWebViewBoundary(freshView.CoreWebView2, freshSession, () => events.Capture(() =>
                {
                    events.Record($"fresh state={freshSession.State}");
                    Assert.True(freshSession.CanNavigate, $"Fresh bootstrap failed: {freshSession.State}");
                    if (freshSession.State == ShellState.Loaded) { loaded.TrySetResult(); }
                }));
                freshView.CoreWebView2.NavigationStarting += (_, args) => events.Capture(() =>
                    events.Record($"fresh NavigationStarting id={args.NavigationId} uri={args.Uri}"));
                freshView.CoreWebView2.NavigationCompleted += (_, args) => events.Capture(() =>
                {
                    events.Record($"fresh NavigationCompleted success={args.IsSuccess} error={args.WebErrorStatus}");
                    Assert.True(args.IsSuccess, $"Fresh navigation failed: {args.WebErrorStatus}");
                });
                var freshRequests = new List<string>();
                freshView.CoreWebView2.AddWebResourceRequestedFilter("*", CoreWebView2WebResourceContext.Document,
                    CoreWebView2WebResourceRequestSourceKinds.All);
                freshView.CoreWebView2.WebResourceRequested += (_, args) => events.Capture(() =>
                {
                    freshRequests.Add(args.Request.Method + " " + args.Request.Uri);
                    events.Record($"fresh request {args.Request.Method} {args.Request.Uri}");
                    // Cookie headers may be added AFTER this event; always provide the synthetic response.
                    args.Response = Response(freshView.CoreWebView2, "<p>Fresh server-hosted bootstrap</p>", 200);
                    events.Record("fresh response constructed");
                });
                freshView.CoreWebView2.Navigate(freshSession.Origin!.Value + "/");
                await events.Wait(loaded.Task);
                // Read only this public marker in the isolated test profile, never production authentication cookies.
                var cookies = await events.Wait(freshView.CoreWebView2.CookieManager.GetCookiesAsync("https://valora.test/"));
                var cookie = Assert.Single(cookies);
                Assert.Equal("lifecycle_fixture", cookie.Name);
                Assert.Equal("present", cookie.Value);
                Assert.Equal("valora.test", cookie.Domain);
                Assert.Equal("/", cookie.Path);
                Assert.True(cookie.IsSecure);
                Assert.Equal(CoreWebView2CookieSameSiteKind.Strict, cookie.SameSite);
                events.Record("fresh browser store proved cookie/profile continuity");
                Assert.Equal(new[] { "GET", "POST" }, oldRequests);
                Assert.Equal(new[] { "GET https://valora.test/" }, freshRequests);
                oldSession.NavigationCompleted(1, ShellState.Loaded);
                Assert.Equal(ShellState.Closed, oldSession.State);
                Assert.Equal(ShellState.Loaded, freshSession.State);
                Assert.True(lifecycle.IsCurrent(freshSession));
                events.Record($"final state={freshSession.State}");
                await events.Wait(Task.CompletedTask);
            }
            catch
            {
                output.WriteLine(events.Trace);
                throw;
            }
        });

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task RequestCallbackFailureReachesOwningTest(bool assertionFailure)
    {
        Exception expected = assertionFailure ? new Xunit.Sdk.XunitException("Fixture callback assertion") :
            new COMException("Fixture missing header", unchecked((int)0x80070490));
        var actual = await Record.ExceptionAsync(() => WebViewBoundaryTests.OnWebView(async view =>
        {
            var events = new WebViewTestDiagnostics();
            var unanswered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
            view.CoreWebView2.AddWebResourceRequestedFilter("*", CoreWebView2WebResourceContext.Document,
                CoreWebView2WebResourceRequestSourceKinds.All);
            view.CoreWebView2.WebResourceRequested += (_, _) => events.Capture(() => throw expected);
            view.CoreWebView2.Navigate("https://valora.test/");
            await events.Wait(unanswered.Task);
        }));
        Assert.Same(expected, actual);
    }

    [Theory]
    [InlineData(200)]
    [InlineData(401)]
    [InlineData(403)]
    public Task ServerHostedLoginAndDeniedResponsesRemainBrowserOwned(int httpStatus) =>
        WebViewBoundaryTests.OnWebView(async view =>
        {
            var events = new WebViewTestDiagnostics();
            var session = new ShellSession();
            session.Begin("https://valora.test");
            var completed = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
            var response = new TaskCompletionSource<int>(TaskCreationOptions.RunContinuationsAsynchronously);
            new TrustedWebViewBoundary(view.CoreWebView2, session, () => events.Capture(() =>
            {
                if (session.State == ShellState.Loaded) { completed.TrySetResult(); }
            }));
            view.CoreWebView2.AddWebResourceRequestedFilter("*", CoreWebView2WebResourceContext.All,
                CoreWebView2WebResourceRequestSourceKinds.All);
            view.CoreWebView2.WebResourceRequested += (_, args) => events.Capture(() =>
                args.Response = args.Request.Uri.EndsWith("/session-response", StringComparison.Ordinal)
                    ? Response(view.CoreWebView2, "{}", httpStatus)
                    : Response(view.CoreWebView2, "<p>Server-hosted login</p><script>fetch('/session-response')</script>", 200));
            view.CoreWebView2.WebResourceResponseReceived += (_, args) => events.Capture(() =>
            {
                if (args.Request.Uri.EndsWith("/session-response", StringComparison.Ordinal))
                {
                    response.TrySetResult(args.Response.StatusCode);
                }
            });
            view.CoreWebView2.Navigate("https://valora.test/login");
            await events.Wait(completed.Task);
            Assert.Equal(httpStatus, await events.Wait(response.Task));
            Assert.Equal(ShellState.Loaded, session.State); // Transport state, never an authentication verdict.
            Assert.Equal("https://valora.test/login", view.CoreWebView2.Source);
            await events.Wait(Task.CompletedTask);
        });

    private static CoreWebView2WebResourceResponse Response(CoreWebView2 core, string html, int status,
        string headers = "Content-Type: text/html\r\n") =>
        core.Environment.CreateWebResourceResponse(new MemoryStream(Encoding.UTF8.GetBytes(html)), status,
            status == 200 ? "OK" : status == 401 ? "Unauthorized" : "Forbidden", headers);
}
