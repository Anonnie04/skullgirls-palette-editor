# Contributing

Use Windows x64, Python 3.12 with Tkinter, and the .NET 9 SDK for the bridge.
Install `requirements-dev.txt` in a virtual environment. See [Building from source](docs/BUILDING.md) for
building the required Mod Manager core and setting `PALETTE_MANAGER_ROOT`.

Run `python test_palette.py` for preview, color editing, project/recovery and export checks.
Use `python test_projects.py` for focused project persistence and recovery checks.
After building the bridge, run `python test_direct_apply.py` for install,
rollback and conflict checks against synthetic games. These tests require
neither a game installation nor game assets. `python scripts/build_release.py`
also tests the packaged executable and produces release archives.

For bug reports, include the editor version, selected character and palette
slot, game version and steps to reproduce. Include the error text or a small
relevant log excerpt with personal paths removed. Do not upload game archives,
the game executable, mod-support DLLs or copyrighted asset dumps.

The Python editor uses the MIT license, matching Sprite Workshop. The separate
bridge retains GPL-3.0. Preserve existing copyright and third-party notices.
