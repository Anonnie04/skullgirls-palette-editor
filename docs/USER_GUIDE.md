# Palette Editor user guide

[Back to the README](../README.md)

- [Set up the editor](#set-up-the-editor)
- [Choose a character and palette](#choose-a-character-and-palette)
- [Choose a preview sprite](#choose-a-preview-sprite)
- [Edit colors](#edit-colors)
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

## Save and share

### Palette images

**Save palette…** exports PNG or DDS. **Import PNG / DDS…** accepts palette images
with matching dimensions. These image files are useful for exchanging palette
colors; use a mod ZIP to include the gameplay palette as well.

### Mod Manager ZIP

1. Click **Save Mod Manager ZIP…**.
2. Enter the mod's name, description and version in **Mod details**.
3. Use a version such as `1.0.0`, with 2–4 numeric parts. Descriptions support multiple lines.
4. Click **Save ZIP…** and choose the destination.
5. Import the ZIP into Mod Manager, enable it, and apply it with Skullgirls closed.

The details are written to `mod.json` and remembered for the currently loaded
palette after a successful export. Cancelling the destination picker leaves the
details window open. PNG/DDS exports use the normal image save dialog.

Mod ZIPs include both the character-select DDS and the character's gameplay
palette in its FOIT metadata. Use the same game version that was used to export
the mod. Legacy embedded palettes are unsupported.

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
character in the editor. Export the palette from that installed state. Later
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
