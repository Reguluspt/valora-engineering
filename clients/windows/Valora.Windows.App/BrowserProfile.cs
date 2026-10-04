using System.Security.Cryptography;
using System.Text;

namespace Valora.Windows.App;

internal static class BrowserProfile
{
    internal static string PathFor(TrustedOrigin origin, string localApplicationData) =>
        Path.Combine(localApplicationData, "Valora", "WindowsClient", "WebView2",
            Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(origin.Value))));
}
