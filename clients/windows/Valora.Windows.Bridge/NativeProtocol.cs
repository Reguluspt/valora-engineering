using System.Text;
using System.Text.Json;

namespace Valora.Windows.Bridge;

public enum NativeError
{
    BAD_PROTOCOL, BAD_MESSAGE, NOT_TRUSTED, CAPABILITY_UNAVAILABLE, INVALID_ARGUMENT,
    CANCELLED, HANDLE_INVALID, TYPE_NOT_ALLOWED, SIZE_LIMIT, BUSY, OS_UNAVAILABLE, BRIDGE_REVOKED, FAILED
}

public sealed class NativeBridgeException(NativeError code) : Exception(code.ToString())
{
    public NativeError Code { get; } = code;
}

public sealed record NativeRequest(string RequestId, string Capability, JsonElement Payload);

public static class NativeProtocol
{
    public const string Id = "valora.native/1";
    public const int MessageLimit = 64 * 1024;
    public const int PendingLimit = 8;
    public static IReadOnlyList<string> Capabilities { get; } = Array.AsReadOnly(new[]
    {
        "pickExcelFile", "pickDocumentFile", "openInExcel", "openInWord", "saveDownloadedArtifact",
        "dragDrop", "showNotification", "deepLink", "openExternalUrl"
    });

    public static NativeRequest Parse(string json)
    {
        if (Encoding.UTF8.GetByteCount(json) > MessageLimit) { throw new NativeBridgeException(NativeError.SIZE_LIMIT); }
        try
        {
            using var document = JsonDocument.Parse(json, new JsonDocumentOptions { MaxDepth = 8 });
            var root = document.RootElement;
            Shape(root, "protocol", "type", "requestId", "capability", "payload");
            if (Text(root, "protocol") != Id) { throw new NativeBridgeException(NativeError.BAD_PROTOCOL); }
            var id = Text(root, "requestId");
            if (Text(root, "type") != "request" || !Guid.TryParseExact(id, "D", out var uuid) || uuid.ToString("D") != id)
            {
                throw new NativeBridgeException(NativeError.BAD_MESSAGE);
            }
            var capability = Text(root, "capability");
            if (capability != "hello" && !Capabilities.Contains(capability))
            {
                throw new NativeBridgeException(NativeError.CAPABILITY_UNAVAILABLE);
            }
            var payload = root.GetProperty("payload");
            ValidatePayload(capability, payload);
            return new NativeRequest(id, capability, payload.Clone());
        }
        catch (JsonException) { throw new NativeBridgeException(NativeError.BAD_MESSAGE); }
    }

    public static void Shape(JsonElement value, params string[] keys)
    {
        if (value.ValueKind != JsonValueKind.Object) { throw new NativeBridgeException(NativeError.BAD_MESSAGE); }
        var names = value.EnumerateObject().Select(p => p.Name).ToArray();
        if (names.Length != keys.Length || names.Distinct(StringComparer.Ordinal).Count() != names.Length ||
            keys.Any(key => !names.Contains(key, StringComparer.Ordinal)))
        {
            throw new NativeBridgeException(NativeError.BAD_MESSAGE);
        }
    }

    public static string Text(JsonElement value, string key)
    {
        if (!value.TryGetProperty(key, out var property) || property.ValueKind != JsonValueKind.String)
        {
            throw new NativeBridgeException(NativeError.BAD_MESSAGE);
        }
        return property.GetString()!;
    }

    public static bool SafeText(string value, int maximum) => value.Length != 0 &&
        value.EnumerateRunes().Count() <= maximum && !value.Any(char.IsControl) &&
        ValidUnicode(value);

    private static bool ValidUnicode(string value)
    {
        for (var i = 0; i < value.Length; i++)
        {
            if (char.IsHighSurrogate(value[i]))
            {
                if (++i >= value.Length || !char.IsLowSurrogate(value[i])) { return false; }
            }
            else if (char.IsLowSurrogate(value[i])) { return false; }
        }
        return true;
    }

    public static bool SafeName(string name) => SafeText(name, 255) &&
        !name.Any(c => "\\/:*?\"<>|".Contains(c)) && name is not ("." or "..") &&
        !name.EndsWith('.') && !name.EndsWith(' ');

    public static bool SafeRoute(string route)
    {
        if (route.Length is 0 or > 2048 || !route.StartsWith('/') || route.StartsWith("//") ||
            route.Contains('\\') || route.Any(char.IsControl) || route.Any(char.IsWhiteSpace) || !ValidUnicode(route)) { return false; }
        var path = Uri.UnescapeDataString(route.Split('?', '#')[0]);
        return !path.StartsWith("//") && !path.Contains('\\') && !path.Contains('%') &&
            !path.Any(char.IsControl) && !path.Any(char.IsWhiteSpace) &&
            !path.Split('/').Any(segment => segment is "." or "..");
    }

    public static void ValidatePayload(string capability, JsonElement payload)
    {
        switch (capability)
        {
            case "hello": case "pickExcelFile": case "pickDocumentFile": case "dragDrop": case "deepLink":
                Shape(payload); break;
            case "openInExcel": case "openInWord":
                Shape(payload, "handle");
                if (!IsHandle(Text(payload, "handle"))) { throw new NativeBridgeException(NativeError.HANDLE_INVALID); }
                break;
            case "saveDownloadedArtifact":
                Shape(payload, "artifactHandle", "suggestedFilename");
                if (!IsHandle(Text(payload, "artifactHandle"))) { throw new NativeBridgeException(NativeError.HANDLE_INVALID); }
                if (!SafeName(Text(payload, "suggestedFilename"))) { throw new NativeBridgeException(NativeError.INVALID_ARGUMENT); }
                break;
            case "showNotification":
                Shape(payload, "title", "body");
                if (!SafeText(Text(payload, "title"), 80) || !SafeText(Text(payload, "body"), 256))
                {
                    throw new NativeBridgeException(NativeError.INVALID_ARGUMENT);
                }
                break;
            case "openExternalUrl":
                Shape(payload, "url");
                if (Text(payload, "url").Length is 0 or > 2048) { throw new NativeBridgeException(NativeError.INVALID_ARGUMENT); }
                break;
        }
    }

    public static bool IsHandle(string value) => value.Length == 48 && value.All(c => c is >= '0' and <= '9' or >= 'a' and <= 'f');
    public static string Success(string id, object result) => JsonSerializer.Serialize(new
    {
        protocol = Id, type = "response", requestId = id, ok = true, result
    });
    public static string Failure(string id, NativeError code) => JsonSerializer.Serialize(new
    {
        protocol = Id, type = "response", requestId = id, ok = false,
        error = new { code = code.ToString(), message = "Native operation unavailable or rejected." }
    });
    public static string Event(string name, object payload) => JsonSerializer.Serialize(new { protocol = Id, type = "event", @event = name, payload });
}
