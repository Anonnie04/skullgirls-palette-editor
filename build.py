"""Build and smoke-test the independent Windows executable."""
from pathlib import Path
import subprocess
import sys
import os
import shutil
import zipfile

ROOT = Path(__file__).resolve().parent


def run(*args):
    subprocess.run([str(arg) for arg in args], cwd=ROOT, check=True)


if __name__ == '__main__':
    (ROOT / 'build').mkdir(exist_ok=True)
    manager = Path(os.environ.get('PALETTE_MANAGER_ROOT', ROOT.parent / 'Skullgirls Mod Manager')).resolve()
    if not (manager / 'dist' / 'Core.dll').is_file():
        raise SystemExit('Build Skullgirls Mod Manager first, or set PALETTE_MANAGER_ROOT to its source folder with dist/Core.dll.')
    os.environ['PALETTE_MANAGER_ROOT'] = str(manager)
    os.environ.setdefault('DOTNET_CLI_HOME', str(manager / '.build'))
    os.environ.setdefault('NUGET_PACKAGES', str(manager / '.packages'))
    os.environ['DOTNET_CLI_TELEMETRY_OPTOUT'] = '1'
    run('dotnet', 'build', ROOT / 'manager_bridge' / 'PaletteApply.csproj', '-c', 'Release', '--nologo',
        '-p:ManagerCorePath=' + str(manager / 'dist' / 'Core.dll'))
    run(sys.executable, 'test_direct_apply.py')
    if (manager / 'licenses').is_dir():
        shutil.copytree(manager / 'licenses', ROOT / 'third-party-licenses' / 'ModManager', dirs_exist_ok=True)
    shutil.copy2(manager / 'LICENSE', ROOT / 'manager_bridge' / 'LICENSE')
    shutil.copy2(manager / 'THIRD-PARTY-NOTICES.md', ROOT / 'third-party-licenses' / 'ModManager' / 'THIRD-PARTY-NOTICES.md')
    with zipfile.ZipFile(ROOT / 'manager_bridge' / 'source.zip', 'w', zipfile.ZIP_DEFLATED) as source:
        for name in ('Program.cs', 'PaletteApply.csproj', 'LICENSE'):
            source.write(ROOT / 'manager_bridge' / name, 'manager_bridge/' + name)
    run(sys.executable, 'test_palette.py')
    run(sys.executable, '-m', 'PyInstaller', '--noconfirm', '--distpath', ROOT,
        '--workpath', ROOT / 'build' / 'pyinstaller', ROOT / 'palette.spec')
    run(ROOT / 'Skullgirls Palette Editor.exe', '--smoke-test', ROOT / 'build' / 'packaged-ui.json')
