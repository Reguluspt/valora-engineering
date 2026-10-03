namespace Valora.Windows.Bridge;

public interface INativeCapabilityCatalog
{
    IReadOnlyCollection<string> EnabledCapabilities { get; }
}
