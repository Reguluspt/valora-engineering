using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Valora.Windows.Bridge;
using Microsoft.Web.WebView2.Core;
using System.Security.Cryptography;
using System.Text;

namespace Valora.Windows.App;

internal sealed class MainWindow : Window
{
    private ShellSession session = new();
    private readonly Grid layout = new() { RequestedTheme = ElementTheme.Light };
    private readonly TextBlock status = new() { TextWrapping = TextWrapping.Wrap, VerticalAlignment = VerticalAlignment.Center };
    private readonly Button retry = new() { Content = "Thử lại" };
    private readonly ProgressRing progress = new() { Width = 24, Height = 24 };
    private WebView2? webView;
    private bool starting;

    internal MainWindow(INativeCapabilityCatalog capabilities)
    {
        if (capabilities.EnabledCapabilities.Count != 0)
        {
            throw new InvalidOperationException("WIN-1 must not expose native capabilities.");
        }

        Title = "Valora";
        layout.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        layout.RowDefinitions.Add(new RowDefinition());
        var bar = new Grid { ColumnSpacing = 16, Margin = new Thickness(24) };
        bar.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        bar.ColumnDefinitions.Add(new ColumnDefinition());
        bar.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        Grid.SetColumn(status, 1);
        Grid.SetColumn(retry, 2);
        bar.Children.Add(progress);
        bar.Children.Add(status);
        bar.Children.Add(retry);
        layout.Children.Add(bar);
        Content = layout;
        layout.Loaded += async (_, _) => await StartAsync();
        retry.Click += async (_, _) => await StartAsync();
        Closed += (_, _) =>
        {
            session.Close();
            CloseWebView();
        };
        RenderState();
    }

    private async Task StartAsync()
    {
        if (starting || session.State == ShellState.Closed) { return; }
        starting = true;
        try
        {
            session.Close();
            CloseWebView();
            session = new ShellSession();
            if (!session.Begin(ServerConfiguration.Read())) { RenderState(); return; }
            RenderState();

            // Per-Windows-user, per-origin browser data; no native auth/identity authority.
            var originKey = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(session.Origin!.Value)));
            var profile = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "Valora", "WindowsClient", "WebView2", originKey);
            var options = new CoreWebView2EnvironmentOptions
            {
                ReleaseChannels = CoreWebView2ReleaseChannels.Stable
            };
            var environment = await CoreWebView2Environment.CreateWithOptionsAsync(null, profile, options);
            if (session.State == ShellState.Closed) { return; }
            if (!Version.TryParse(environment.BrowserVersionString.Split(' ')[0], out var runtime) || runtime.Major < 154)
            {
                throw new InvalidOperationException("Serviced Evergreen Runtime 154 or newer is required.");
            }
            var current = new WebView2 { Visibility = Visibility.Collapsed };
            webView = current;
            Grid.SetRow(current, 1);
            layout.Children.Add(current);
            await current.EnsureCoreWebView2Async(environment);
            if (session.State == ShellState.Closed || webView != current) { return; }
            new TrustedWebViewBoundary(current.CoreWebView2, session, () =>
            {
                if (webView == current) { RenderState(); }
            });
            current.CoreWebView2.Navigate(session.Origin!.Value + "/");
        }
        catch (Exception error) when (error is System.Runtime.InteropServices.COMException or
            InvalidOperationException or IOException or UnauthorizedAccessException or ArgumentException)
        {
            session.Fail(ShellState.InitializationFailure);
            RenderState();
        }
        finally
        {
            starting = false;
            if (session.State != ShellState.Closed) { RenderState(); }
        }
    }

    private void RenderState()
    {
        if (session.State == ShellState.Closed) { return; }
        status.Text = session.State switch
        {
            ShellState.NoConfiguration => "Chưa cấu hình máy chủ. Liên hệ quản trị viên rồi thử lại.",
            ShellState.InvalidConfiguration => "Cấu hình máy chủ không hợp lệ. Liên hệ quản trị viên rồi thử lại.",
            ShellState.Initializing => "Đang khởi tạo kết nối…",
            ShellState.Loading => "Đang tải Valora…",
            ShellState.Loaded => "Đã kết nối Valora.",
            ShellState.NavigationBlocked => "Đã chặn điều hướng không được phép. Thử lại để kết nối máy chủ.",
            ShellState.NetworkFailure => "Không kết nối được máy chủ. Kiểm tra mạng rồi thử lại.",
            ShellState.CertificateFailure => "Chứng chỉ máy chủ không hợp lệ. Liên hệ quản trị viên rồi thử lại.",
            ShellState.InitializationFailure => "Không khởi tạo được WebView2. Kiểm tra WebView2 Runtime rồi thử lại.",
            _ => "Không tải được Valora. Thử lại hoặc liên hệ quản trị viên."
        };
        var busy = session.State is ShellState.Initializing or ShellState.Loading;
        progress.IsActive = busy;
        progress.Visibility = busy ? Visibility.Visible : Visibility.Collapsed;
        retry.IsEnabled = !starting && !busy;
        retry.Visibility = session.State == ShellState.Loaded ? Visibility.Collapsed : Visibility.Visible;
        if (webView is not null)
        {
            webView.Visibility = session.State == ShellState.Loaded ? Visibility.Visible : Visibility.Collapsed;
            if (!session.CanNavigate)
            {
                // Defer control destruction out of the WebView callback; hide/revoke immediately.
                var failedView = webView;
                DispatcherQueue.TryEnqueue(() =>
                {
                    if (webView == failedView && !session.CanNavigate) { CloseWebView(); }
                });
            }
        }
    }

    private void CloseWebView()
    {
        if (webView is null) { return; }
        var previous = webView;
        webView = null;
        layout.Children.Remove(previous);
        previous.Close();
    }
}
