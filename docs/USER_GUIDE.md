# Palette Editor user guide

[Back to the README](../README.md)

- [Set up the editor](#set-up-the-editor)
- [Choose a character and palette](#choose-a-character-and-palette)
- [Choose a preview sprite](#choose-a-preview-sprite)
- [Edit colors](#edit-colors)
- [Save projects and recover drafts](#save-projects-and-recover-drafts)
- [Save and share](#save-and-share)
- [Apply directly to the game](#apply-directly-to-the-game)
- [Use palettes with other mods](#use-palettes-with-other-mods)
- [Troubleshooting](#troubleshooting)

## Set up the editor

1. Download the **windows-x64.zip** from the [latest release](https://github.com/Anonnie04/skullgirls-palette-editor/releases/latest).
2. Extract the whole ZIP to a writable folder.
3. Open **Skullgirls Palette Editor.exe** or **Launch Palette Editor.cmd**.
4. Select your Skullgirls game folder using **Browse…** if it was not found automatically.

The portable release supports Windows x64 and includes Python and its libraries.
Previewing, editing and exporting a ZIP work independently of Mod Manager.

To apply changes directly, you also need [Skullgirls Mod Manager](https://github.com/Anonnie04/skullgirls-mod-manager)
and the .NET 9 Desktop Runtime. Version 0.3.16 is the tested Manager version.
Open the Manager once to set up its **Mods** and **Data** folders.

For game builds that verify protected archives, first use **Backups & tools →
Set up mod support** in Mod Manager with your own supported loader.
The editor does not include game files or compatibility loaders.

## Choose a character and palette

1. Choose a character and a **Palette slot**, then click **Load from game**.
2. The sprite preview appears on the left and the palette on the right.
3. Use **Scan game** to discover characters and slots if needed.

Available palette slots are discovered automatically and listed with a count.
Selecting another slot loads it for editing. **Palettes…** opens a thumbnail
chooser showing the current preview sprite in each installed palette.
Double-click a palette or select it and click **Edit palette**.
The editor checks for unsaved changes before switching.

The **Original** checkbox compares the preview against the palette loaded from
the game. After a successful direct apply, that applied palette becomes the new
reference.

## Choose a preview sprite

Click **Choose sprite…** above the preview to browse thumbnails of the loaded
character's sprites. Double-click a thumbnail or select it and click **Use sprite**.

Use Previous/Next to browse pages, or **Go to sprite** to jump to a sprite number.
The frame arrows and number field in the editor let you step through nearby sprites.
Thumbnails include your unsaved palette edits. Changing the preview sprite keeps
your color changes intact.

Preview uses neutral lighting; stage lighting and effects can look different in-game.

The preview selector compares **Requested** colors with **Stored** colors decoded
from the same gameplay metadata that ZIP export generates. It changes both the
sprite preview and palette swatches; editing fields always show your requested
color. **Difference** shows absolute errors: black means an exact match, brighter
pixels mean a larger difference. Swatches use the largest RGBA channel error;
the sprite shows the largest rendered channel error at each pixel.

Gold marks beside material rows flag storage differences. The comparison lists
the three materials with the largest RGBA errors on a 0–255 scale. Individual
shade edits may fit poorly into the game's limited gradient points; try
**Recolor material…** to preserve a ramp more closely. This is a palette-storage
preview, and stage lighting can still change the appearance. It works without
Mod Manager or Sprite Workshop. The **Original** checkbox still shows the loaded
reference sprite; selecting a preview mode returns to your edits.

## Edit colors

Each palette material has 16 shades. Click a palette box to select its shade,
or click the sprite to select the material and shade used by that pixel.

| Control | What it does |
| --- | --- |
| **Pick color…** | Changes the selected shade. |
| **Recolor material…** | Adjusts the material's shading ramp around the selected shade. |
| Hex field and **Set** | Sets a color directly using a value such as `#33aaff`. |
| **Undo** / **Redo** | Steps through your edits. |
| **Reset material** | Restores the selected material to its loaded reference. |
| **Original** | Shows the reference palette for comparison. |

The color picker opens beside the sprite. Drag the hue ring or the
saturation/brightness square to preview changes live on the sprite and palette.
You can also enter a hex color inside the picker.

Click **Apply color** to keep the result as one undo step. **Cancel** or Escape
restores the colors from before you opened the picker.

When recoloring a material, the selected shade is the reference: the wheel starts
with that box's color, and your chosen color is applied to that box while the other
shades adjust around it.

The pickers preserve game-encoded alpha. You can edit the alpha byte manually,
but it is not a conventional transparency control. Editing, undo and reset do not
write to the game; use direct apply or install an exported mod when ready.

## Save projects and recover drafts

**Save project** writes an editable `.sgpalette` file; **Save as…** keeps another
copy. **Open project…** restores the character, palette slot, edited RGBA colors
and export details. Use **Export details…** to set the name, description and
version without exporting anything. Undo history starts fresh when reopening.

Projects need the source game assets for sprite previews and mod ZIP preparation.
They contain palette samples and source fingerprints, not sprite art or character
metadata. If the original data folder moved, opening asks for its new location.
To use another game build, choose its game folder above, then select **Open
project… → Open project using selected game folder…**.
See [Project format](PROJECT_FORMAT.md) for the local JSON schema.

If the source palette or character metadata changed, the editor offers three
choices: reapply only the shades you edited onto the current source for review,
reload the current palette without those edits, or cancel. Check the sprite and
material mapping before saving the reviewed result. A game build with different
material dimensions cannot be rebased; locate the matching build instead.

Committed edits are autosaved approximately every 1.5 seconds to **Recovery**
beside the editor. Each open document gets a separate `.sgdraft` file, written by
flushing a temporary file and replacing the previous draft. Temporary picker
previews are excluded until committed. Drafts capture the latest completed
autosave; edits immediately before an unexpected exit may not have reached it.

After restarting, the status bar reports available drafts. Click **Recover draft…**
and choose a draft to review its character, slot and save time. Recovery opens a
separate unsaved project and warns if its linked project changed or disappeared.
The recovery menu also offers the selected game folder as an alternate source.
It never automatically replaces that project. Use **Save project** and choose a
destination; saving or explicitly discarding recovered work removes its original
draft if it has not changed. Drafts from other documents remain available.

Closing or switching with unsaved work offers **Yes** to save a project, **No** to
discard it, or **Cancel** to continue editing. Exporting PNG, DDS or ZIP files, or
applying to the game, does not save the editable project. If another editor or
process has changed an open project file, Save refuses to overwrite it; use
**Save as…** to keep both versions. Projects and drafts are entirely local and
do not require Manager profiles, Mod Manager or Sprite Workshop.

## Save and share

### Palette images

Click **Export PNG / DDS…** to choose a format and read its contents and limitations
before picking a destination. The dialog shows the character, slot, palette size
and source data folder. Cancelling the save picker keeps the format dialog open.

| Output | Contains | Compatibility |
| --- | --- | --- |
| **PNG palette image** | RGBA palette colors for sharing or reimporting | Import into a palette with matching dimensions. Use a mod ZIP for gameplay changes and installation files. |
| **DDS palette texture** | The character-select texture in the source game's layout | Use with a matching game build. Use a mod ZIP for gameplay changes and installation files. |
| **Mod ZIP** | Character-select DDS, full character metadata including gameplay palette changes, and mod details | Use the same game build and character mods as the source. Any later replacement of that metadata can override its palette changes. |

**Import PNG / DDS…** accepts palette images with matching dimensions. Exporting
all three formats works with Palette Editor alone; installing a ZIP requires a
compatible mod installer. Mod Manager is optional, and Sprite Workshop is not
required for exporting or direct apply.

### Mod Manager ZIP

1. Click **Export mod ZIP…**.
2. Review the source, game-build compatibility and metadata conflict explanation,
   then enter the mod's name, description and version in **Mod details**.
3. Use a version such as `1.0.0`, with 2–4 numeric parts. Descriptions support multiple lines.
4. Click **Export ZIP…** and choose the destination.
5. Install the ZIP with a compatible mod installer. With Mod Manager, import it,
   enable it, and apply with Skullgirls closed.

The details are written to `mod.json` and remembered for the currently loaded
palette after a successful export. Save a project to retain them across editor
sessions. Cancelling the destination picker leaves the details window open.
The chosen image format determines the save extension; a different extension is
refused rather than silently changing the output type.

Mod ZIPs include both the character-select DDS and the character's gameplay
palette in its FOIT metadata. Use the same game version that was used to export
the mod. The layout version reported in an unsupported-layout error describes
character metadata, not a game release number. Legacy embedded palettes are
unsupported and receive a specific DDS-based-build explanation. If the selected
gameplay palette cannot be exported, its details dialog explains why and disables
ZIP export before the destination picker; PNG/DDS color export remains available
for an already loaded document.

## Apply directly to the game

Apply any pending character mods in Mod Manager before loading the palette you
want to edit. Close Skullgirls before applying your changes.

1. Click **Apply palette to game…**.
2. Review the character, palette slot and game folder.
3. Enter the mod name, description and version, then click **Apply to game**.
4. If prompted, select the Mod Manager installation folder containing **Mods** and **Data**.
5. Keep the editor open until it reports that installation and verification have finished.

The editor creates or updates an enabled direct-palette mod for that character
in the Manager library. It preserves earlier direct edits to other slots,
applies the enabled mods, and verifies both the installed menu palette and
gameplay metadata. Mod Manager keeps its archive backups and rollback state.

Reopen Mod Manager to see the updated entry. To remove a direct palette mod,
disable it in Mod Manager and apply the remaining enabled mods. Use the Manager's
**Restore originals** option when you want to restore all managed archive baselines.

## Use palettes with other mods

Sprite Workshop mods and palette mods can be used together. Gameplay palettes
share the character's metadata file with sprite mods and other palette slots.

For ZIP export, apply the other mods you want to preserve before loading the
character in the editor. Export preparation reads the latest character metadata
to preserve unrelated slots and records. If the selected menu or gameplay palette
changed since loading, save your project and reopen it to review the current
source before exporting. Export the palette from that installed state. Later
mods replacing the same FOIT can override its gameplay palette; the Manager's
load order determines which replacement wins.

If you change another mod for a character that already has a direct-palette mod:

1. Disable that character's direct-palette mod in Mod Manager.
2. Apply your other mods.
3. Reload the character in the editor before making and applying new palette edits.

The editor detects a changed character baseline and explains these steps before
replacing anything. Stale palettes and externally modified archives are refused.

When Mod Manager's verified `data02` redirect is active, the editor follows it.
Selecting `data01` or `data02` explicitly uses that folder for loading; direct
apply requires the Manager's active archive folder.

## Troubleshooting

### Colors change at character select but not in a match

Older ZIPs that included only the DDS affect character select. Load and re-export
with the current editor to include the gameplay palette, then import and apply
the updated ZIP. Check whether a later character mod overrides its FOIT file.

### A shade looks different in gameplay

Gameplay uses a limited number of gradient points. Individual shade edits are
fitted to the material's existing gradient, so whole-material recoloring generally
transfers more closely. Stage lighting can also change the appearance.

The editor preserves other palette slots, animated effect records, sprite metadata
and art bytes. If the gameplay palette cannot be identified uniquely, export is
refused rather than guessing which color data to change.

### Apply reports changed files or another character mod

Reload a palette if the game's palette changed after you loaded it. For a changed
character mod, follow the steps in [Use palettes with other mods](#use-palettes-with-other-mods).
For an archive changed outside Mod Manager or an interrupted operation, resolve
the reported state in Mod Manager before trying again.

Direct-apply preparation files and logs are kept in **Direct Apply** beside the
editor. Mod Manager keeps the game archive backups in its own **Data** profiles.

### Get help

[Report an issue](https://github.com/Anonnie04/skullgirls-palette-editor/issues)
with the editor version, game version, character, palette slot, reproduction steps
and exact error text. Remove personal paths from log excerpts. Do not upload game
archives, executables, asset dumps or support DLLs.
