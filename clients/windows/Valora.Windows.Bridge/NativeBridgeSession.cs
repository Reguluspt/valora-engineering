namespace Valora.Windows.Bridge;

public sealed class NativeBridgeSession(INativePlatform platform)
{
    private readonly object gate = new();
    private BridgeGeneration? generation;
    private readonly IReadOnlyList<string> capabilities = Array.AsReadOnly(platform.EnabledCapabilities
        .Where(NativeProtocol.Capabilities.Contains).Distinct(StringComparer.Ordinal).ToArray());
    public event Action<string, BridgeGeneration>? NativeEvent;
    public bool Enabled { get { lock (gate) { return generation?.Active == true; } } }
    public BridgeGeneration? CurrentGeneration { get { lock (gate) { return generation; } } }

    public void Enable()
    {
        lock (gate)
        {
            generation?.Revoke();
            generation = new BridgeGeneration();
        }
    }

    public void Revoke()
    {
        lock (gate)
        {
            if (generation?.Active != true) { return; }
            generation.Revoke();
            NativeEvent?.Invoke(NativeProtocol.Event("bridgeRevoked", new { code = "BRIDGE_REVOKED" }), generation);
        }
    }

    public Task<string> DispatchAsync(string json, BridgeGeneration? expected = null)
    {
        NativeRequest request;
        try { request = NativeProtocol.Parse(json); }
        catch (NativeBridgeException error) { return Task.FromResult(NativeProtocol.Failure(Guid.Empty.ToString("D"), error.Code)); }
        lock (gate)
        {
            var current = generation;
            if (expected is not null && !ReferenceEquals(current, expected))
            {
                return Task.FromResult(NativeProtocol.Failure(request.RequestId, NativeError.BRIDGE_REVOKED));
            }
            if (current is null || !current.Active) { return Task.FromResult(NativeProtocol.Failure(request.RequestId, NativeError.NOT_TRUSTED)); }
            // Fixed association launches also use TreatAsUntrusted and can show an OS confirmation.
            var interactive = request.Capability is "pickExcelFile" or "pickDocumentFile" or "openInExcel" or "openInWord" or
                "saveDownloadedArtifact" or "openExternalUrl";
            try
            {
                if (request.Capability != "hello" && !current.Negotiated) { throw new NativeBridgeException(NativeError.BAD_PROTOCOL); }
                if (request.Capability != "hello" && !capabilities.Contains(request.Capability))
                {
                    throw new NativeBridgeException(NativeError.CAPABILITY_UNAVAILABLE);
                }
                var completion = current.Admit(request.RequestId, interactive);
                _ = ExecuteAsync(current, request, interactive);
                return completion.Task;
            }
            catch (NativeBridgeException error) { return Task.FromResult(NativeProtocol.Failure(request.RequestId, error.Code)); }
        }
    }

    private async Task ExecuteAsync(BridgeGeneration current, NativeRequest request, bool interactive)
    {
        string response;
        try
        {
            var result = await ExecuteCapabilityAsync(current, request);
            response = current.Start(() => NativeProtocol.Success(request.RequestId, result));
        }
        catch (NativeBridgeException error) { response = NativeProtocol.Failure(request.RequestId, error.Code); }
        catch (OperationCanceledException) { response = NativeProtocol.Failure(request.RequestId, NativeError.BRIDGE_REVOKED); }
        catch (Exception) { response = NativeProtocol.Failure(request.RequestId, NativeError.FAILED); }
        current.Complete(request.RequestId, interactive, response);
    }

