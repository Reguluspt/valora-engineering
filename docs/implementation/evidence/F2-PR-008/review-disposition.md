# F2-PR-008 review finding disposition

The first frozen manifest (`b0a11c70496e7459a649f6e405ec625a31c096845d1370e723f5c856296a49c4`) received Reviewer A PASS and Reviewer B BLOCKER. Because the browser evidence changed, those verdicts are invalid for the replacement snapshot. Both independent reviewers must inspect the new frozen manifest before commit.

| Finding | Classification | Disposition |
| --- | --- | --- |
| `15-keyboard-focus.jpg` was byte-for-byte identical to `12-empty.jpg`, so it did not prove keyboard focus. | VALID | Re-captured the existing error/retry fixture with the “Thử lại” button reached by three keyboard Tab presses. Browser accessibility state reported that button focused; computed `:focus-visible` was true with white 2 px and blue 4 px ring. The replacement image differs from both the empty and unfocused error screenshots. |
| Focus-ring contrast within drawer tabs and table rows was not verified by the first review. | ADVISORY | The repaired primary recovery-button capture proves one visible keyboard focus state. Existing `:focus-visible` primitive styles apply to shared buttons, command bar, table, panel and drawer controls; no CSS change was required. |
| Stale F2 progress wording in CODEX.md. | ADVISORY | Product Owner's task-specific baseline decision supersedes only this stale progress gate. CODEX remains otherwise canonical and unchanged. |

No production file was edited for this correction. The affected browser state was rerun; the replacement screenshot and this disposition are included in the new manifest. The original Reviewer A verdict will be rerun because a reviewed evidence file changed.
