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
        try { callback(); }
        catch (Exception error)
        {
            failure.TrySetException(error);
            Record($"CALLBACK ERROR {error.GetType().Name}: {error.Message}");
        }
    }

    internal async Task Wait(Task signal)
    {
        var completed = await Task.WhenAny(signal, failure.Task).WaitAsync(TimeSpan.FromSeconds(10));
        if (failure.Task.IsCompleted) { await failure.Task; }
        await completed;
    }

    internal async Task<T> Wait<T>(Task<T> signal)
    {
        await Wait((Task)signal);
        return await signal;
    }
}
