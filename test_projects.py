"""Project/recovery checks against synthetic game assets and real Tk controls."""
from copy import deepcopy
from pathlib import Path
import tempfile
import zipfile
from unittest.mock import patch
import numpy as np
from decoder import GFS
from game_palette import patch as patch_palette
from palette import PaletteDocument
from palette_project import (DraftStore, open_project, project_data,
                             read_json, validate_project)
from test_fixtures import fixture, make_gfs


def refused(action, text=None):
    try:
        action()
    except (ValueError, OSError) as exc:
        assert text is None or text in str(exc), str(exc)
    else:
        raise AssertionError('Unsafe or invalid project operation accepted')


def pump(window, predicate):
    """Poll the Tk worker queue with a bounded event loop, no file dialogs."""
    def check():
        if predicate():
            window.quit()
        else:
            window.after(20, check)
    timeout = window.after(5000, window.quit)
    check()
    window.mainloop()
    window.after_cancel(timeout)
    assert predicate(), 'Project load did not complete'


def run():
    with tempfile.TemporaryDirectory(prefix='project-tests-') as temporary:
        root = Path(temporary)
        game = fixture(root)
        doc = PaletteDocument(game, 'annie', 1)
        assert not doc.dirty and doc.project_path is None
        doc.set_color(1, 8, (240, 10, 80, 255))
        doc.mod_details = dict(name='Annie — café', desc='Line one\nLine two', version='2.3.4')
        requested = doc.colors.copy()
        project = root / 'annie.sgpalette'
        doc.save_project(project)
        assert not doc.dirty
        opening = open_project(project)
        assert not opening.source_changed
        reopened = opening.finish()
        assert not reopened.dirty and reopened.mod_details == doc.mod_details
        assert reopened.project_path == project and np.array_equal(reopened.colors, requested)
        assert reopened.undo_stack == []
        for kind in ('png', 'dds', 'zip'):
            reopened.mod_details['desc'] = kind
            reopened.export(root / ('export.' + kind), kind)
            assert reopened.dirty
        reopened.save_project(project)
        assert not reopened.dirty

        # Atomic replacement failure retains both the saved file and checkpoint.
        saved_bytes = project.read_bytes()
        reopened.set_color(2, 4, (10, 20, 30, 255))
        with patch('palette_project.os.replace', side_effect=OSError('simulated interruption')):
            refused(lambda: reopened.save_project(project), 'interruption')
        assert project.read_bytes() == saved_bytes and reopened.dirty
        assert not list(root.glob('.annie.sgpalette.*.tmp'))

        # Two editors cannot silently replace each other's project save.
        other = open_project(project).finish()
        other.mod_details['name'] = 'Newer work'
        other.save_project(project)
        newer_bytes = project.read_bytes()
        refused(lambda: reopened.save_project(project), 'changed')
        assert project.read_bytes() == newer_bytes
        reopened.save_project(root / 'separate.sgpalette')

        # Per-document drafts survive a process restart and never overwrite projects.
        store = DraftStore(root / 'Recovery')
        reopened.mod_details['desc'] = 'Recovery details'
        store.write(reopened)
        draft = store.path_for(reopened)
        previous_draft = draft.read_bytes()
        reopened.set_color(3, 1, (77, 88, 99, 255))
        with patch('palette_project.os.replace', side_effect=OSError('draft interruption')):
            refused(lambda: store.write(reopened), 'interruption')
        assert draft.read_bytes() == previous_draft
        store.write(reopened)
        restarted = DraftStore(store.directory)
        assert restarted.pending() == [draft]
        linked_project = reopened.project_path
        linked_project.write_bytes(newer_bytes)
        assert 'has changed or is missing' in restarted.recovery_note(draft)
        recovered = open_project(draft, recovered=True).finish()
        assert recovered.project_path is None and recovered.dirty
        assert recovered.mod_details['desc'] == 'Recovery details'
        assert np.array_equal(recovered.colors, reopened.colors)
        recovered.save_project(root / 'recovered.sgpalette')
        restarted.remove(recovered)
        assert linked_project.read_bytes() == newer_bytes and not draft.exists()
        store.write(reopened)
        fresh_doc = PaletteDocument(game, 'annie', 1)
        store.write(fresh_doc)
        assert len(store.pending()) == 2  # Concurrent sessions have distinct names.

        # Reject malformed projects before loading any game assets.
        data = project_data(doc)
        mutations = [lambda d: d.update(version=2), lambda d: d.update(character=[]),
                     lambda d: d.update(slot=True), lambda d: d['colors'][0][0].__setitem__(0, 256),
                     lambda d: d['colors'][0][0].__setitem__(0, -1),
                     lambda d: d['colors'][0][0].__setitem__(0, 1.5),
                     lambda d: d['colors'][0][0].__setitem__(0, True),
                     lambda d: d.update(colors=[[[False] * 4] * 16]),
                     lambda d: d.update(colors=[[[0] * 4]]),
                     lambda d: d['source'].update(dds_sha256='invalid'),
                     lambda d: d['mod_details'].update(version='bad')]
        for mutate in mutations:
            invalid = deepcopy(data)
            mutate(invalid)
            refused(lambda: validate_project(invalid))
        invalid_path = root / 'invalid.sgpalette'
        invalid_path.write_text('{truncated', encoding='utf-8')
        refused(lambda: open_project(invalid_path), 'invalid JSON')
        invalid_path.write_bytes(b' ' * (2 * 1024 * 1024 + 1))
        refused(lambda: read_json(invalid_path), 'too large')
        refused(lambda: doc.save_project(game / 'unsafe.sgpalette'), 'outside the game')

        # A relocated matching game is usable with an explicit folder override.
        moved_game = fixture(root / 'relocated')
        relocated = open_project(project, moved_game).finish()
        assert not relocated.dirty and relocated.source == moved_game / 'data01'

        # New unrelated palette slots and metadata are retained by ZIP preparation.
        foit_path = game / 'data01/characters-foits.gfs'
        sprite_path = game / 'data01/sprites.gfs'
        foit_archive, sprite_archive = foit_path.read_bytes(), sprite_path.read_bytes()
        second = PaletteDocument(game, 'annie', 2)
        second_colors = second.colors.copy()
        second_colors[2, :, :3] = (20, 120, 220)
        fresh_metadata, _ = patch_palette(second.metadata, 2, second.original, second_colors)
        make_gfs(foit_path, {'characters/annie.foit': fresh_metadata})
        doc.export(root / 'fresh.zip', 'zip')
        with zipfile.ZipFile(root / 'fresh.zip') as archive:
            metadata = archive.read('characters-foits.gfs/characters/annie.foit')
        expected, _ = patch_palette(fresh_metadata, 1, doc.original, doc.colors)
        assert metadata == expected and foit_path.read_bytes() != foit_archive
        assert sprite_path.read_bytes() == sprite_archive

        # Changed source reopening rebases edited shades and retains fresh others.
        new_colors = doc.original.copy()
        new_colors[2, :, :3] = (80, 90, 100)
        baseline = PaletteDocument(game, 'annie', 1)
        baseline.replace(new_colors)
        metadata, _ = patch_palette(fresh_metadata, 1, baseline.original, new_colors)
        make_gfs(foit_path, {'characters/annie.foit': metadata})
        make_gfs(sprite_path, {'sprites/annie_1p.dds': baseline.texture(),
                               'sprites/annie_2p.dds': second.dds})
        refused(lambda: doc.export(root / 'stale.zip', 'zip'), 'changed after loading')
        changed = open_project(project)
        assert changed.source_changed
        rebased = changed.finish()
        assert rebased.dirty and tuple(rebased.colors[1, 8]) == tuple(doc.colors[1, 8])
        assert np.array_equal(rebased.colors[2], new_colors[2])
        reloaded = open_project(project).finish(reapply=False)
        assert np.array_equal(reloaded.colors, new_colors) and reloaded.project_path is None and not reloaded.dirty
        rebased.save_project(root / 'reviewed.sgpalette')
        rebased.export(root / 'reviewed.zip', 'zip')
        # Target gameplay-only changes also refuse stale ZIP preparation.
        changed_gameplay, _ = patch_palette(metadata, 1, baseline.original, doc.colors)
        make_gfs(foit_path, {'characters/annie.foit': changed_gameplay})
        refused(lambda: rebased.export(root / 'stale-gameplay.zip', 'zip'), 'gameplay palette changed')
        foit_path.write_bytes(foit_archive)
        sprite_path.write_bytes(sprite_archive)

        # Actual project controls, asynchronous opening, save/discard/cancel and
        # recovery startup status use isolated local storage and synthetic assets.
        from palette_app import create_app
        window, editor = create_app(recovery_directory=root / 'UI-Recovery')
        window.withdraw()
        editor.doc = PaletteDocument(game, 'annie', 1)
        editor.refresh()
        editor.doc.set_color(1, 3, (120, 130, 140, 255))
        editor.edit_details()
        editor.mod_dialog.name.set('UI details')
        editor.mod_dialog.submit()
        editor.autosave()
        ui_draft = editor.drafts.path_for(editor.doc)
        assert ui_draft.is_file()
        ui_project = root / 'ui.sgpalette'
        with patch('palette_ui.filedialog.asksaveasfilename', return_value=str(ui_project)):
            assert editor.save_project()
        assert not editor.doc.dirty and not ui_draft.exists()
        editor.doc.set_color(2, 2, (44, 55, 66, 255))
        with patch('palette_ui.messagebox.askyesnocancel', return_value=None):
            assert not editor.confirm_discard()
        with patch('palette_ui.messagebox.askyesnocancel', return_value=True), \
                patch('palette_ui.filedialog.asksaveasfilename', return_value=''):
            editor.doc.project_path = None
            assert not editor.confirm_discard()
        editor.doc.project_path = ui_project
        with patch('palette_ui.messagebox.askyesnocancel', return_value=True):
            assert editor.confirm_discard() and not editor.doc.dirty
        editor.doc.set_color(2, 3, (66, 77, 88, 255))
        editor.autosave()
        with patch('palette_ui.messagebox.askyesnocancel', return_value=False):
            editor.open_project(ui_project)
        pump(window, lambda: not editor.loading)
        assert editor.doc.mod_details['name'] == 'UI details' and not editor.doc.dirty
        assert not ui_draft.exists()
        # Drafts capture committed edits, never temporary color-picker previews.
        editor.choose_color()
        editor.picker.on_change((200, 10, 20))
        editor.autosave()
        assert not editor.drafts.path_for(editor.doc).exists()
        editor.picker.finish(False)
        # Failed and cancelled loads retain current work and its recovery draft.
        editor.doc.set_color(1, 2, (10, 30, 50, 255))
        editor.autosave()
        retained = editor.doc
        with patch('palette_ui.messagebox.askyesnocancel', return_value=False), \
                patch('palette_ui.messagebox.showerror'), \
                patch('palette_ui.open_project', side_effect=ValueError('load failure')):
            editor.open_project(ui_project)
            pump(window, lambda: not editor.loading)
        assert editor.doc is retained and editor.drafts.path_for(retained).exists()
        assert editor.discarded_document is None
        editor.game.set(str(moved_game))
        with patch('palette_ui.messagebox.askyesnocancel', return_value=False):
            editor.open_project(ui_project, use_selected_source=True)
            pump(window, lambda: not editor.loading)
        assert editor.doc.source == moved_game / 'data01'
        editor.doc.set_color(1, 2, (10, 30, 50, 255))
        editor.autosave()
        retained = editor.doc
        # Cancelling the changed-source review also retains the outgoing draft.
        make_gfs(foit_path, {'characters/annie.foit': doc.metadata + b'new metadata record'})
        with patch('palette_ui.messagebox.askyesnocancel', side_effect=[False, None]):
            editor.open_project(ui_project)
            pump(window, lambda: not editor.loading)
        assert editor.doc is retained and editor.discarded_document is None
        assert editor.drafts.path_for(retained).exists()
        with patch('palette_ui.messagebox.askyesnocancel', side_effect=[False, True]):
            editor.open_project(ui_project)
            pump(window, lambda: not editor.loading)
        assert editor.doc is not retained and editor.doc.dirty
        assert not editor.drafts.path_for(retained).exists()
        editor.autosave()
        recover_path = editor.drafts.path_for(editor.doc)
        before_recovery = editor.doc.colors.copy()
        with patch('palette_ui.filedialog.askopenfilename', return_value=str(recover_path)), \
                patch('palette_ui.messagebox.askyesno', return_value=True), \
                patch('palette_ui.messagebox.askyesnocancel', return_value=False):
            editor.recover_draft()
            pump(window, lambda: not editor.loading)
        assert editor.doc.project_path is None and editor.doc.dirty
        assert np.array_equal(editor.doc.colors, before_recovery)
        window.geometry('900x720')
        window.update_idletasks()
        assert editor.winfo_reqheight() < 720
        retained = editor.doc
        foit_path.write_bytes(foit_archive)
        window.destroy()
        assert editor.drafts.path_for(retained).exists()
    print('Project tests passed: round trips, atomic writes, concurrent saves, recovery, source review, fresh exports and UI controls.')


if __name__ == '__main__':
    run()
