# Building from source

[Back to the README](../README.md)

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
Workshop. See [Contributing](../CONTRIBUTING.md), [Releasing](RELEASING.md) and
[Changelog](../CHANGELOG.md). Runtime license notices accompany the release.

## Bridge source and licensing

The Python editor, decoder and visual theme use MIT. The separate direct-apply
bridge retains GPL-3.0 and loads the core from the user's existing Mod Manager
installation. Its source and license are bundled in `manager_bridge/source.zip`.
The portable executable can export that source archive:

```powershell
& '.\Skullgirls Palette Editor.exe' --export-apply-source destination.zip
```
