using Microsoft.Web.WebView2.Core;

namespace Valora.Windows.App;

internal sealed class TrustedWebViewBoundary
{
    internal TrustedWebViewBoundary(CoreWebView2 core, ShellSession session, Action changed)
    {
        core.Settings.IsWebMessageEnabled = false;
        core.Settings.AreHostObjectsAllowed = false;
        core.Settings.AreDevToolsEnabled = false;
        core.Settings.AreDefaultContextMenusEnabled = false;
        core.Settings.AreBrowserAcceleratorKeysEnabled = false;
        core.Settings.IsBuiltInErrorPageEnabled = false;

        void Block(ShellState state)
        {
            session.Fail(state);
            core.Stop();
            changed();
        }

        core.NavigationStarting += (_, args) =>
        {
            args.Cancel = !session.NavigationStarting(args.Uri, args.NavigationId);
            changed();
        };
        core.NavigationCompleted += (_, args) =>
        {
            session.NavigationCompleted(args.NavigationId,
                args.IsSuccess ? ShellState.Loaded : ClassifyFailure(args.WebErrorStatus));
            changed();
        };
        core.NewWindowRequested += (_, args) =>
        {
            args.Handled = true;
            Block(ShellState.NavigationBlocked);
        };
        // WIN-1 has no frame use case. Denying every child frame also covers srcdoc/opaque frames.
        core.FrameCreated += (_, args) =>
        {
            args.Frame.NavigationStarting += (_, navigation) => navigation.Cancel = true;
            Block(ShellState.NavigationBlocked);
        };
        core.FrameNavigationStarting += (_, args) => args.Cancel = true;
        core.LaunchingExternalUriScheme += (_, args) =>
        {
            args.Cancel = true;
            Block(ShellState.NavigationBlocked);
        };
        core.ServerCertificateErrorDetected += (_, args) =>
        {
            args.Action = CoreWebView2ServerCertificateErrorAction.Cancel;
            Block(ShellState.CertificateFailure);
        };
        core.PermissionRequested += (_, args) =>
        {
            args.State = CoreWebView2PermissionState.Deny;
            args.Handled = true;
        };
        core.DownloadStarting += (_, args) =>
        {
            args.Cancel = true;
            args.Handled = true;
            Block(ShellState.NavigationBlocked);
        };
        core.BasicAuthenticationRequested += (_, args) => args.Cancel = true;
        core.ProcessFailed += (_, _) => Block(ShellState.NavigationFailure);
    }

    internal static ShellState ClassifyFailure(CoreWebView2WebErrorStatus error) => error switch
    {
        CoreWebView2WebErrorStatus.CertificateCommonNameIsIncorrect or
        CoreWebView2WebErrorStatus.CertificateExpired or
        CoreWebView2WebErrorStatus.ClientCertificateContainsErrors or
        CoreWebView2WebErrorStatus.CertificateRevoked or
        CoreWebView2WebErrorStatus.CertificateIsInvalid => ShellState.CertificateFailure,
        CoreWebView2WebErrorStatus.ServerUnreachable or
        CoreWebView2WebErrorStatus.Timeout or
        CoreWebView2WebErrorStatus.ConnectionAborted or
        CoreWebView2WebErrorStatus.ConnectionReset or
        CoreWebView2WebErrorStatus.Disconnected or
        CoreWebView2WebErrorStatus.CannotConnect or
        CoreWebView2WebErrorStatus.HostNameNotResolved => ShellState.NetworkFailure,
        _ => ShellState.NavigationFailure
    };
}
