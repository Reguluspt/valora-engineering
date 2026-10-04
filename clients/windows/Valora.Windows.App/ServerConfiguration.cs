using Microsoft.Win32;
using System.Security;

namespace Valora.Windows.App;

internal static class ServerConfiguration
{
    // Installation/admin tooling owns this machine-level key and its ACL; the shell never writes it.
    internal static string? Read()
    {
        try
        {
            using var machine = RegistryKey.OpenBaseKey(RegistryHive.LocalMachine, RegistryView.Registry64);
            using var key = machine.OpenSubKey(@"SOFTWARE\Valora\WindowsClient", writable: false);
            return Read(key);
        }
        catch (Exception error) when (error is SecurityException or UnauthorizedAccessException or IOException)
        {
            return "";
        }
    }

    internal static string? Read(RegistryKey? key)
    {
        if (key is null) { return null; }
        var value = key.GetValue("ServerOrigin", null, RegistryValueOptions.DoNotExpandEnvironmentNames);
        if (value is null) { return null; }
        return key.GetValueKind("ServerOrigin") == RegistryValueKind.String && value is string origin ? origin : "";
    }
}
