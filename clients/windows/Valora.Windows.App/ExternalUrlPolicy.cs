namespace Valora.Windows.App;

internal sealed class ExternalUrlPolicy(IEnumerable<string> origins)
{
    private readonly TrustedOrigin[] allowed = origins.Select(value => TrustedOrigin.TryParse(value, out var parsed)
        ? parsed! : throw new ArgumentException("Invalid native external origin catalog.")).ToArray();
    internal bool Enabled => allowed.Length != 0;
    internal bool Allows(string url) => url.Length <= 2048 && allowed.Any(origin => origin.Allows(url));
}
