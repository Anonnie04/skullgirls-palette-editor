# Local palette project format

The editor writes UTF-8 JSON with a trailing newline to `.sgpalette` files.
The format is independent of Mod Manager and Sprite Workshop. Projects contain
palette values and source identity; the original game assets are still required.
Project and draft files are limited to 2 MiB. Unknown versions, invalid colors
and mismatched dimensions are refused before edits are restored.

## Version 1

| Field | Value |
| --- | --- |
| `format` | `"skullgirls-palette-project"` |
| `version` | Integer `1` |
| `character` | Character key used by the game, such as `"annie"` |
| `slot` | Integer palette slot, 1–256 |
| `source.folder` | Absolute source data folder containing the game archives |
| `source.dds_sha256` | Lowercase SHA-256 of the original selected DDS bytes |
| `source.metadata_sha256` | Lowercase SHA-256 of the original complete character FOIT bytes |
| `original` | Original RGBA samples, shaped `[materials][16][4]` |
| `colors` | Edited RGBA samples, with the same shape as `original` |
| `mod_details` | Object with text `name`, `desc` and numeric version string `version` |

There must be 1–256 materials. Every RGBA channel is an integer from 0 to 255;
alpha retains the game's encoded meaning. Mod details use the same validation as
ZIP manifests. Unknown extra fields are ignored; saving emits the supported fields.
No executable content, sprite art, metadata payload or undo history is embedded.

The source hashes detect a different game/mod baseline. With explicit user review,
the editor applies only pixels where `colors` differs from `original` onto the
current palette; unedited pixels come from the new source. Material counts must
match. The reviewed project uses fresh game metadata for future exports.

## Writes and conflicts

Saving writes a sibling temporary file, flushes it with `fsync`, then uses
`os.replace` to replace the destination. A failed replacement preserves the
previous project and its saved checkpoint. The editor remembers the saved file's
SHA-256. Before saving to the same path, it refuses a changed or missing file and
directs the user to Save as. Atomic replacement prevents partial project files;
it does not guarantee persistence through every hardware or filesystem failure.

## Recovery envelope

Recovery uses the same project object inside a `.sgdraft` JSON envelope:

| Field | Value |
| --- | --- |
| `format` | `"skullgirls-palette-draft"` |
| `version` | Integer `1` |
| `written_at` | UTC ISO 8601 timestamp |
| `document` | Complete version 1 project object described above |
| `project_path` | Associated project path, or `null` for untitled work |
| `project_digest` | SHA-256 of that project's last known saved bytes, or `null` |

Draft filenames use a random per-document UUID, so separate documents and editor
instances do not share a writable draft. Drafts live in `Recovery/` beside the
source launcher or portable executable. They are local files, excluded from
source control and release archives. Source paths in projects and drafts may
contain personal folder names; review them before sharing.

Recovery is explicit and starts a separate unsaved project. A saved or discarded
recovery consumes the original draft only if its bytes still match those opened;
an updated draft from another editor is retained. Successfully saving a project,
or explicitly discarding its edits, removes that document's own draft. Failed or
cancelled loads preserve the outgoing document and its draft.
