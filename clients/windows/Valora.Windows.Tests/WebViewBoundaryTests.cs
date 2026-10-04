using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;
using Valora.Windows.App;
using Xunit;

namespace Valora.Windows.Tests;

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

    private static Task OnWebView(Func<WebView2, Task> test)
    {
        var result = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var thread = new Thread(() =>
        {
            using var form = new System.Windows.Forms.Form { ShowInTaskbar = false, Opacity = 0 };
            using var webView = new WebView2 { Dock = System.Windows.Forms.DockStyle.Fill };
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
                    var environment = await CoreWebView2Environment.CreateAsync(null, profile, options);
                    await webView.EnsureCoreWebView2Async(environment);
                    await test(webView);
                    result.TrySetResult();
                }
                catch (Exception error) { result.TrySetException(error); }
                finally { form.Close(); }
            };
            System.Windows.Forms.Application.Run(form);
        });
        thread.SetApartmentState(ApartmentState.STA);
        thread.IsBackground = true;
        thread.Start();
        return result.Task.WaitAsync(TimeSpan.FromSeconds(60));
    }
}
