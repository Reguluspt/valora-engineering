using System.Collections.ObjectModel;

namespace Valora.Windows.Bridge;

public sealed class FoundationCapabilityCatalog : INativeCapabilityCatalog
{
    public IReadOnlyCollection<string> EnabledCapabilities { get; } =
        new ReadOnlyCollection<string>([]);
}
