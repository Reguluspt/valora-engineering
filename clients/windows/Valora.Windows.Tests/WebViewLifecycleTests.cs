using System.Text;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;
using Valora.Windows.App;
using Xunit;

namespace Valora.Windows.Tests;

public sealed class WebViewLifecycleTests
{
    [Theory]
    [InlineData((int)LifecycleSignal.Suspend, (int)LifecycleSignal.Resume)]
    [InlineData((int)LifecycleSignal.Disconnect, (int)LifecycleSignal.Reconnect)]
    public Task RebootstrapAfterFormMutationUsesFreshControlAndOnlyRootGet(int loss, int recovery) =>
        WebViewBoundaryTests.OnWebView(async oldView =>
        {
            var lifecycle = new ShellLifecycle(() => "https://valora.test");
            var oldSession = lifecycle.Begin(lifecycle.Session)!;
            var mutation = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
            var oldRequests = new List<string>();
            new TrustedWebViewBoundary(oldView.CoreWebView2, oldSession, () => { });
            oldView.CoreWebView2.AddWebResourceRequestedFilter("*", CoreWebView2WebResourceContext.Document,
                CoreWebView2WebResourceRequestSourceKinds.All);
            oldView.CoreWebView2.WebResourceRequested += (_, args) =>
            {
                oldRequests.Add(args.Request.Method);
                var isMutation = args.Request.Uri.EndsWith("/unknown-write", StringComparison.Ordinal);
                var html = isMutation ? "<p>Unknown outcome</p>" :
                    "<form id='write' method='post' action='/unknown-write'><input name='value' value='fixture'></form><script>document.getElementById('write').submit()</script>";
                args.Response = Response(oldView.CoreWebView2, html, 200,
                    "Content-Type: text/html\r\nSet-Cookie: lifecycle_fixture=present; Secure; SameSite=Strict; Path=/; Max-Age=300\r\n");
                if (isMutation)
                {
                    Assert.Equal("POST", args.Request.Method);
                    lifecycle.Signal((LifecycleSignal)loss);
                    mutation.TrySetResult();
                }
            };
            oldView.CoreWebView2.Navigate("https://valora.test/form");
            await mutation.Task.WaitAsync(TimeSpan.FromSeconds(10));
            Assert.Equal(ShellState.Closed, oldSession.State);
            var environment = oldView.CoreWebView2.Environment;
            var parent = oldView.Parent!;
            parent.Controls.Remove(oldView);
            oldView.Dispose();

            var freshSession = lifecycle.Begin(lifecycle.Signal((LifecycleSignal)recovery))!;
            using var freshView = new WebView2 { Dock = System.Windows.Forms.DockStyle.Fill };
            parent.Controls.Add(freshView);
            await freshView.EnsureCoreWebView2Async(environment);
            Assert.NotSame(oldView, freshView);
            var loaded = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
            new TrustedWebViewBoundary(freshView.CoreWebView2, freshSession, () =>
            {
                if (freshSession.State == ShellState.Loaded) { loaded.TrySetResult(); }
            });
            var freshRequests = new List<string>();
            freshView.CoreWebView2.AddWebResourceRequestedFilter("*", CoreWebView2WebResourceContext.Document,
                CoreWebView2WebResourceRequestSourceKinds.All);
            freshView.CoreWebView2.WebResourceRequested += (_, args) =>
            {
                freshRequests.Add(args.Request.Method + " " + args.Request.Uri);
                // Test-only public marker: browser persistence without native production cookie access.
                Assert.Contains("lifecycle_fixture=present", args.Request.Headers.GetHeader("Cookie"));
                args.Response = Response(freshView.CoreWebView2, "<p>Fresh server-hosted bootstrap</p>", 200);
            };
            freshView.CoreWebView2.Navigate(freshSession.Origin!.Value + "/");
            await loaded.Task.WaitAsync(TimeSpan.FromSeconds(10));
            Assert.Equal(new[] { "GET", "POST" }, oldRequests);
            Assert.Equal(new[] { "GET https://valora.test/" }, freshRequests);
            oldSession.NavigationCompleted(1, ShellState.Loaded);
            Assert.Equal(ShellState.Closed, oldSession.State);
            Assert.Equal(ShellState.Loaded, freshSession.State);
            Assert.True(lifecycle.IsCurrent(freshSession));
        });

    [Theory]
    [InlineData(200)]
    [InlineData(401)]
    [InlineData(403)]
    public Task ServerHostedLoginAndDeniedResponsesRemainBrowserOwned(int httpStatus) =>
        WebViewBoundaryTests.OnWebView(async view =>
        {
            var session = new ShellSession();
            session.Begin("https://valora.test");
            var completed = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
            var response = new TaskCompletionSource<int>(TaskCreationOptions.RunContinuationsAsynchronously);
            new TrustedWebViewBoundary(view.CoreWebView2, session, () =>
            {
                if (session.State == ShellState.Loaded) { completed.TrySetResult(); }
            });
            view.CoreWebView2.AddWebResourceRequestedFilter("*", CoreWebView2WebResourceContext.All,
                CoreWebView2WebResourceRequestSourceKinds.All);
            view.CoreWebView2.WebResourceRequested += (_, args) =>
                args.Response = args.Request.Uri.EndsWith("/session-response", StringComparison.Ordinal)
                    ? Response(view.CoreWebView2, "{}", httpStatus)
                    : Response(view.CoreWebView2, "<p>Server-hosted login</p><script>fetch('/session-response')</script>", 200);
            view.CoreWebView2.WebResourceResponseReceived += (_, args) =>
            {
                if (args.Request.Uri.EndsWith("/session-response", StringComparison.Ordinal))
                {
                    response.TrySetResult(args.Response.StatusCode);
                }
            };
            view.CoreWebView2.Navigate("https://valora.test/login");
            await completed.Task.WaitAsync(TimeSpan.FromSeconds(10));
            Assert.Equal(httpStatus, await response.Task.WaitAsync(TimeSpan.FromSeconds(10)));
            Assert.Equal(ShellState.Loaded, session.State); // Transport state, never an authentication verdict.
            Assert.Equal("https://valora.test/login", view.CoreWebView2.Source);
        });

    private static CoreWebView2WebResourceResponse Response(CoreWebView2 core, string html, int status,
        string headers = "Content-Type: text/html\r\n") =>
        core.Environment.CreateWebResourceResponse(new MemoryStream(Encoding.UTF8.GetBytes(html)), status,
            status == 200 ? "OK" : status == 401 ? "Unauthorized" : "Forbidden", headers);
}
