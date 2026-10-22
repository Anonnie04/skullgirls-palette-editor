# Preview/export are standalone; direct apply connects to the user's Mod Manager.
from pathlib import Path
bridge = Path(SPECPATH) / 'manager_bridge' / 'bin' / 'Release' / 'net9.0'
bridge_files = [(str(path), 'manager_bridge') for path in bridge.glob('PaletteApply.*') if path.is_file() and path.suffix != '.pdb']
bridge_files.append((str(Path(SPECPATH) / 'manager_bridge' / 'source.zip'), 'manager_bridge'))
a = Analysis(['palette_app.py'], pathex=[], binaries=[], datas=bridge_files, hiddenimports=[],
             hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[],
             noarchive=False, optimize=0)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [],
          name='Skullgirls Palette Editor', debug=False,
          bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, disable_windowed_traceback=False)
