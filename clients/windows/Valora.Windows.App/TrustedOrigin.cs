using System.Globalization;
using System.Text.RegularExpressions;

namespace Valora.Windows.App;

internal sealed class TrustedOrigin
{
    private static readonly Regex UrlShape = new(
        @"\A(?i:https)://(?<host>\[[0-9a-fA-F:]+\]|[a-zA-Z0-9.-]+)(?::(?<port>[1-9][0-9]{0,4}))?(?<tail>/[^\s\\]*|[?#][^\s\\]*)?\z",
        RegexOptions.CultureInvariant, TimeSpan.FromMilliseconds(100));

    private readonly string host;
    private readonly int port;

    private TrustedOrigin(Uri uri)
    {
        host = uri.IdnHost;
        port = uri.Port;
        Value = uri.GetLeftPart(UriPartial.Authority).ToLowerInvariant();
    }

    internal string Value { get; }

    internal static bool TryParse(string? value, out TrustedOrigin? origin)
    {
        origin = null;
        if (!TryUrl(value, out var uri, out var tail) || (tail != "" && tail != "/"))
        {
            return false;
        }

        origin = new TrustedOrigin(uri!);
        return true;
    }

    internal bool Allows(string? destination) =>
        TryUrl(destination, out var uri, out _) &&
        string.Equals(host, uri!.IdnHost, StringComparison.OrdinalIgnoreCase) && port == uri.Port;

    private static bool TryUrl(string? value, out Uri? uri, out string tail)
    {
        uri = null;
        tail = "";
        if (string.IsNullOrEmpty(value) || value.Length > 8192 || value.Any(char.IsControl))
        {
            return false;
        }

        var match = UrlShape.Match(value);
        if (!match.Success || !Uri.TryCreate(value, UriKind.Absolute, out var parsed) ||
            parsed.Scheme != Uri.UriSchemeHttps || parsed.UserInfo.Length != 0)
        {
            return false;
        }

        var rawHost = match.Groups["host"].Value;
        var rawPort = match.Groups["port"].Value;
        if (rawHost.EndsWith('.') || (rawPort.Length != 0 &&
            (!int.TryParse(rawPort, NumberStyles.None, CultureInfo.InvariantCulture, out var number) || number > 65535)))
        {
            return false;
        }

        if (parsed.HostNameType == UriHostNameType.IPv4)
        {
            if (!string.Equals(rawHost, parsed.Host, StringComparison.Ordinal)) { return false; }
        }
        else if (parsed.HostNameType == UriHostNameType.Dns)
        {
            if (rawHost.Length > 253 || rawHost.Split('.').Any(label =>
                label.Length is 0 or > 63 || label.StartsWith('-') || label.EndsWith('-')))
            {
                return false;
            }
        }
        else if (parsed.HostNameType != UriHostNameType.IPv6)
        {
            return false;
        }

        uri = parsed;
        tail = match.Groups["tail"].Value;
        return true;
    }
}
