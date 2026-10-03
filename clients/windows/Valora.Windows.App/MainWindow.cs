using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Valora.Windows.Bridge;

namespace Valora.Windows.App;

internal sealed class MainWindow : Window
{
    internal MainWindow(INativeCapabilityCatalog capabilities)
    {
        if (capabilities.EnabledCapabilities.Count != 0)
        {
            throw new InvalidOperationException("WIN-0 must not expose native capabilities.");
        }

        Title = "Valora — Windows foundation";
        var layout = new Grid { RequestedTheme = ElementTheme.Light };
        layout.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        layout.RowDefinitions.Add(new RowDefinition());
        layout.Children.Add(new TextBlock
        {
            Text = "Nền tảng Windows — chưa kết nối máy chủ.",
            Margin = new Thickness(24),
            FontSize = 20
        });

        // WIN-1 owns initialization, protected configuration and trusted-origin navigation.
        var webView = new WebView2();
        Grid.SetRow(webView, 1);
        layout.Children.Add(webView);
        Content = layout;
    }
}
