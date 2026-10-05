using System.Diagnostics;
using System.Text.Json;
using Microsoft.Web.WebView2.Core;

namespace Valora.Windows.Tests;

internal sealed class WebViewFixtureTrace
{
    [ThreadStatic] internal static WebViewFixtureTrace? Current;
    private static readonly object fileLock = new();
    private static int activeFixtures;
    private readonly string id = Guid.NewGuid().ToString("N");
    private readonly string name;
    private readonly Stopwatch clock = Stopwatch.StartNew();
    private readonly string? path = Environment.GetEnvironmentVariable("VALORA_WEBVIEW_TRACE_PATH");
    private readonly List<Task> browserExits = new();
    private readonly List<CoreWebView2Environment> environments = new();

    internal WebViewFixtureTrace(string name) { this.name = name; }

    internal void Start()
    {
        Interlocked.Increment(ref activeFixtures);
        Write("fixture-start");
    }

    internal void End()
    {
        Write("fixture-end");
        Interlocked.Decrement(ref activeFixtures);
    }

    internal void Write(string stage, object? detail = null)
    {
        if (path is null) { return; }
        var row = JsonSerializer.Serialize(new
        {
            id, name, stage, detail, utc = DateTimeOffset.UtcNow,
            elapsedMs = clock.ElapsedMilliseconds, activeFixtures = Volatile.Read(ref activeFixtures),
            thread = Environment.CurrentManagedThreadId, apartment = Thread.CurrentThread.GetApartmentState().ToString()
        });
        lock (fileLock) { File.AppendAllText(path, row + Environment.NewLine); }
    }

    internal void TrackBrowser(CoreWebView2 core)
    {
        var pid = core.BrowserProcessId;
        var environment = core.Environment;
        environments.Add(environment);
        var exited = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        Write("browser-tracked", new { pid, profile = environment.UserDataFolder, version = environment.BrowserVersionString });
        environment.BrowserProcessExited += (_, args) =>
        {
            try
            {
                Write("browser-process-exited", new { args.BrowserProcessId, args.BrowserProcessExitKind });
                if (args.BrowserProcessExitKind != CoreWebView2BrowserProcessExitKind.Normal)
                {
                    throw new InvalidOperationException($"Fixture browser exited abnormally: {args.BrowserProcessExitKind}");
                }
                exited.TrySetResult();
            }
            catch (Exception error) { exited.TrySetException(error); }
        };
        browserExits.Add(Task.WhenAll(ObserveBrowserExit(pid), exited.Task));
    }

    internal Task WaitForBrowserRelease() => Task.WhenAll(browserExits).WaitAsync(TimeSpan.FromSeconds(10));

    private async Task ObserveBrowserExit(uint pid)
    {
        Process process;
        try
        {
            process = Process.GetProcessById(checked((int)pid));
        }
        catch (ArgumentException) { Write("browser-process-already-released", pid); return; }
        using (process)
        {
            // The STA message loop ends during disposal; resource completion must not depend on it.
            await process.WaitForExitAsync().ConfigureAwait(false);
            Write("browser-process-released", pid);
        }
    }
}
