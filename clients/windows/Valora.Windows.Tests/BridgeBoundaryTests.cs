using Valora.Windows.Bridge;
using Xunit;

namespace Valora.Windows.Tests;

public sealed class BridgeBoundaryTests
{
    [Fact]
    public void FoundationExposesNoNativeCapabilities()
    {
        INativeCapabilityCatalog bridge = new FoundationCapabilityCatalog();
        Assert.Empty(bridge.EnabledCapabilities);
        Assert.False(bridge.EnabledCapabilities is string[]);
    }

    [Fact]
    public void BridgeDoesNotDependOnAppOrWebViewOrDomainAssemblies()
    {
        var dependencies = typeof(INativeCapabilityCatalog).Assembly.GetReferencedAssemblies();
        Assert.All(dependencies, dependency => Assert.StartsWith("System.", dependency.Name));
    }
}
