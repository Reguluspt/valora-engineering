using Windows.Storage;
using Windows.Storage.Pickers;
using Windows.System;
using Valora.Windows.Bridge;

namespace Valora.Windows.App;

internal sealed class WindowsNativeFile(StorageFile file) : INativeFile
{
    internal StorageFile File { get; } = file;
    public async Task<NativeFileInfo> InspectAsync(CancellationToken cancellation)
    {
        var properties = await File.GetBasicPropertiesAsync().AsTask(cancellation);
        return new NativeFileInfo(File.Name, File.FileType.ToLowerInvariant(), properties.Size);
    }
}

internal sealed class WindowsNativePlatform(nint window) : INativePlatform
{
    private readonly ExternalUrlPolicy external = new([]);
    public IReadOnlyCollection<string> EnabledCapabilities { get; } = Array.AsReadOnly(new[]
    {
        "pickExcelFile", "pickDocumentFile", "openInExcel", "openInWord", "dragDrop"
    });

    public async Task<INativeFile?> PickAsync(bool excel, BridgeGeneration generation)
    {
        var picker = new FileOpenPicker { ViewMode = PickerViewMode.List, SuggestedStartLocation = PickerLocationId.DocumentsLibrary };
        foreach (var extension in excel ? new[] { ".xls", ".xlsx" } : new[] { ".docx" }) { picker.FileTypeFilter.Add(extension); }
        WinRT.Interop.InitializeWithWindow.Initialize(picker, window);
        var selected = await generation.Start(() => picker.PickSingleFileAsync().AsTask(generation.Cancellation));
        return selected is null ? null : new WindowsNativeFile(selected);
    }

    public Task<bool> OpenAsync(INativeFile file, bool excel, BridgeGeneration generation)
    {
        if (file is not WindowsNativeFile selected) { throw new NativeBridgeException(NativeError.HANDLE_INVALID); }
        return generation.Start(() => Launcher.LaunchFileAsync(selected.File,
            new LauncherOptions { TreatAsUntrusted = true }).AsTask(generation.Cancellation));
    }

    public async Task<bool?> SaveAsync(INativeFile artifact, string suggestedFilename, BridgeGeneration generation)
    {
        if (artifact is not WindowsNativeFile selected) { throw new NativeBridgeException(NativeError.HANDLE_INVALID); }
        if (!NativeProtocol.SafeName(suggestedFilename)) { throw new NativeBridgeException(NativeError.INVALID_ARGUMENT); }
        var extension = selected.File.FileType.ToLowerInvariant();
        if (!suggestedFilename.EndsWith(extension, StringComparison.OrdinalIgnoreCase))
        {
            throw new NativeBridgeException(NativeError.TYPE_NOT_ALLOWED);
        }
        var picker = new FileSavePicker { SuggestedFileName = suggestedFilename };
        picker.FileTypeChoices.Add("Valora artifact", new List<string> { extension });
        WinRT.Interop.InitializeWithWindow.Initialize(picker, window);
        var destination = await generation.Start(() => picker.PickSaveFileAsync().AsTask(generation.Cancellation));
        if (destination is null) { return null; }
        using var source = await generation.Start(() => selected.File.OpenReadAsync().AsTask(generation.Cancellation));
        if (source.Size > BridgeGeneration.FileLimit) { throw new NativeBridgeException(NativeError.SIZE_LIMIT); }
        using var target = await generation.Start(() => destination.OpenAsync(FileAccessMode.ReadWrite).AsTask(generation.Cancellation));
        using var input = source.AsStreamForRead();
        using var output = target.AsStreamForWrite();
        generation.Start(() => { output.SetLength(0); return true; });
        var buffer = new byte[64 * 1024];
        ulong copied = 0;
        int count;
        while ((count = await generation.Start(() => input.ReadAsync(buffer.AsMemory(), generation.Cancellation).AsTask())) != 0)
        {
            copied += (ulong)count;
            if (copied > BridgeGeneration.FileLimit) { throw new NativeBridgeException(NativeError.SIZE_LIMIT); }
            await generation.Start(() => output.WriteAsync(buffer.AsMemory(0, count), generation.Cancellation).AsTask());
        }
        await generation.Start(() => output.FlushAsync(generation.Cancellation));
        return true;
    }

    public Task<bool> NotifyAsync(string title, string body, BridgeGeneration generation) =>
        throw new NativeBridgeException(NativeError.CAPABILITY_UNAVAILABLE);

    public Task<bool> OpenExternalAsync(string url, BridgeGeneration generation)
    {
        if (!external.Enabled) { throw new NativeBridgeException(NativeError.CAPABILITY_UNAVAILABLE); }
        if (!external.Allows(url)) { throw new NativeBridgeException(NativeError.INVALID_ARGUMENT); }
        return generation.Start(() => Launcher.LaunchUriAsync(new Uri(url),
            new LauncherOptions { TreatAsUntrusted = true }).AsTask(generation.Cancellation));
    }
}
