using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Valora.Windows.Bridge;
using Microsoft.Web.WebView2.Core;
using Windows.ApplicationModel.DataTransfer;
using Windows.Storage;

namespace Valora.Windows.App;

internal sealed class MainWindow : Window
{
    private readonly ShellLifecycle lifecycle;
    private readonly ILifecycleEvents lifecycleEvents;
    private readonly Grid layout = new() { RequestedTheme = ElementTheme.Light };
    private readonly TextBlock status = new() { TextWrapping = TextWrapping.Wrap, VerticalAlignment = VerticalAlignment.Center };
    private readonly Button retry = new() { Content = "Thử lại" };
    private readonly ProgressRing progress = new() { Width = 24, Height = 24 };
    private WebView2? webView;
    private ShellSession? viewSession;
    private NativeBridgeSession? bridge;
    private WebViewNativeBridge? native;

    internal MainWindow()
    {
        lifecycleEvents = new WindowsLifecycleEvents();
        lifecycle = new ShellLifecycle(ServerConfiguration.Read, lifecycleEvents.NetworkAvailable);
        lifecycleEvents.Changed += LifecycleChanged;

        Title = "Valora";
        layout.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        layout.RowDefinitions.Add(new RowDefinition());
        var bar = new Grid { ColumnSpacing = 16, Margin = new Thickness(24) };
        bar.AllowDrop = true;
        bar.DragOver += (_, args) =>
        {
            args.Handled = true;
            args.AcceptedOperation = bridge?.Enabled == true && args.DataView.Contains(StandardDataFormats.StorageItems)
                ? DataPackageOperation.Copy : DataPackageOperation.None;
        };
        bar.Drop += async (_, args) =>
        {
            args.Handled = true;
            var expectedBridge = bridge;
            var expectedGeneration = expectedBridge?.CurrentGeneration;
            if (expectedBridge?.Enabled != true || expectedGeneration is null || !args.DataView.Contains(StandardDataFormats.StorageItems)) { return; }
            try
            {
                var items = await args.DataView.GetStorageItemsAsync();
                if (items.Count != 1 || items[0] is not StorageFile file) { return; }
                await expectedBridge.MediateDropAsync(new INativeFile[] { new WindowsNativeFile(file) }, expectedGeneration);
            }
            catch (Exception error) when (error is NativeBridgeException or OperationCanceledException or
                System.Runtime.InteropServices.COMException or UnauthorizedAccessException or IOException) { }
        };
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
            lifecycle.Close();
            lifecycleEvents.Changed -= LifecycleChanged;
            lifecycleEvents.Dispose();
            CloseWebView();
        };
        RenderState();
    }

    private void LifecycleChanged(LifecycleSignal signal)
    {
        var expected = lifecycle.Signal(signal);
        DispatcherQueue.TryEnqueue(Microsoft.UI.Dispatching.DispatcherQueuePriority.High, async () =>
        {
            if (!lifecycle.IsCurrent(expected)) { return; }
            CloseWebView();
            RenderState();
            if (expected.State == ShellState.Revalidating) { await StartAsync(expected); }
        });
    }

    private async Task StartAsync(ShellSession? expected = null)
    {
        expected ??= lifecycle.Session;
        if (expected.State is ShellState.Initializing or ShellState.Loading) { return; }
        var owned = lifecycle.Begin(expected);
        if (owned is null) { return; }
        try
        {
            CloseWebView();
            RenderState();
            var origin = owned.Origin;
            if (origin is null || !owned.CanNavigate || !lifecycle.IsCurrent(owned)) { return; }

            var profile = BrowserProfile.PathFor(origin,
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData));
            var options = new CoreWebView2EnvironmentOptions
            {
                ReleaseChannels = CoreWebView2ReleaseChannels.Stable
            };
            var environment = await CoreWebView2Environment.CreateWithOptionsAsync(null, profile, options);
            if (!lifecycle.IsCurrent(owned) || !owned.CanNavigate) { return; }
            if (!Version.TryParse(environment.BrowserVersionString.Split(' ')[0], out var runtime) || runtime.Major < 154)
            {
                throw new InvalidOperationException("Serviced Evergreen Runtime 154 or newer is required.");
            }
            var current = new WebView2 { Visibility = Visibility.Collapsed };
            webView = current;
            viewSession = owned;
            Grid.SetRow(current, 1);
            layout.Children.Add(current);
            await current.EnsureCoreWebView2Async(environment);
            if (!lifecycle.IsCurrent(owned) || !owned.CanNavigate || webView != current) { return; }
            bridge = new NativeBridgeSession(new WindowsNativePlatform(WinRT.Interop.WindowNative.GetWindowHandle(this)));
            native = new WebViewNativeBridge(current.CoreWebView2, owned, bridge,
                () => lifecycle.IsCurrent(owned) && webView == current,
                action => DispatcherQueue.TryEnqueue(Microsoft.UI.Dispatching.DispatcherQueuePriority.High, () => action()));
            new TrustedWebViewBoundary(current.CoreWebView2, owned, () =>
            {
                if (lifecycle.IsCurrent(owned) && webView == current) { RenderState(); }
            }, native);
            // New control + Navigate(root) starts a GET, never Reload/history/form replay.
            current.CoreWebView2.Navigate(origin.Value + "/");
        }
        catch (Exception error) when (error is System.Runtime.InteropServices.COMException or
            InvalidOperationException or IOException or UnauthorizedAccessException or ArgumentException)
        {
            owned.Fail(ShellState.InitializationFailure);
            if (lifecycle.IsCurrent(owned)) { RenderState(); }
        }
        finally
        {
            if (lifecycle.IsCurrent(owned)) { RenderState(); }
        }
    }

    private void RenderState()
    {
        var session = lifecycle.Session;
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
            ShellState.Suspended => "Đã tạm dừng kết nối. Valora sẽ kết nối lại khi máy hoạt động.",
            ShellState.NetworkUnavailable => "Mất kết nối mạng. Valora sẽ kết nối lại khi có mạng.",
            ShellState.Revalidating => "Đang kết nối lại Valora…",
            _ => "Không tải được Valora. Thử lại hoặc liên hệ quản trị viên."
        };
        var busy = session.State is ShellState.Initializing or ShellState.Loading or ShellState.Revalidating;
        progress.IsActive = busy;
        progress.Visibility = busy ? Visibility.Visible : Visibility.Collapsed;
        retry.IsEnabled = !busy && session.State is not (ShellState.Suspended or ShellState.NetworkUnavailable);
        retry.Visibility = session.State == ShellState.Loaded ? Visibility.Collapsed : Visibility.Visible;
        if (webView is not null)
        {
            webView.Visibility = viewSession == session && session.State == ShellState.Loaded ? Visibility.Visible : Visibility.Collapsed;
            if (viewSession != session || !session.CanNavigate)
            {
                // Defer control destruction out of the WebView callback; hide/revoke immediately.
                var failedView = webView;
                DispatcherQueue.TryEnqueue(() =>
                {
                    if (webView == failedView && (viewSession != lifecycle.Session || !lifecycle.Session.CanNavigate)) { CloseWebView(); }
                });
            }
        }
    }

    private void CloseWebView()
    {
        if (webView is null) { return; }
        var previous = webView;
        native?.Dispose();
        native = null;
        bridge?.Revoke();
        bridge = null;
        webView = null;
        viewSession = null;
        layout.Children.Remove(previous);
        previous.Close();
    }
}
