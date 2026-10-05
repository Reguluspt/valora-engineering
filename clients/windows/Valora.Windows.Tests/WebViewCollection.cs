using Xunit;

namespace Valora.Windows.Tests;

// Separate profiles still start competing browser process groups. Bound that resource to one real
// fixture at a time; other xUnit collections retain their normal parallel execution.
[CollectionDefinition(nameof(WebViewCollection))]
public sealed class WebViewCollection { }
