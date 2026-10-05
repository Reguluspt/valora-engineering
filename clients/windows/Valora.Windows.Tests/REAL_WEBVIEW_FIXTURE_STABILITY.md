# WIN-3R real-WebView fixture stability

Issue #116 repairs Windows post-merge certification of Issue #112 at baseline `bf37513ebc6a05a4d5cc620aa6569d0efef3f84a`. Classification: `TEST_INFRA_PARALLELISM`, with a fixture teardown ownership defect. Production App/Bridge code is unchanged.

## Reproduction and limits

Windows Client #13 attempt 1 failed 7/157 tests; attempt 2 failed 3/157. The attempt-2 TRX records simultaneous execution of the callback regression, external-navigation boundary case and replaced-control case between 00:44:50 and 00:45:01 UTC. There was no attempt 3.

Local observation retained the original deadlines, assertions and scheduling. Each fixture used a different profile and STA, so this was overlapping independent browser process groups rather than a shared-profile data race; Microsoft documents that ownership in the [WebView2 process model](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/process-model). The original task completed before `form.Close()`, control disposal and browser exit. Tracing observed up to five active fixtures across three xUnit collections, including teardown overlapping a successor in the same class.

The controlled experiment restricted only the task process and its children to one logical CPU while keeping three xUnit workers visible (`DOTNET_PROCESSOR_COUNT=3`). It used no background load, retries or runtime/security switches. This is a resource-pressure reproduction, not a claim that the hosted runner has the same hardware.

| Baseline experiment | Passed | Failed | Skipped |
| --- | ---: | ---: | ---: |
| Real-WebView group, normal local CPU resources | 27 | 0 | 0 |
| Real-WebView group, two CPU affinity | 27 | 0 | 0 |
| Affected methods individually, one CPU, seven invocations | 16 | 0 | 0 |
| Real-WebView group, three collections, one CPU | 11 | 16 | 0 |
| Full suite, three real-WebView collections, one CPU | 154 | 3 | 0 |
| Real-WebView group, only collection membership changed, one CPU | 27 | 0 | 0 |

In the local failing COM-exception callback case, initialization completed and `NavigationStarting` arrived, but `WebResourceRequested` never entered before the unchanged ten-second wait expired. No callback exception existed to transport. This regression uses WebView2 directly without App/Bridge behavior, so production bridge revocation or request handling cannot cause that failure. Under the collection-only comparison, both callback cases returned the exact original exception through the unchanged `Assert.Same(expected, actual)` assertion.

A separate deterministic regression blocks `FormClosed` teardown. It fails against the original fixture because the owning task has already completed. The repaired fixture keeps that task pending until the control, STA and browser are released.

## Bounded repair

Only `WebViewBoundaryTests`, `WebViewLifecycleTests` and `WebViewNativeBridgeTests` share `WebViewCollection`. Other collections retain xUnit's normal parallel execution; neither assembly-wide serialization nor `DisableParallelization` is enabled.

The fixture disposes its control, awaits the tracked browser process exit and WebView2 normal-exit event while the STA pump is available ([threading model](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/threading-model)), closes/disposes the form, joins its STA and then completes the owning task. The lifecycle test also registers the replacement browser so its release belongs to the same fixture. Exception dispatch preserves the original callback exception instance; a concurrent teardown error remains an explicit failure. Navigation deadlines remain ten seconds (45 seconds for existing public TLS cases), and the overall fixture deadline remains 60 seconds. No wait is retried.

`VALORA_WEBVIEW_TRACE_PATH` enables test-only JSONL evidence with fixture identity, timestamps, thread/apartment, profile, runtime/PID, navigation/callback entries, exception transport and teardown stages. It records synthetic/public request URLs, never request bodies or cookies. Windows CI retains this trace beside the TRX even on failure.

## Stability verification

After a locked restore and Release x64 build, use separate empty evidence directories. The harness stops at the first failure and refuses to overwrite a trace. CPU affinity and environment variables are restored on exit.

```powershell
./real-webview-stability.ps1 -Scope Isolated -Runs 3 -CpuCount 1 -EvidenceDirectory C:/evidence/isolated
./real-webview-stability.ps1 -Scope RealWebView -Runs 20 -EvidenceDirectory C:/evidence/group
./real-webview-stability.ps1 -Scope All -Runs 3 -CpuCount 1 -EvidenceDirectory C:/evidence/full
```

The complete suite contains 158 cases: all 157 baseline cases plus the teardown ownership regression. The real-WebView group contains 28 cases. Stability evidence, final build/publish/smoke/provenance, dual exact-head reviews and both exact-head CI results belong to the candidate reported in the Draft PR. None certifies a later merge SHA; Issues #116 and #112 stay open and WIN-4 stays on hold until Gate Owner exact-main certification.
