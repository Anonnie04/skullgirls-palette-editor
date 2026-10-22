"""Build and verify allowlisted Windows and matching source release archives."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from version import __version__

SOURCE_FILES = '''.gitignore .gitattributes .python-version LICENSE README.md
CHANGELOG.md CONTRIBUTING.md THIRD_PARTY_NOTICES.txt requirements.txt requirements-dev.txt
build.py palette.spec palette_app.py palette.py palette_ui.py palette_browser.py
color_wheel.py decoder.py direct_apply.py game_palette.py mod_details.py mod_info.py
sprite_browser.py theme.py test_palette.py test_direct_apply.py test_fixtures.py version.py
manager_bridge/Program.cs manager_bridge/PaletteApply.csproj manager_bridge/LICENSE
scripts/build_release.py docs/RELEASING.md docs/USER_GUIDE.md docs/BUILDING.md docs/licenses/README.md docs/licenses/Tcl.txt
docs/licenses/Tk.txt .github/workflows/windows.yml .github/ISSUE_TEMPLATE/bug_report.md'''.split()
SOURCE_FILES.append('Launch Palette Editor.cmd')


def run(*args):
    subprocess.run([str(arg) for arg in args], cwd=ROOT, check=True)


def licenses():
    notices = {}
    for name in ('numpy', 'Pillow', 'pyinstaller', 'pyinstaller-hooks-contrib'):
        distribution = importlib.metadata.distribution(name)
        found = 0
        for file in distribution.files or []:
            if not Path(file).name.lower().startswith(('license', 'licence', 'copying', 'notice')):
                continue
            path = Path(distribution.locate_file(file))
            if not path.is_file():
                continue
            label = str(file).replace('\\', '/').replace('..', 'parent').replace('/', '__')
            notices[f'third-party-licenses/{name}/{label}'] = path.read_bytes()
            found += 1
        if not found:
            raise RuntimeError(f'No license notices found for {name}')
    python_license = next((Path(sys.base_prefix) / name for name in ('LICENSE.txt', 'LICENSE')
                           if (Path(sys.base_prefix) / name).is_file()), None)
    if python_license is None:
        raise RuntimeError('Cannot locate the bundled Python license')
    notices['third-party-licenses/Python/LICENSE.txt'] = python_license.read_bytes()
    import tkinter
    window = tkinter.Tk()
    window.withdraw()
    try:
        libraries = [Path(window.tk.eval('info library')), Path(window.tk.eval('set tk_library'))]
    finally:
        window.destroy()
    for name, library in zip(('Tcl', 'Tk'), libraries):
        path = next((library / file for file in ('license.terms', 'license', 'LICENSE')
                     if (library / file).is_file()), ROOT / 'docs' / 'licenses' / f'{name}.txt')
        notices[f'third-party-licenses/{name}/LICENSE.txt'] = path.read_bytes()
    for path in (ROOT / 'third-party-licenses' / 'ModManager').rglob('*'):
        if path.is_file():
            notices[path.relative_to(ROOT).as_posix()] = path.read_bytes()
    return notices


def write_zip(path, files):
    prefix = f'Skullgirls-Palette-Editor-{__version__}'
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, content in sorted(files.items()):
            if name.startswith('/') or '..' in Path(name).parts:
                raise ValueError('Invalid package path')
            archive.writestr(f'{prefix}/{name}', content)
    with zipfile.ZipFile(path) as archive:
        if archive.testzip():
            raise RuntimeError(f'Corrupt release archive: {path}')


def main():
    if os.name != 'nt' or platform.architecture()[0] != '64bit':
        raise SystemExit('Build the supported portable release on Windows x64')
    run(sys.executable, 'build.py')
    executable = ROOT / 'Skullgirls Palette Editor.exe'
    run(executable, '--self-test')
    smoke = json.loads((ROOT / 'build' / 'packaged-ui.json').read_text())
    if smoke.get('ui') != 'passed':
        raise RuntimeError('Packaged UI smoke test failed')
    source = {name: (ROOT / name).read_bytes() for name in SOURCE_FILES}
    portable = {name: source[name] for name in ('README.md', 'LICENSE', 'CHANGELOG.md', 'CONTRIBUTING.md',
                                               'docs/USER_GUIDE.md', 'docs/BUILDING.md', 'docs/RELEASING.md',
                                               'manager_bridge/LICENSE',
                                               'THIRD_PARTY_NOTICES.txt', 'Launch Palette Editor.cmd')}
    portable[executable.name] = executable.read_bytes()
    portable['manager_bridge/source.zip'] = (ROOT / 'manager_bridge' / 'source.zip').read_bytes()
    portable.update(licenses())
    release = ROOT / 'release'
    release.mkdir(exist_ok=True)
    packages = [release / f'Skullgirls-Palette-Editor-v{__version__}-windows-x64.zip',
                release / f'Skullgirls-Palette-Editor-v{__version__}-source.zip']
    write_zip(packages[0], portable)
    write_zip(packages[1], source)
    checksums = []
    for path in packages:
        with path.open('rb') as stream:
            checksums.append(f'{hashlib.file_digest(stream, "sha256").hexdigest()}  {path.name}')
    (release / 'SHA256SUMS.txt').write_text('\n'.join(checksums) + '\n', encoding='utf-8')
    print(json.dumps({'version': __version__, 'tests': 'passed', 'assets': [str(p) for p in packages]}, indent=2))


if __name__ == '__main__':
    main()
