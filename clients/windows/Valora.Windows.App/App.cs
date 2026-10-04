using Microsoft.UI.Xaml;
using Valora.Windows.Bridge;

namespace Valora.Windows.App;

public sealed partial class App : Application
{
    private Window? window;

    public App()
    {
        InitializeComponent();
    }

    protected override void OnLaunched(LaunchActivatedEventArgs args)
    {
        window = new MainWindow();
        window.Activate();
    }
}
