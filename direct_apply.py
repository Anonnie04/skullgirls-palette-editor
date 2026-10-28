"""Prepare an editor-owned mod and apply it through the existing Manager core."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import uuid
from decoder import GFS
from palette import palette_source
from game_palette import patch


def helper_path():
    base = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
    path = base / 'manager_bridge' / 'PaletteApply.exe'
    if not path.is_file():
        path = base / 'manager_bridge' / 'bin' / 'Release' / 'net9.0' / 'PaletteApply.exe'
    if not path.is_file():
        raise ValueError('The direct-apply helper is missing. Rebuild the editor.')
    return path


def apply_palette(document, details, manager_root, operations):
    helper = helper_path()
    manager_root = Path(manager_root).resolve()
    source = palette_source(document.source)
    game = source.parent if source.name.lower() in ('data01', 'data02') else source
    operation = Path(operations).resolve() / uuid.uuid4().hex
    operation.mkdir(parents=True)
    expected = {}
    with GFS(source / 'characters-foits.gfs') as foits, GFS(source / 'sprites.gfs') as sprites:
        current_metadata = foits.read(f'characters/{document.character}.foit')
        current_dds = sprites.read(f'sprites/{document.character}_{document.slot}p.dds')
    if current_dds != document.dds:
        raise ValueError('This palette changed in the game after loading. Reload it before applying.')
    expected['characters-foits.gfs/' + document.metadata_internal] = hashlib.sha256(current_metadata).hexdigest()
    expected['sprites.gfs/' + document.internal] = hashlib.sha256(current_dds).hexdigest()
    # Merge into fresh metadata so edits to other palette slots remain present.
    updated, _ = patch(current_metadata, document.slot, document.original, document.colors)
    old_metadata = document.metadata
    try:
        document.metadata = current_metadata
        document.export(operation / 'palette.zip', 'zip', details, mark_saved=False)
    finally:
        document.metadata = old_metadata
    request = dict(ManagerRoot=str(manager_root), GameFolder=str(game), DataFolder=str(source),
                   Character=document.character, Zip=str(operation / 'palette.zip'), Expected=expected)
    request_file = operation / 'request.json'
    request_file.write_text(json.dumps(request, indent=2), encoding='utf-8')
    result = subprocess.run([str(helper), str(request_file)], capture_output=True, text=True, encoding='utf-8', errors='replace',
                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    (operation / 'apply.log').write_text(result.stdout + result.stderr, encoding='utf-8')
    if result.returncode:
        raise ValueError(result.stderr.strip() or result.stdout.strip() or 'Direct apply failed. See ' + str(operation / 'apply.log'))
    receipt = json.loads((operation / 'result.json').read_text(encoding='utf-8'))
    if receipt.get('status') != 'passed':
        raise ValueError('Installation verification did not complete.')
    document.metadata = updated
    document.dds = document.texture()
    document.original = document.colors.copy()
    document.mod_details = details.copy()
    return receipt
