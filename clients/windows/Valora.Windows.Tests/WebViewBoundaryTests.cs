using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;
using System.Runtime.CompilerServices;
using System.Runtime.ExceptionServices;
using Valora.Windows.App;
using Xunit;

namespace Valora.Windows.Tests;

[Collection(nameof(WebViewCollection))]
public sealed class WebViewBoundaryTests
{
    [Theory]
    [InlineData("https://expired.badssl.com")]
    [InlineData("https://wrong.host.badssl.com")]
    [InlineData("https://self-signed.badssl.com")]
    public Task InvalidCertificatesFailClosedInRealWebView(string origin) => OnWebView(async webView =>
    {
        var session = new ShellSession();
        session.Begin(origin);
        var failed = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        new TrustedWebViewBoundary(webView.CoreWebView2, session, () =>
        {
            if (!session.CanNavigate) { failed.TrySetResult(); }
        });
        webView.CoreWebView2.Navigate(origin + "/");
        await failed.Task.WaitAsync(TimeSpan.FromSeconds(45));
        Assert.Equal(ShellState.CertificateFailure, session.State);
        Assert.False(session.CanNavigate);
    });

    [Fact]
    public Task RealHttpsNavigationUsesPlatformTls() => OnWebView(async webView =>
    {
        var session = new ShellSession();
        Assert.True(session.Begin("https://example.com"));
        var completed = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        new TrustedWebViewBoundary(webView.CoreWebView2, session, () =>
        {
            if (session.State is ShellState.Loaded or ShellState.CertificateFailure or
                ShellState.NetworkFailure or ShellState.NavigationFailure)
            {
                completed.TrySetResult();
            }
        });
        webView.CoreWebView2.Navigate("https://example.com/");
        await completed.Task.WaitAsync(TimeSpan.FromSeconds(45));
        Assert.Equal(ShellState.Loaded, session.State);
        Assert.StartsWith("https://example.com/", webView.CoreWebView2.Source);
        Assert.False(webView.CoreWebView2.Settings.IsWebMessageEnabled);
        Assert.False(webView.CoreWebView2.Settings.AreHostObjectsAllowed);
    });

    [Theory]
    [InlineData("http://valora.test/")]
    [InlineData("https://foreign.test/")]
    [InlineData("https://valora.test:8443/")]
    public Task ForeignNavigationIsCancelledByRealWebViewEvents(string destination) => OnWebView(async webView =>
    {
        var session = new ShellSession();
        session.Begin("https://valora.test");
        var blocked = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        new TrustedWebViewBoundary(webView.CoreWebView2, session, () =>
        {
            if (session.State == ShellState.NavigationBlocked) { blocked.TrySetResult(); }
        });
        webView.CoreWebView2.Navigate(destination);
        await blocked.Task.WaitAsync(TimeSpan.FromSeconds(10));
        Assert.Equal(ShellState.NavigationBlocked, session.State);
        Assert.False(session.CanNavigate);
    });

    [Theory]
    [InlineData("redirect")]
    [InlineData("popup")]
    [InlineData("frame")]
    [InlineData("srcdoc")]
    [InlineData("external")]
    public Task FixtureNavigationCannotEscapeTheBoundary(string kind) => OnWebView(async webView =>
    {
        var session = new ShellSession();
        session.Begin("https://valora.test");
        var blocked = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        new TrustedWebViewBoundary(webView.CoreWebView2, session, () =>
        {
            if (session.State == ShellState.NavigationBlocked) { blocked.TrySetResult(); }
        });
        webView.CoreWebView2.AddWebResourceRequestedFilter("*", CoreWebView2WebResourceContext.Document,
            CoreWebView2WebResourceRequestSourceKinds.All);
        webView.CoreWebView2.WebResourceRequested += (_, args) =>
        {
            Assert.StartsWith("https://valora.test/", args.Request.Uri);
            var html = kind switch
            {
                "popup" => "<script>window.open('https://foreign.test/', '_blank')</script>",
                "frame" => "<iframe src='https://foreign.test/'></iframe>",
                "srcdoc" => "<iframe srcdoc='untrusted content'></iframe>",
                "external" => "<script>location.href='valora-unregistered-test://foreign'</script>",
                _ => ""
            };
            // Browser-served test fixture; no host script injection or certificate override.
            var body = new MemoryStream(System.Text.Encoding.UTF8.GetBytes(html));
            args.Response = webView.CoreWebView2.Environment.CreateWebResourceResponse(body,
                kind == "redirect" ? 302 : 200, kind == "redirect" ? "Found" : "OK",
                kind == "redirect" ? "Location: https://foreign.test/\r\n" : "Content-Type: text/html\r\n");
        };
        webView.CoreWebView2.Navigate("https://valora.test/");
        await blocked.Task.WaitAsync(TimeSpan.FromSeconds(10));
        Assert.Equal(ShellState.NavigationBlocked, session.State);
        Assert.False(webView.CoreWebView2.Settings.IsWebMessageEnabled);
        Assert.False(webView.CoreWebView2.Settings.AreHostObjectsAllowed);
    });

