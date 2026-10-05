using System.Diagnostics;

namespace Valora.Windows.Tests;

internal sealed class WebViewTestDiagnostics
{
    private readonly Stopwatch clock = Stopwatch.StartNew();
    private readonly List<string> events = new();
    private readonly TaskCompletionSource failure = new(TaskCreationOptions.RunContinuationsAsynchronously);

    internal void Record(string message)
    {
        lock (events)
        {
            if (events.Count < 64) { events.Add($"{events.Count + 1:D2} {clock.ElapsedMilliseconds}ms {message}"); }
        }
    }

    internal string Trace { get { lock (events) { return string.Join(Environment.NewLine, events); } } }

    // Transfer callback failures to the awaited test task; do not recover or rethrow into COM.
    internal void Capture(Action callback)
    {
        WebViewFixtureTrace.Current?.Write("captured-callback-entry");
        try { callback(); }
        catch (Exception error)
        {
            failure.TrySetException(error);
            WebViewFixtureTrace.Current?.Write("callback-exception-transport", new { type = error.GetType().Name, error.Message });
            Record($"CALLBACK ERROR {error.GetType().Name}: {error.Message}");
        }
    }

    internal async Task Wait(Task signal)
    {
        WebViewFixtureTrace.Current?.Write("signal-wait-start");
        var completed = await Task.WhenAny(signal, failure.Task).WaitAsync(TimeSpan.FromSeconds(10));
        WebViewFixtureTrace.Current?.Write("signal-wait-completed", failure.Task.IsCompleted);
        if (failure.Task.IsCompleted) { await failure.Task; }
        await completed;
    }

    internal async Task<T> Wait<T>(Task<T> signal)
    {
        await Wait((Task)signal);
        return await signal;
    }
}
