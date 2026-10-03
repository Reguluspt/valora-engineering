---
name: valora-live-authority-bootstrap
description: Verify live Valora main, CODEX, exact CI and task authority before implementation, handoff or memory recall.
---

# Live authority bootstrap

Fetch origin from the assigned checkout. Verify live main, task branch HEAD and CODEX blob against the current task contract; read relevant CODEX sections from that verified baseline. Inspect the assigned Issue/PR live, and verify CI's head SHA, completion and SUCCESS for the exact claimed baseline. Chat, handoff and OpenViking cannot certify any current state. Stop on a material authority or baseline mismatch.

Before recall or work, output:

```text
PROJECT AUTHORITY READY: YES/NO
live main:
CODEX blob:
exact-main CI:
current gate:
active task:
conflicts:
next authorized action:
```

Use the [operating profile](../../../docs/plan/VALORA_OPENVIKING_OPERATING_PROFILE_V1.md) only after this bootstrap. Preserve CODEX precedence and the current task's allowed scope. Read only needed authority; do not reconstruct history.
