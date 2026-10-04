using System.Text.RegularExpressions;
using Xunit;

namespace Valora.Windows.Tests;

public sealed class NativeAuthBoundaryTests
{
    private static string WindowsRoot()
    {
        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        while (directory is not null && !File.Exists(Path.Combine(directory.FullName, "Valora.Windows.sln")))
        {
            directory = directory.Parent;
        }
        Assert.NotNull(directory);
        return directory!.FullName;
    }

    [Theory]
    [InlineData(@"CookieManager|GetCookies|CreateCookie|AddOrUpdateCookie|DeleteAllCookies")]
    [InlineData(@"access[_-]?token|refresh[_-]?token|XSRF|X-CSRF|csrf[_-]?token|password|PasswordVault|CredentialManager")]
    [InlineData(@"organization[_-]?(id|slug)|user[_-]?id|AccountContext|RBAC|\bBearer\b")]
    [InlineData(@"/api/v1/auth|HttpClient|WebRequest|HttpWebRequest")]
    [InlineData(@"ExecuteScript|AddScriptToExecute|WebMessageReceived|AddHostObject")]
    [InlineData(@"\.Reload\s*\(|\.GoBack\s*\(|\.GoForward\s*\(|NavigateWithWebResourceRequest|CreateWebResourceRequest")]
    public void ProductionWindowsSourceHasNoNativeAuthenticationOrReplayPrimitive(string pattern)
    {
        var root = WindowsRoot();
        var files = new[] { "Valora.Windows.App", "Valora.Windows.Bridge" }
            .SelectMany(project => Directory.EnumerateFiles(Path.Combine(root, project), "*", SearchOption.AllDirectories))
            .Where(path => !path.Split(Path.DirectorySeparatorChar).Any(part => part is "bin" or "obj"))
            .Where(path => Path.GetExtension(path) is ".cs" or ".xaml");
        Assert.NotEmpty(files);
        foreach (var path in files)
        {
            Assert.False(Regex.IsMatch(File.ReadAllText(path), pattern, RegexOptions.IgnoreCase),
                $"Forbidden native authority/replay primitive in {Path.GetFileName(path)}: {pattern}");
        }
    }

    [Fact]
    public void NativeBootstrapHasOneRootNavigationAndNoHistoryOrRequestReconstruction()
    {
        var source = File.ReadAllText(Path.Combine(WindowsRoot(), "Valora.Windows.App", "MainWindow.cs"));
        Assert.Single(Regex.Matches(source, @"\.Navigate\s*\("));
        Assert.Contains("Navigate(origin.Value + \"/\")", source);
        Assert.Contains("lifecycle.IsCurrent(owned)", source);
        Assert.DoesNotContain("HttpStatusCode", source);
        Assert.DoesNotContain("HttpStatusCode", File.ReadAllText(Path.Combine(WindowsRoot(),
            "Valora.Windows.App", "TrustedWebViewBoundary.cs")));
    }
}
