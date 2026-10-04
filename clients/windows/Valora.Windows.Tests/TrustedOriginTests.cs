using Valora.Windows.App;
using Xunit;

namespace Valora.Windows.Tests;

public sealed class TrustedOriginTests
{
    [Theory]
    [InlineData("https://VALORA.example:443/", "https://valora.example")]
    [InlineData("https://valora.example:8443", "https://valora.example:8443")]
    [InlineData("https://192.168.1.10/", "https://192.168.1.10")]
    [InlineData("https://[::1]:8443/", "https://[::1]:8443")]
    public void AcceptsAndCanonicalizesHttpsOrigins(string input, string expected)
    {
        Assert.True(TrustedOrigin.TryParse(input, out var origin));
        Assert.Equal(expected, origin!.Value);
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("http://valora.example")]
    [InlineData("https://")]
    [InlineData("valora.example")]
    [InlineData("https://user:password@valora.example")]
    [InlineData("https://@valora.example")]
    [InlineData("https://valora.example/path")]
    [InlineData("https://valora.example/../")]
    [InlineData("https://valora.example/%2e%2e/")]
    [InlineData("https://valora.example?token=secret")]
    [InlineData("https://valora.example#fragment")]
    [InlineData(" https://valora.example")]
    [InlineData("https://valora.example\n")]
    [InlineData("https://valora.example\\evil")]
    [InlineData("https://valora.example.")]
    [InlineData("https://127.1")]
    [InlineData("https://2130706433")]
    [InlineData("https://0177.0.0.1")]
    [InlineData("https://vаlora.example")]
    [InlineData("https://%76alora.example")]
    [InlineData("https://valora.example:0443")]
    [InlineData("https://valora.example:0")]
    public void RejectsUnsafeOrNonOriginConfiguration(string? input)
    {
        Assert.False(TrustedOrigin.TryParse(input, out var origin));
        Assert.Null(origin);
    }

    [Theory]
    [InlineData("https://VALORA.example:443/login?return=%2F#section", true)]
    [InlineData("https://valora.example/api/v1", true)]
    [InlineData("http://valora.example/", false)]
    [InlineData("https://other.example/", false)]
    [InlineData("https://valora.example:8443/", false)]
    [InlineData("https://valora.example.evil/", false)]
    [InlineData("https://user@valora.example/", false)]
    [InlineData("https://valora.example./", false)]
    [InlineData("https://%76alora.example/", false)]
    [InlineData("https://valora.example\\evil/", false)]
    [InlineData("javascript:alert(1)", false)]
    [InlineData("file:///C:/secret.txt", false)]
    [InlineData("data:text/html,hello", false)]
    [InlineData("about:blank", false)]
    [InlineData("blob:https://valora.example/id", false)]
    public void NavigationUsesExactOrigin(string destination, bool allowed)
    {
        Assert.True(TrustedOrigin.TryParse("https://valora.example", out var origin));
        Assert.Equal(allowed, origin!.Allows(destination));
    }

    [Fact]
    public void ExplicitPortIsTheOnlyTrustedPort()
    {
        Assert.True(TrustedOrigin.TryParse("https://valora.example:8443", out var origin));
        Assert.True(origin!.Allows("https://valora.example:8443/path"));
        Assert.False(origin.Allows("https://valora.example/path"));
    }
}
