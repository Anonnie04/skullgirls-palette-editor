# Palette Editor — improvement plan

Date: 26 October 2026

Status: Standalone items 1–3 implemented and included in the rebuilt local EXE;
optional integration work remains proposed.

Release validation (28 October 2026): the full 0.2.0 release pipeline passed on
Windows x64 using Python 3.12.11 and the pinned build dependencies, with the bridge
built against the documented Mod Manager 0.3.16 source revision. Source tests,
packaged UI smoke tests and bundled self-tests passed. Portable and corresponding
source archives include the required notices and bridge source. Real-game
visual/install checks remain.

## Design principle

Palette Editor is a standalone editing and export application. Loading palettes, previewing sprites, recoloring, undo/redo and PNG/DDS/mod ZIP export must work without Sprite Workshop or Mod Manager installed. Mod Manager is an optional installation bridge. The existing **Apply palette to game** feature uses that bridge; this plan does not imply that standalone direct installation already exists.

This plan is based on documentation and selected source inspection, not a completed runtime audit. Effort estimates are relative.

## 1. Preview the colors that gameplay can actually store

**Progress (28 October 2026):** Added Requested, Stored and Difference preview
modes, material error highlights and ranked fitting errors. Stored colors are
decoded from the same patched metadata used by ZIP export. Synthetic tests
cover exact fits, difficult gradients, later slots, undo/redo and preview controls
without Manager or Workshop. Release-pipeline and packaged checks passed;
real-game visual checks remain.

**Priority: High · Effort: Medium · Standalone**

Gameplay uses limited gradient points, so individual shade edits are fitted and can differ from the requested colors. Show a comparison between requested colors and the reconstructed palette produced by the existing gameplay patcher.

- Offer requested/stored preview modes and a difference view.
- Highlight materials with the largest fitting differences.
- Explain when whole-material recoloring will preserve the intended appearance more closely.
- Describe this as a palette-storage preview; stage lighting can still affect appearance.

**Acceptance:** The stored preview matches colors decoded from generated metadata. Exact-fit edits show no difference. A difficult gradient produces an understandable comparison before export. Manager and Workshop are not installed during this check.

## 2. Save editable palette projects and recover drafts

**Progress (28 October 2026):** Audited the existing in-memory saved checkpoint;
there was no editable project format or recovery mechanism. Added local versioned
`.sgpalette` projects, atomic per-document drafts, explicit recovery and source
change review. Project save checkpoints include export details; exporting and
applying no longer mark editable work saved. ZIP preparation preserves fresh
unrelated slots and metadata and refuses a stale target palette. Tests cover
round trips, interrupted writes, conflicting saves, source rebasing, independent
drafts, and actual UI save/open/recover/cancel controls. Release-pipeline and
packaged checks passed; real-game checks remain. See [Project format](PROJECT_FORMAT.md).

**Priority: High · Effort: Medium · Standalone**

Provide a documented local project format for resuming work, including the character, slot, source identity, edited colors and export details. Audit existing persistence first and extend it rather than introducing competing save mechanisms.

- Distinguish saving editable work from exporting a palette or distributable mod.
- Preserve a recoverable draft after an unexpected exit using atomic writes.
- Detect when the original game palette has changed and offer a clear review/reload path.
- Preserve unrelated slots and metadata when preparing an export.

**Acceptance:** A user can close and reopen a project without losing edits or export details. Recovery does not silently overwrite newer work. Everything is stored locally without Manager profiles.

## 3. Make export compatibility explicit

**Progress (28 October 2026):** Added PNG/DDS format selection with contents and
compatibility notes before choosing a destination. ZIP details explain the source
game/mod baseline, full character metadata conflicts and optional installer use.
ZIP compatibility is checked before the save picker, with specific legacy and
unsupported-layout explanations; image export stays available for loaded work.
Conventional ZIP payloads and mod metadata are unchanged. Synthetic UI tests cover
format selection, cancellation, extensions, complete ZIP contents and unavailable
gameplay export without consulting Manager or Workshop. Real-game checks remain.

**Priority: Medium · Effort: Medium · Standalone**

Present what each output contains: an image palette, a DDS palette, or a complete mod package containing menu and gameplay changes. Explain the selected game's compatibility constraints before export.

For packages containing full character metadata, explain that another replacement of that metadata can override palette changes. This applies to any installation workflow, not just packages produced by Workshop. Do not make installing another tool a prerequisite for exporting usable files.

**Acceptance:** The user can choose the correct output and see its limitations with Palette Editor alone. ZIP exports retain complete payloads and normal metadata. Unsupported legacy layouts receive a specific explanation.

## Optional Mod Manager integration

### Improve the existing direct-apply bridge

**Priority: Medium within the optional integration · Effort: Medium**

Add structured helper progress for preparing, checking, staging, installing and verifying. Expose an **Open operation log** action and a specific recovery step for failed operations. Cancellation must respect the Manager's transaction boundaries.

Keep bridge setup within the optional Apply workflow. A missing Manager must not block startup, editing, saving or exporting, and should not prompt installation during those activities. Sprite Workshop is never required for this bridge.

**Acceptance:** With Manager installed, slow operations show progress and failures explain recovery. Without Manager, the standalone editor remains fully usable and the optional Apply action explains its dependency when invoked.

### Consider composable palette packages later

**Priority: Low · Effort: Large · Optional research**

A future Manager extension could apply palette operations over compatible character metadata from any supported package. Evaluate this as an optional package enhancement, not the editor's core format or a prerequisite for releases. Preserve complete conventional exports and detect consumer support explicitly.

**Acceptance:** Enhanced packages cannot silently lose palette changes in older consumers. Ordinary exports work without the extension. Testing does not require Workshop to be installed.

## Suggested order

1. Add the stored-gameplay-palette comparison.
2. Audit and improve editable project persistence and draft recovery.
3. Clarify standalone export compatibility.
4. Improve the optional apply bridge independently; defer package composition until its benefits and format are established.

## References

- [User workflow and compatibility constraints](USER_GUIDE.md)
- [Direct-apply caller](../direct_apply.py)
- [Gameplay palette patching](../game_palette.py)