    private async Task<object> ExecuteCapabilityAsync(BridgeGeneration current, NativeRequest request)
    {
        var payload = request.Payload;
        switch (request.Capability)
        {
            case "hello":
                return current.Start(() =>
                {
                    current.Negotiated = true;
                    return new { protocol = NativeProtocol.Id, capabilities };
                });
            case "pickExcelFile": case "pickDocumentFile":
                var excel = request.Capability == "pickExcelFile";
                var selected = await current.Start(() => platform.PickAsync(excel, current));
                if (selected is null) { return new { selected = false }; }
                var info = await current.Start(() => selected.InspectAsync(current.Cancellation));
                BridgeGeneration.ValidateFile(info);
                if (excel ? info.Extension is not (".xls" or ".xlsx") : info.Extension != ".docx")
                {
                    throw new NativeBridgeException(NativeError.TYPE_NOT_ALLOWED);
                }
                return new { selected = true, handle = current.Register(selected, info), name = info.Name, extension = info.Extension, sizeBytes = info.SizeBytes };
            case "openInExcel": case "openInWord":
                var openExcel = request.Capability == "openInExcel";
                var file = current.Resolve(NativeProtocol.Text(payload, "handle"), openExcel);
                var latest = await current.Start(() => file.InspectAsync(current.Cancellation));
                BridgeGeneration.ValidateFile(latest);
                if (openExcel ? latest.Extension is not (".xls" or ".xlsx") : latest.Extension != ".docx")
                {
                    throw new NativeBridgeException(NativeError.TYPE_NOT_ALLOWED);
                }
                if (!await current.Start(() => platform.OpenAsync(file, openExcel, current))) { throw new NativeBridgeException(NativeError.OS_UNAVAILABLE); }
                return new { opened = true };
            case "saveDownloadedArtifact":
                var artifact = current.Resolve(NativeProtocol.Text(payload, "artifactHandle"), false, true);
                var artifactInfo = await current.Start(() => artifact.InspectAsync(current.Cancellation));
                BridgeGeneration.ValidateFile(artifactInfo);
                var suggestedFilename = NativeProtocol.Text(payload, "suggestedFilename");
                if (!suggestedFilename.EndsWith(artifactInfo.Extension, StringComparison.OrdinalIgnoreCase))
                {
                    throw new NativeBridgeException(NativeError.TYPE_NOT_ALLOWED);
                }
                var saved = await current.Start(() => platform.SaveAsync(artifact, suggestedFilename, current));
                return new { saved = saved == true };
            case "showNotification":
                if (!await current.Start(() => platform.NotifyAsync(NativeProtocol.Text(payload, "title"), NativeProtocol.Text(payload, "body"), current)))
                {
                    throw new NativeBridgeException(NativeError.OS_UNAVAILABLE);
                }
                return new { shown = true };
            case "openExternalUrl":
                if (!await current.Start(() => platform.OpenExternalAsync(NativeProtocol.Text(payload, "url"), current)))
                {
                    throw new NativeBridgeException(NativeError.OS_UNAVAILABLE);
                }
                return new { opened = true };
            default: throw new NativeBridgeException(NativeError.CAPABILITY_UNAVAILABLE);
        }
    }

    public async Task MediateDropAsync(IReadOnlyList<INativeFile> files, BridgeGeneration expected)
    {
        var current = CurrentGeneration;
        if (!ReferenceEquals(current, expected)) { throw new NativeBridgeException(NativeError.BRIDGE_REVOKED); }
        if (current is null || !current.Active || !current.Negotiated || !capabilities.Contains("dragDrop"))
        {
            throw new NativeBridgeException(NativeError.CAPABILITY_UNAVAILABLE);
        }
        if (files.Count != 1) { throw new NativeBridgeException(NativeError.INVALID_ARGUMENT); }
        var info = await current.Start(() => files[0].InspectAsync(current.Cancellation));
        var handle = current.Register(files[0], info);
        current.Start(() =>
        {
            NativeEvent?.Invoke(NativeProtocol.Event("filesDropped", new { handle, name = info.Name, extension = info.Extension, sizeBytes = info.SizeBytes }), current);
            return true;
        });
    }

    public void MediateDeepLink(string route, BridgeGeneration expected)
    {
        var current = CurrentGeneration;
        if (!ReferenceEquals(current, expected)) { throw new NativeBridgeException(NativeError.BRIDGE_REVOKED); }
        if (current is null || !current.Negotiated || !capabilities.Contains("deepLink"))
        {
            throw new NativeBridgeException(NativeError.CAPABILITY_UNAVAILABLE);
        }
        if (!NativeProtocol.SafeRoute(route)) { throw new NativeBridgeException(NativeError.INVALID_ARGUMENT); }
        current.Start(() => { NativeEvent?.Invoke(NativeProtocol.Event("deepLink", new { route }), current); return true; });
    }
}
