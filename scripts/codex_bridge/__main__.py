"""Run the harmless P1 replay. No live-network or real-executor switch exists."""

import argparse
import json
from pathlib import Path
import tempfile

from .agent import Agent, FIXTURE_CONTENT, FakeExecutor, invocation_manifest
from .offline import FIXTURE_KEY, FIXTURE_NOW, FIXTURE_SHA, OfflineQueue, fixture_issue
from .schema import Policy
from .state import Journal


def main():
    parser = argparse.ArgumentParser(description="P1 offline fixture only; P2 unavailable")
    parser.add_argument("--state-dir", type=Path, required=True, help="Local protected state, outside repository")
    parser.add_argument("--codex-binary", type=Path, help="Emit disabled invocation manifest; never launches")
    args = parser.parse_args()
    state = args.state_dir.resolve()
    repo = Path(__file__).resolve().parents[2]
    if state == repo or repo in state.parents:
        parser.error("state directory must be outside the repository")
    with tempfile.TemporaryDirectory(prefix="valora-bridge-fixture-") as temporary:
        workspace = Path(temporary).resolve()
        (workspace / "fixture.txt").write_bytes(FIXTURE_CONTENT)
        policy = Policy(workspace, FIXTURE_SHA)
        journal = Journal(state)
        try:
            control = fixture_issue(policy, number=1)
            control["body"] = "CONTROL — DO NOT DISPATCH"
            queue = OfflineQueue(policy, [control, fixture_issue(policy)])
            executor = FakeExecutor()
            agent = Agent(policy, FIXTURE_KEY, queue, journal, executor,
                          lambda: FIXTURE_SHA, clock=lambda: FIXTURE_NOW)
            report = {**agent.once(), "fake_executor_calls": executor.calls,
                      "live_network_calls": 0, "inference_calls": 0,
                      "results": [json.loads(body) for body in queue.results.values()]}
            if args.codex_binary:
                report["codex_invocation"] = invocation_manifest(args.codex_binary, policy)
            print(json.dumps(report, indent=2))
            return 0 if report["status"] == "OFFLINE_CYCLE_COMPLETE" else 2
        except Exception:
            print('{"status":"BLOCKED","reason":"OFFLINE_REPLAY_FAILED"}')
            return 2
        finally:
            journal.close()


if __name__ == "__main__":
    raise SystemExit(main())