    internal static Task OnWebView(Func<WebView2, Task> test, [CallerMemberName] string testName = "")
    {
        var trace = new WebViewFixtureTrace(testName);
        trace.Start();
        var result = new TaskCompletionSource<Exception?>(TaskCreationOptions.RunContinuationsAsynchronously);
        var thread = new Thread(() =>
        {
            Exception? failure = null;
            try
            {
                WebViewFixtureTrace.Current = trace;
                using var form = new System.Windows.Forms.Form { ShowInTaskbar = false, Opacity = 0 };
                using var webView = new WebView2 { Dock = System.Windows.Forms.DockStyle.Fill };
                trace.Write("control-created");
                webView.Disposed += (_, _) => trace.Write("control-disposed");
                form.FormClosed += (_, _) => trace.Write("form-closed");
                form.Controls.Add(webView);
                form.Shown += async (_, _) =>
                {
                    try
                    {
                        var options = new CoreWebView2EnvironmentOptions
                        {
                            ReleaseChannels = CoreWebView2ReleaseChannels.Stable
                        };
                        var profile = Path.Combine(Path.GetTempPath(), "Valora.Win1.Tests", Guid.NewGuid().ToString("N"));
                        trace.Write("environment-start", profile);
                        var environment = await CoreWebView2Environment.CreateAsync(null, profile, options);
                        trace.Write("environment-created", profile);
                        await webView.EnsureCoreWebView2Async(environment);
                        trace.Write("control-initialized", webView.CoreWebView2.BrowserProcessId);
                        trace.TrackBrowser(webView.CoreWebView2);
                        webView.CoreWebView2.NavigationStarting += (_, args) => trace.Write("navigation-start", new { args.NavigationId, args.Uri });
                        webView.CoreWebView2.NavigationCompleted += (_, args) => trace.Write("navigation-completed", new { args.NavigationId, args.IsSuccess, args.WebErrorStatus });
                        webView.CoreWebView2.WebResourceRequested += (_, args) => trace.Write("request-callback-entry", new { args.Request.Method, args.Request.Uri });
                        await test(webView);
                        trace.Write("test-body-result");
                    }
                    catch (Exception error)
                    {
                        trace.Write("test-body-exception", new { type = error.GetType().Name, error.Message });
                        failure = error;
                    }
                    finally
                    {
                        try
                        {
                            webView.Dispose();
                            // Keep the STA pump available for WebView shutdown callbacks after controller disposal.
                            await trace.WaitForBrowserRelease();
                        }
                        catch (Exception error)
                        {
                            failure = failure is null ? error : new AggregateException(failure, error);
                        }
                        finally
                        {
                            try { trace.Write("form-close-start"); form.Close(); }
                            catch (Exception error)
                            {
                                failure = failure is null ? error : new AggregateException(failure, error);
                                System.Windows.Forms.Application.ExitThread();
                            }
                        }
                    }
                };
                System.Windows.Forms.Application.Run(form);
                trace.Write("message-loop-ended");
            }
            catch (Exception error) { failure = failure is null ? error : new AggregateException(failure, error); }
            finally { result.TrySetResult(failure); }
        });
        thread.SetApartmentState(ApartmentState.STA);
        thread.IsBackground = true;
        thread.Start();
        return Complete().WaitAsync(TimeSpan.FromSeconds(60));

        async Task Complete()
        {
            try
            {
                var failure = await result.Task;
                if (!thread.Join(TimeSpan.FromSeconds(10))) { throw new TimeoutException("Fixture STA did not exit."); }
                trace.Write(failure is null ? "owning-task-result" : "owning-task-exception",
                    failure is null ? null : new { type = failure.GetType().Name, failure.Message });
                if (failure is not null) { ExceptionDispatchInfo.Capture(failure).Throw(); }
            }
            finally { trace.End(); }
        }
    }
}
