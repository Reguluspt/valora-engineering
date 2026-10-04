using Microsoft.Win32;
using Valora.Windows.App;
using Xunit;

namespace Valora.Windows.Tests;

public sealed class ServerConfigurationTests
{
    [Fact]
    public void MissingKeyHasNoConfiguration()
    {
        Assert.Null(ServerConfiguration.Read(null));
    }

    [Theory]
    [InlineData((int)RegistryValueKind.String, "https://valora.example", "https://valora.example")]
    [InlineData((int)RegistryValueKind.ExpandString, "https://%VALORA_HOST%", "")]
    [InlineData((int)RegistryValueKind.String, "https://user:secret@valora.example", "https://user:secret@valora.example")]
    public void ConfigurationIsReadWithoutExpansionOrPersistence(int kind, string input, string expected)
    {
        var path = @"Software\Valora.Win1.Tests\" + Guid.NewGuid().ToString("N");
        try
        {
            using (var writable = Registry.CurrentUser.CreateSubKey(path))
            {
                writable.SetValue("ServerOrigin", input, (RegistryValueKind)kind);
            }
            using var readOnly = Registry.CurrentUser.OpenSubKey(path, writable: false);
            Assert.Equal(expected, ServerConfiguration.Read(readOnly));
            Assert.Equal(["ServerOrigin"], readOnly!.GetValueNames());
            Assert.Equal(input, readOnly.GetValue("ServerOrigin", null, RegistryValueOptions.DoNotExpandEnvironmentNames));
            var session = new ShellSession();
            session.Begin(ServerConfiguration.Read(readOnly));
            Assert.Equal(input.Contains("secret") || kind == (int)RegistryValueKind.ExpandString
                ? ShellState.InvalidConfiguration : ShellState.Initializing, session.State);
        }
        finally { Registry.CurrentUser.DeleteSubKeyTree(path, throwOnMissingSubKey: false); }
    }
}
