"""Real Manager transactions against synthetic games only."""
from pathlib import Path
import json
import tempfile
import shutil
import sys
import os
import numpy as np
from palette import PaletteDocument
from direct_apply import apply_palette
from decoder import GFS
from game_palette import locate, expand
from test_fixtures import fixture


def files(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}


def run():
    with tempfile.TemporaryDirectory(prefix='direct-apply-') as temporary:
        root = Path(temporary)
        game = fixture(root)
        (game / 'SkullGirls.exe').write_bytes(b'not executable; test fixture')
        manager = root / 'Manager'
        (manager / 'Data').mkdir(parents=True)
        (manager / 'dist').mkdir()
        editor_root = Path(sys.executable if getattr(sys, 'frozen', False) else __file__).resolve().parent
        manager_source = Path(os.environ.get('PALETTE_MANAGER_ROOT', editor_root.parent / 'Skullgirls Mod Manager'))
        for assembly in (manager_source / 'dist').glob('*.dll'):
            shutil.copy2(assembly, manager / 'dist' / assembly.name)
        keep = manager / 'Mods' / 'keep'
        (keep / 'sprites.gfs/sprites').mkdir(parents=True)
        (keep / 'mod.json').write_text(json.dumps(dict(id='fixture.keep', name='Other enabled mod', author='Test', desc='Preserve me', version='1.0.0')))
        (keep / 'enabled').touch()
        (keep / 'sprites.gfs/sprites/keep.bin').write_bytes(b'other mod payload')
        doc = PaletteDocument(game, 'annie', 1)
        colors = doc.colors.copy(); colors[1, :, :3] = (230, 40, 100); doc.replace(colors)
        receipt = apply_palette(doc, doc.mod_details, manager, root / 'operations')
        assert receipt['status'] == 'passed' and doc.dirty  # Applying is separate from saving editable work.
        with GFS(game / 'data01/sprites.gfs') as archive:
            first_dds = archive.read('sprites/annie_1p.dds')
            assert first_dds == doc.texture() and archive.read('sprites/keep.bin') == b'other mod payload'
        direct = [p for p in (manager / 'Mods').iterdir() if p.is_dir() and p != keep]
        assert len(direct) == 1 and json.loads((direct[0] / 'mod.json').read_text())['id'] == 'paletteeditor.direct.annie'
        assert (keep / 'enabled').exists()
        # An external archive change must refuse apply and restore the library/order.
        before_library = files(manager / 'Mods')
        archive_path = game / 'data01/sprites.gfs'
        valid_archive = archive_path.read_bytes()
        archive_path.write_bytes(valid_archive + b'outside change')
        altered = archive_path.read_bytes()
        colors = doc.colors.copy(); colors[1, :, :3] = (30, 180, 100); doc.replace(colors)
        try:
            apply_palette(doc, doc.mod_details, manager, root / 'operations')
        except ValueError as exc:
            assert 'outside' in str(exc).lower()
        else:
            raise AssertionError('External changes were overwritten')
        assert files(manager / 'Mods') == before_library and archive_path.read_bytes() == altered
        assert doc.dirty
        archive_path.write_bytes(valid_archive)
        # Applying another slot retains both the first DDS and its gameplay colors.
        second = PaletteDocument(game, 'annie', 2)
        colors = second.colors.copy(); colors[2, :, :3] = (20, 160, 210); second.replace(colors)
        apply_palette(second, second.mod_details, manager, root / 'operations')
        with GFS(game / 'data01/sprites.gfs') as archive:
            assert archive.read('sprites/annie_1p.dds') == first_dds
            assert archive.read('sprites/annie_2p.dds') == second.texture()
            assert archive.read('sprites/keep.bin') == b'other mod payload'
        with GFS(game / 'data01/characters-foits.gfs') as archive:
            data = archive.read('characters/annie.foit')
            counts, at = locate(data, 1, doc.original)
            assert np.all(expand(data, at, counts)[1, :, :3] == (230, 40, 100))
        assert len([p for p in (manager / 'Mods').iterdir() if p.is_dir()]) == 2
        assert (keep / 'enabled').exists()
        # A changed character mod hidden beneath our direct mod must not be lost.
        changed = manager / 'Mods' / 'changed-character'
        (changed / 'characters-foits.gfs/characters').mkdir(parents=True)
        (changed / 'mod.json').write_text(json.dumps(dict(id='fixture.changed', name='Changed character', author='Test', desc='Baseline guard', version='1.0.0')))
        (changed / 'enabled').touch()
        (changed / 'characters-foits.gfs/characters/annie.foit').write_bytes(b'changed character metadata')
        direct = next(p for p in (manager / 'Mods').iterdir() if p.is_dir() and p not in (keep, changed))
        (manager / 'Mods/order.json').write_text(json.dumps([keep.name, changed.name, direct.name]))
        before_library = files(manager / 'Mods')
        before_game = files(game)
        try:
            apply_palette(second, second.mod_details, manager, root / 'operations')
        except ValueError as exc:
            assert 'character mod' in str(exc).lower()
        else:
            raise AssertionError('Changed character metadata was overwritten')
        assert files(manager / 'Mods') == before_library and files(game) == before_game
    print('Direct apply passed: verified game assets, cumulative palette slots, other enabled mods, backups, stale/archive guards and library rollback.')


if __name__ == '__main__':
    run()
