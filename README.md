# Skullgirls Palette Editor

A Windows palette editor for Skullgirls, with sprite previews, a live color wheel,
palette-slot browsing and verified installation through Skullgirls Mod Manager.

[Download the latest release](https://github.com/Anonnie04/skullgirls-palette-editor/releases/latest) · [Report an issue](https://github.com/Anonnie04/skullgirls-palette-editor/issues) · [Sprite Workshop](https://github.com/Anonnie04/skullgirls-sprite-workshop) · [Mod Manager](https://github.com/Anonnie04/skullgirls-mod-manager)

Extract the full Windows release ZIP to a writable folder. Windows x64 is supported.
The release includes Python and its libraries. Direct apply additionally requires
Skullgirls Mod Manager 0.3.16 (the tested version) and the .NET 9 Desktop Runtime.
For protected game archives, first use **Backups & tools → Set up mod support**
in Mod Manager with your own supported loader. No game files or loaders are bundled.

Open **Skullgirls Palette Editor.exe** or **Launch Palette Editor.cmd**. Preview, editing and ZIP export run independently. Direct apply connects to your existing Skullgirls Mod Manager folder and uses its .NET 9 runtime and backup system.

Choose your Skullgirls game folder, character and palette slot, then **Load from game**. Use **Scan game** to discover characters and slots. The sprite preview is on the left and the palette is on the right. Browse frames or click the sprite to select its material and shade. **Original** compares against the loaded palette.

Available palette slots are discovered automatically and listed with a count. Selecting another slot loads it for editing. **Palettes…** opens a thumbnail chooser showing the current preview sprite in each installed palette. Double-click a palette or choose **Edit palette**. Unsaved edits are checked before switching.

**Apply palette to game…** installs directly without a manual ZIP import. Review the palette slot and game folder, enter the mod details, close Skullgirls, and click **Apply to game**. The editor registers an enabled direct-palette mod in Mod Manager, preserves previous direct edits to other slots, applies enabled mods, and verifies the installed DDS and gameplay metadata. Mod Manager retains its usual archive backups and rollback state. Reopen Mod Manager to see the updated entry and manage or restore it there. Apply pending character mods in the manager before loading a palette; stale or externally modified files are refused. ZIP export remains available for sharing.

Use **Choose sprite…** above the preview to browse the loaded character's sprites as thumbnails. Select a thumbnail and click **Use sprite**, or double-click it. Previous/Next browse pages, and **Go to sprite** jumps directly to a sprite number. Thumbnails use the current palette, including your unsaved edits. Choosing a sprite leaves your palette changes intact; the frame arrows and number field remain available for stepping through nearby sprites.

If you later change another mod for that same character, disable the character's direct-palette mod in Mod Manager, apply your other mods, and reload the character in the editor before applying new palette edits. The editor detects a changed character baseline and explains these steps before anything is replaced.

Pick a color, enter a hex color, or **Recolor material** to change a shading ramp. Color pickers preserve game-encoded alpha; manual alpha editing is available. Undo, redo and reset material leave the game unchanged.

**Pick color** and **Recolor material** open a color wheel beside the sprite. Drag the hue ring or the saturation/brightness square to preview changes live on the sprite and palette. You can also enter a hex color in the picker. **Apply color** keeps the result as one undo step; **Cancel** or Escape restores the starting colors.

Material recoloring uses the selected shade as its reference: the wheel starts with that box's color, and the color you choose is applied to that box while the other shades adjust around it.

**Save palette** exports PNG or DDS. Import accepts palette images of matching dimensions. **Save Mod Manager ZIP** packages your palette for import into Skullgirls Mod Manager. Sprite Workshop mods and palette mods can be used together; mods replacing the same palette slot follow manager load order. Match the game version used for export. Legacy embedded palettes are unsupported.

Before saving a mod ZIP, the **Mod details** window lets you enter its name, description and version number. Descriptions support multiple lines. Use a version such as `1.0.0` (2–4 numeric parts). Click **Save ZIP…** to choose a destination; these values are written into `mod.json`. Cancelling the destination picker keeps the details window open. Successful exports remember the details for the currently loaded palette. PNG/DDS exports use the normal image save dialog.

Mod ZIPs include the menu DDS and the character's embedded gameplay palette in its FOIT file. Earlier exports containing only the DDS affect character select; re-export them with the updated editor. Gameplay uses a limited number of gradient points, so isolated shade edits are fitted to the material's existing gradient. Whole-material recoloring generally transfers more closely. Other palette slots, animated effect records, sprite metadata and art bytes are preserved. Exports refuse palettes whose gameplay color span cannot be identified uniquely.

Gameplay palettes share the character metadata file with sprite mods and other palette slots. Load the game after applying the other mods you want to preserve, then export the palette mod. Later mods replacing that same FOIT can override it. The editor follows Mod Manager's verified `data02` redirect when active; selecting `data01` or `data02` explicitly uses that folder.

## Source and build

Use Python 3.12 with Tkinter. Install `requirements.txt`, then run `python palette_app.py`. Run `python test_palette.py` for the synthetic archive, preview, history and export checks.

For a full Windows build, install the .NET 9 SDK and set up Python:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

Clone [Mod Manager](https://github.com/Anonnie04/skullgirls-mod-manager) beside this
checkout as `Skullgirls Mod Manager`, check out compatible commit
`768685b1c92cb40c377e0c1f7d0e437b97298f2f` (0.3.16), and run its `Build.ps1`.
If it lives elsewhere, set `$env:PALETTE_MANAGER_ROOT='C:\path\to\manager-source'`.
This folder must contain `dist/Core.dll`, `LICENSE` and the manager notices.

```powershell
python build.py                  # compile bridge, test, build EXE and smoke-test
python test_direct_apply.py      # optional focused synthetic install checks
python scripts/build_release.py # full build + packaged tests + release ZIPs
```

The build compiles the bridge against the installed Manager core without bundling
that core. Tests create synthetic game archives and never apply to your installed
game. GitHub Actions runs the Windows build and retains portable/source ZIPs and
SHA-256 checksums as artifacts, using read-only workflow permissions like Sprite
Workshop. See [Contributing](CONTRIBUTING.md), [Releasing](docs/RELEASING.md) and
[Changelog](CHANGELOG.md). Runtime license notices accompany the release.

This unofficial tool reads user-supplied game assets. No Skullgirls assets are distributed. The Python editor, decoder and visual theme use the MIT license. The separate direct-apply bridge uses GPL-3.0; its source and license are in `manager_bridge/source.zip`, also exportable from a packed executable with `--export-apply-source destination.zip`. It loads the core from your existing Mod Manager installation rather than redistributing it.
