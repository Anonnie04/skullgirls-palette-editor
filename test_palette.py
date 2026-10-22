"""Synthetic palette tests. Never changes installed game archives."""
import io
import json
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch
import tkinter as tk
from types import SimpleNamespace
import numpy as np
from PIL import Image
from decoder import GFS
from palette import PaletteDocument, palette_slots
from test_fixtures import fixture


def run():
    with tempfile.TemporaryDirectory(prefix='palette-tests-') as folder:
        root = Path(folder)
        game = fixture(root)
        assert palette_slots(game, 'annie') == [1, 2]
        doc = PaletteDocument(game, 'annie', 1)
        assert doc.texture() == doc.dds
        original = doc.colors.copy()
        preview = np.array(doc.render(0))
        assert preview.shape == (16, 16, 4)
        assert doc.sample(0, 0, 0) == (1, 0)
        assert doc.sample(0, -1, 0) is None
        doc.recolor(1, (255, 20, 80))
        assert np.array_equal(original[:, :, 3], doc.colors[:, :, 3])
        assert not np.array_equal(preview, np.array(doc.render(0)))
        assert np.array_equal(preview, np.array(doc.render(0, original=True)))
        assert doc.dirty
        changed = doc.colors.copy()
        doc.undo()
        assert np.array_equal(doc.colors, original) and not doc.dirty
        doc.redo()
        assert np.array_equal(doc.colors, changed)
        doc.set_color(2, 8, (23, 45, 67, 91))
        with Image.open(io.BytesIO(doc.texture())) as image:
            assert np.array_equal(np.array(image.convert('RGBA')), doc.colors)
        doc.export(root / 'palette.zip', 'zip')
        assert not doc.dirty
        with zipfile.ZipFile(root / 'palette.zip') as archive:
            assert set(archive.namelist()) == {'mod.json', 'sprites.gfs/sprites/annie_1p.dds', 'characters-foits.gfs/characters/annie.foit'}
            assert json.loads(archive.read('mod.json'))['id'].startswith('paletteeditor.annie.1.')
            assert archive.read('sprites.gfs/sprites/annie_1p.dds') == doc.texture()
            from game_palette import patch as patch_palette, locate, expand
            fixed = archive.read('characters-foits.gfs/characters/annie.foit')
            expected, spans = patch_palette(doc.metadata, 1, doc.original, doc.colors)
            assert fixed == expected and len(fixed) == len(doc.metadata)
            allowed = np.zeros(len(fixed), dtype=bool)
            for offset, size in spans:
                allowed[offset:offset + size] = True
            assert np.array_equal(np.frombuffer(fixed,np.uint8)[~allowed], np.frombuffer(doc.metadata,np.uint8)[~allowed])
            counts, at = locate(doc.metadata, 1, doc.original)
            assert spans
            # A later slot is located across variable-length effect data.
            second = PaletteDocument(game, 'annie', 2)
            solid = second.colors.copy()
            solid[1, :, :3] = (230, 40, 100)
            patched, spans2 = patch_palette(second.metadata, 2, second.original, solid)
            counts2, at2 = locate(second.metadata, 2, second.original)
            assert at2 > at + sum(counts) * 4
            assert np.array_equal(expand(patched,at2,counts2)[1,:,:3], solid[1,:,:3])
            assert patched[at:at + sum(counts) * 4] == second.metadata[at:at + sum(counts) * 4]
            assert locate(patched,2,solid)[1] == at2
            unchanged, no_spans = patch_palette(doc.metadata,1,doc.original,doc.original)
            assert unchanged == doc.metadata and not no_spans
            for bad in (b'', doc.metadata[:30]):
                try:
                    patch_palette(bad,1,doc.original,doc.colors)
                except ValueError:
                    pass
                else:
                    raise AssertionError('Truncated metadata accepted')
        for kind in ('png', 'dds'):
            doc.export(root / ('palette.' + kind), kind)
            other = PaletteDocument(game, 'annie', 1)
            other.import_image(root / ('palette.' + kind))
            assert np.array_equal(other.colors, doc.colors)
        for path, kind in ((game / 'palette.zip', 'zip'), (root / 'bad', 'other')):
            try:
                doc.export(path, kind)
            except ValueError:
                pass
            else:
                raise AssertionError('Unsafe/invalid output accepted')
        Image.new('RGBA', (17, 4)).save(root / 'wrong.png')
        try:
            doc.import_image(root / 'wrong.png')
        except ValueError:
            pass
        else:
            raise AssertionError('Wrong dimensions accepted')
        # Test actual editor wiring without opening file dialogs.
        from palette_app import create_app
        window, editor = create_app()
        window.withdraw()
        assert window.title() == 'Skullgirls Palette Editor'
        editor.doc = doc
        editor.frame_box.configure(to=len(doc.frame_indices))
        editor.refresh()
        # All installed slots are discoverable and can be previewed without edits.
        editor.game.set(str(game))
        editor.character.set('Annie')
        editor.scan_slots()
        assert tuple(editor.slots['values']) == ('1', '2') and editor.palette_count.get() == '2 palettes'
        from palette_browser import PaletteCatalog
        catalog = PaletteCatalog(doc, doc.frame_indices[0])
        palette_snapshot = doc.colors.copy()
        assert catalog.frame_indices == [1, 2]
        assert not np.array_equal(np.array(catalog.render(1)), np.array(catalog.render(2)))
        assert np.array_equal(doc.colors, palette_snapshot)
        loaded_slots = []
        with patch.object(editor, 'load', new=lambda: loaded_slots.append(editor.slot.get())):
            editor.choose_palette()
            editor.sprite_browser.choose(1)
            window.update()
        assert loaded_slots == ['2'] and np.array_equal(doc.colors, palette_snapshot)
        editor.slot.set('1')
        # The Apply UI queues work and restores controls after a verified result.
        editor.open_apply()
        assert editor.mod_dialog.title() == 'Apply palette to game'
        with patch('palette_ui.apply_palette', return_value={'backups': 'fixture backups', 'status': 'passed'}) as apply, patch('palette_ui.filedialog.askdirectory', return_value=str(root / 'Manager')):
            editor.mod_dialog.submit()
            assert editor.applying and not editor.confirm_discard()
            window.after(300, window.quit)
            window.mainloop()
            assert apply.called and not editor.applying and not editor.loading
        assert editor.apply_button.instate(['!disabled']) and 'applied and verified' in editor.status.get()
        # Manifest editing happens before the destination picker and round-trips text.
        old_details = doc.mod_details.copy()
        old_colors = doc.colors.copy()
        old_history = len(doc.undo_stack)
        editor.export('zip')
        dialog = editor.mod_dialog
        dialog.name.set('')
        with patch('palette_ui.filedialog.asksaveasfilename') as save_as:
            dialog.submit()
            assert dialog.error.get() and not save_as.called
        dialog.name.set('Candy Annie — test')
        dialog.description.delete('1.0', 'end')
        description = 'Pink & blue palette.\nIncludes "quoted" text and café colors.'
        dialog.description.insert('1.0', description)
        dialog.version.set('1.2-beta')
        with patch('palette_ui.filedialog.asksaveasfilename') as save_as:
            dialog.submit()
            assert dialog.error.get() and not save_as.called
        dialog.version.set('2.3.4')
        with patch('palette_ui.filedialog.asksaveasfilename', return_value=''):
            dialog.submit()
        assert dialog.winfo_exists() and doc.mod_details == old_details
        assert dialog.description.get('1.0', 'end-1c') == description
        with patch('palette_ui.filedialog.asksaveasfilename', return_value=str(root / 'custom-mod.zip')):
            dialog.submit()
        assert not dialog.winfo_exists()
        with zipfile.ZipFile(root / 'custom-mod.zip') as archive:
            info = json.loads(archive.read('mod.json'))
            assert info['name'] == 'Candy Annie — test' and info['desc'] == description and info['version'] == '2.3.4'
            assert info['author'] == 'Palette Editor' and info['id'].startswith('paletteeditor.annie.1.')
            assert 'characters-foits.gfs/characters/annie.foit' in archive.namelist()
        assert np.array_equal(doc.colors, old_colors) and len(doc.undo_stack) == old_history
        editor.export('zip')
        assert editor.mod_dialog.name.get() == 'Candy Annie — test'
        editor.mod_dialog.name.set('Cancelled name')
        editor.mod_dialog.destroy()
        assert doc.mod_details['name'] == 'Candy Annie — test'
        from mod_info import validate_details
        for version in ('1', '-1.0', '1.2.3.4.5', '1.0-beta', '1.2147483648'):
            try:
                validate_details(dict(name='Test', desc='', version=version))
            except ValueError:
                pass
            else:
                raise AssertionError('Invalid Mod Manager version accepted')
        assert validate_details(dict(name='Test', desc='', version='1.2.3.4'))['version'] == '1.2.3.4'
        # Selecting and cancelling sprite previews never edits the palette/history.
        sprite_colors = doc.colors.copy()
        sprite_history = len(doc.undo_stack)
        editor.choose_sprite()
        browser = editor.sprite_browser
        browser.select(2)
        browser.use()
        assert editor.index() == doc.frame_indices[2]
        assert np.array_equal(doc.colors, sprite_colors) and len(doc.undo_stack) == sprite_history
        editor.choose_sprite()
        editor.sprite_browser.select(4)
        editor.sprite_browser.destroy()
        assert editor.index() == doc.frame_indices[2]
        # Exercise later pages and direct jumps with a larger synthetic catalog.
        from sprite_browser import SpriteBrowser
        chosen, rendered = [], []
        def thumbnail_frame(index, original):
            rendered.append((index, original))
            return Image.new('RGBA', (30, 50), (index * 7, 90, 160, 255))
        catalog = SimpleNamespace(frame_indices=list(range(27)), render=thumbnail_frame)
        browser = SpriteBrowser(editor, catalog, 13, chosen.append, original=True)
        window.after(300, window.quit)
        window.mainloop()
        assert browser.page == 1 and any(index == 12 and original for index, original in rendered)
        browser.jump.set('27')
        browser.go_to()
        assert browser.page == 2 and browser.selected == 26 and browser.next.instate(['disabled'])
        browser.jump.set('invalid')
        browser.go_to()
        assert browser.page == 2
        browser.change_page(-1)
        assert browser.page == 1
        browser.jump.set('27')
        browser.go_to()
        browser.choose(26)
        assert chosen == [26] and not browser.winfo_exists()
        window.update()
        editor.frame.set('1')
        editor.render()
        editor.hex.set('#123456')
        editor.alpha.set('37')
        editor.set_color()
        assert tuple(doc.colors[editor.row, editor.shade]) == (18, 52, 86, 37)
        editor.history(False)
        editor.history(True)
        editor.compare.set(True)
        editor.render()
        # Dragging previews before release/Apply, preserving alpha and history.
        from color_wheel import CENTER, INNER, OUTER, START, SQUARE
        editor.shade = 12  # This shade is used by material 1 in the fixture sprite.
        editor.refresh()
        baseline = doc.colors.copy()
        history_size = len(doc.undo_stack)
        before_preview = np.array(doc.render(0))
        editor.choose_color()
        picker = editor.picker
        assert picker is not None and not editor.compare.get()
        picker.press(SimpleNamespace(x=CENTER + (INNER + OUTER) / 2, y=CENTER))
        window.after(60, window.quit)
        window.mainloop()  # A queued drag updates the sprite without mouse release.
        assert picker.drag_mode == 'hue' and not picker.closed
        assert not np.array_equal(doc.colors, baseline)
        assert not np.array_equal(np.array(doc.render(0)), before_preview)
        assert np.array_equal(doc.colors[:, :, 3], baseline[:, :, 3])
        assert len(doc.undo_stack) == history_size
        picker.drag(SimpleNamespace(x=CENTER, y=CENTER - (INNER + OUTER) / 2))
        picker.flush()
        picker.release(SimpleNamespace(x=CENTER, y=CENTER - (INNER + OUTER) / 2))
        picker.finish(True)
        edited = doc.colors.copy()
        assert editor.picker is None and len(doc.undo_stack) == history_size + 1
        doc.undo()
        assert np.array_equal(doc.colors, baseline)
        doc.redo()
        assert np.array_equal(doc.colors, edited)
        # Cancel whole-material recoloring and preserve an existing redo branch.
        doc.undo()
        redo = [c.copy() for c in doc.redo_stack]
        editor.compare.set(True)
        editor.choose_color(True)
        picker = editor.picker
        assert picker.rgb() == tuple(int(c) for c in baseline[editor.row, editor.shade, :3])
        picker.hex.set('#204060')
        picker.apply_hex()
        picker.flush()
        assert tuple(doc.colors[editor.row, editor.shade, :3]) == (32, 64, 96)
        assert np.any(doc.colors[editor.row, :editor.shade, :3] != baseline[editor.row, :editor.shade, :3])
        picker.press(SimpleNamespace(x=START + SQUARE - 1, y=START))
        picker.flush()
        assert np.array_equal(doc.colors[:, :, 3], baseline[:, :, 3])
        picker.hex.set('#00FF00')
        picker.apply_hex()
        picker.flush()
        once = doc.colors.copy()
        picker.hex.set('#1133CC')
        picker.apply_hex()
        picker.flush()
        picker.hex.set('#00FF00')
        picker.apply_hex()
        picker.flush()
        assert np.array_equal(doc.colors, once), 'Repeated ramp previews drifted'
        picker.finish(False)
        assert np.array_equal(doc.colors, baseline)
        assert len(doc.redo_stack) == len(redo) and all(np.array_equal(a, b) for a, b in zip(doc.redo_stack, redo))
        assert editor.compare.get()
        # Black and neutral reference shades preserve an unchanged ramp exactly.
        from palette import ColorPreview
        for rgb in ((0, 0, 0), (90, 90, 90)):
            neutral = baseline.copy()
            neutral[editor.row, editor.shade, :3] = rgb
            doc.colors = neutral.copy()
            session = ColorPreview(doc, editor.row, editor.shade, True)
            session.preview(rgb)
            assert np.array_equal(doc.colors, neutral)
            session.preview((32, 64, 96))
            assert tuple(doc.colors[editor.row, editor.shade, :3]) == (32, 64, 96)
            session.finish(False)
        doc.colors = baseline.copy()
        # Pending drag callbacks cannot apply changes after Cancel.
        editor.choose_color()
        picker = editor.picker
        picker.hex.set('#abcdef')
        picker.apply_hex()
        picker.finish(False)
        window.update()
        assert np.array_equal(doc.colors, baseline)
        # Accepting without a change creates no history entry.
        history_size = len(doc.undo_stack)
        editor.choose_color()
        editor.picker.finish(True)
        assert len(doc.undo_stack) == history_size
        editor.choose_color()
        picker = editor.picker
        picker.hex.set('#oops')
        picker.finish(True)
        assert not picker.closed and editor.picker is picker
        picker.finish(False)
        with patch('palette_ui.messagebox.askyesno', return_value=False):
            assert not editor.confirm_discard()
        window.update_idletasks()
        editor.choose_color(True)
        picker = editor.picker
        picker.hex.set('#33aaff')
        picker.apply_hex()
        picker.flush()
        window.destroy()
        assert picker.closed and np.array_equal(doc.colors, baseline)
        # Archive bytes are unchanged even after all edits and exports.
        fresh = PaletteDocument(game, 'annie', 1)
        assert np.array_equal(fresh.colors, original)
    print('Palette tests passed: slot discovery/preview, Apply UI, manifest editing, exports, sprite selection, live wheel, alpha and history.')


if __name__ == '__main__':
    run()
