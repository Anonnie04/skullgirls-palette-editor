"""Left sprite / right palette workspace shared by the Workshop and launcher."""
import queue
import threading
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import numpy as np
from PIL import Image, ImageTk, ImageDraw
from decoder import NAMES, available_characters
from palette import PaletteDocument, ColorPreview, palette_slots
from color_wheel import ColorWheel
from sprite_browser import SpriteBrowser
from mod_details import ModDetailsDialog
from export_options import ImageExportDialog, export_notes
from palette_browser import PaletteCatalog
from direct_apply import apply_palette
from palette_project import DraftStore, ProjectOpening, open_project, read_json, validate_project

BG = '#181416'
PANEL = '#292124'
TEXT = '#f5ead5'
MUTED = '#c2b39e'
ACCENT = '#e6bc68'


class PaletteEditor(tk.Frame):
    def __init__(self, parent, game, recovery_directory=None):
        super().__init__(parent, bg=BG, padx=12, pady=12)
        self.game = game
        self.doc = None
        self.row, self.shade = 1, 15
        self.loading = False
        self.applying = False
        self.picker = None
        self.sprite_browser = None
        self.mod_dialog = None
        self.events = queue.Queue()
        base = Path(sys.executable if getattr(sys, 'frozen', False) else __file__).resolve().parent
        self.drafts = DraftStore(recovery_directory or base / 'Recovery')
        self.discarded_document = None
        self.draft_error = None
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        bar = tk.Frame(self, bg=BG)
        bar.grid(row=0, column=0, sticky='ew', pady=(0, 10))
        self.character = tk.StringVar(value='Filia')
        self.slot = tk.StringVar(value='1')
        self.characters = ttk.Combobox(bar, textvariable=self.character, values=list(NAMES.values()), state='readonly', width=18)
        self.characters.pack(side='left')
        self.characters.bind('<<ComboboxSelected>>', self.change_character)
        tk.Label(bar, text='  Palette slot ', bg=BG, fg=MUTED).pack(side='left')
        self.slots = ttk.Combobox(bar, textvariable=self.slot, values=['1'], state='readonly', width=5)
        self.slots.pack(side='left')
        self.slots.bind('<<ComboboxSelected>>', lambda event: self.load())
        self.palette_browser_button = ttk.Button(bar, text='Palettes…', command=self.choose_palette, state='disabled')
        self.palette_browser_button.pack(side='left', padx=(6, 0))
        self.palette_count = tk.StringVar()
        tk.Label(bar, textvariable=self.palette_count, bg=BG, fg=MUTED).pack(side='left', padx=6)
        self.load_button = ttk.Button(bar, text='Load from game', command=self.load)
        self.load_button.pack(side='left', padx=8)
        ttk.Button(bar, text='Scan game', command=self.scan).pack(side='left')
        projects = tk.Frame(self, bg=BG)
        projects.grid(row=1, column=0, sticky='ew', pady=(0, 8))
        open_button = ttk.Menubutton(projects, text='Open project…')
        open_menu = tk.Menu(open_button, tearoff=False)
        open_menu.add_command(label='Open project…', command=self.open_project)
        open_menu.add_command(label='Open project using selected game folder…',
                              command=lambda: self.open_project(use_selected_source=True))
        open_button.configure(menu=open_menu)
        open_button.pack(side='left')
        self.save_project_button = ttk.Button(projects, text='Save project', command=self.save_project)
        self.save_project_button.pack(side='left', padx=6)
        self.save_as_button = ttk.Button(projects, text='Save as…', command=lambda: self.save_project(True))
        self.save_as_button.pack(side='left')
        self.details_button = ttk.Button(projects, text='Export details…', command=self.edit_details)
        self.details_button.pack(side='left', padx=6)
        recovery_button = ttk.Menubutton(projects, text='Recover draft…')
        recovery_menu = tk.Menu(recovery_button, tearoff=False)
        recovery_menu.add_command(label='Recover draft…', command=self.recover_draft)
        recovery_menu.add_command(label='Recover draft using selected game folder…',
                                  command=lambda: self.recover_draft(use_selected_source=True))
        recovery_button.configure(menu=recovery_menu)
        recovery_button.pack(side='left')
        body = tk.PanedWindow(self, orient='horizontal', bg=BG, sashwidth=10, borderwidth=0)
        body.grid(row=2, column=0, sticky='nsew')
        left, right = tk.Frame(body, bg=BG), tk.Frame(body, bg=BG)
        body.add(left, minsize=240, stretch='always')
        body.add(right, minsize=410, width=440, stretch='never')
        left.columnconfigure(0, weight=1)
        left.rowconfigure(2, weight=1)
        preview_header = tk.Frame(left, bg=BG)
        preview_header.grid(row=0, column=0, sticky='ew')
        tk.Label(preview_header, text='SPRITE PREVIEW', bg=BG, fg=ACCENT, font=('Segoe UI', 11, 'bold')).pack(side='left')
        self.choose_sprite_button = ttk.Button(preview_header, text='Choose sprite…', command=self.choose_sprite, state='disabled')
        self.choose_sprite_button.pack(side='right')
        controls = tk.Frame(left, bg=BG)
        controls.grid(row=1, column=0, sticky='ew', pady=8)
        ttk.Button(controls, text='‹', width=3, command=lambda: self.step(-1)).pack(side='left')
        self.frame = tk.StringVar(value='1')
        self.frame_box = ttk.Spinbox(controls, from_=1, to=1, width=6, textvariable=self.frame, command=self.render)
        self.frame_box.pack(side='left', padx=4)
        self.frame_box.bind('<Return>', self.render)
        self.frame_box.bind('<FocusOut>', self.render)
        ttk.Button(controls, text='›', width=3, command=lambda: self.step(1)).pack(side='left')
        self.compare = tk.BooleanVar()
        ttk.Checkbutton(controls, text='Original', variable=self.compare, command=self.render).pack(side='left', padx=8)
        self.preview_mode = tk.StringVar(value='Requested')
        modes = ttk.Combobox(controls, textvariable=self.preview_mode,
                             values=('Requested', 'Stored', 'Difference'), state='readonly', width=11)
        modes.pack(side='left')
        modes.bind('<<ComboboxSelected>>', self.change_preview_mode)
        self.canvas = tk.Canvas(left, bg=PANEL, highlightthickness=0, width=280, height=260)
        self.canvas.grid(row=2, column=0, sticky='nsew')
        self.canvas.bind('<Configure>', self.render)
        self.canvas.bind('<Button-1>', self.pick_sprite)
        self.frame_info = tk.StringVar(value='Load a character to preview its sprites.')
        tk.Label(left, textvariable=self.frame_info, bg=BG, fg=MUTED, wraplength=350, justify='left').grid(row=3, column=0, sticky='w', pady=8)
        tk.Label(left, text='Click the sprite to select its material and shade.\nStored previews palette storage; stage lighting can differ.', bg=BG, fg=MUTED, justify='left').grid(row=4, column=0, sticky='w')
        self.storage_info = tk.StringVar()
        tk.Label(left, textvariable=self.storage_info, bg=BG, fg=MUTED, wraplength=350,
                 justify='left').grid(row=5, column=0, sticky='w', pady=(8, 0))
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)
        tk.Label(right, text='PALETTE  /  16 SHADES PER MATERIAL', bg=BG, fg=ACCENT, font=('Segoe UI', 10, 'bold')).grid(row=0, column=0, sticky='w', pady=(0, 8))
        grid = tk.Frame(right, bg=BG)
        grid.grid(row=1, column=0, sticky='nsew')
        grid.columnconfigure(0, weight=1)
        grid.rowconfigure(0, weight=1)
        self.swatches = tk.Canvas(grid, bg=PANEL, highlightthickness=0, height=110, width=390)
        self.swatches.grid(row=0, column=0, sticky='nsew')
        scroll = ttk.Scrollbar(grid, orient='vertical', command=self.swatches.yview)
        scroll.grid(row=0, column=1, sticky='ns')
        self.swatches.configure(yscrollcommand=scroll.set)
        self.swatches.bind('<Button-1>', self.pick_swatch)
        self.swatches.bind('<MouseWheel>', lambda e: self.swatches.yview_scroll(-int(e.delta / 120), 'units'))
        self.selection = tk.StringVar(value='Select a color')
        tk.Label(right, textvariable=self.selection, bg=BG, fg=TEXT, anchor='w').grid(row=2, column=0, sticky='ew', pady=(10, 6))
        edit = tk.Frame(right, bg=BG)
        edit.grid(row=3, column=0, sticky='ew')
        self.hex = tk.StringVar(value='#000000')
        self.alpha = tk.StringVar(value='255')
        ttk.Entry(edit, textvariable=self.hex, width=10).pack(side='left')
        tk.Label(edit, text='  Alpha byte ', bg=BG, fg=MUTED).pack(side='left')
        ttk.Entry(edit, textvariable=self.alpha, width=4).pack(side='left')
        ttk.Button(edit, text='Set', command=self.set_color).pack(side='left', padx=6)
        tk.Label(right, text='Alpha is game encoded. Color pickers preserve it.', bg=BG, fg=MUTED, font=('Segoe UI', 9)).grid(row=4, column=0, sticky='w', pady=5)
        actions = tk.Frame(right, bg=BG)
        actions.grid(row=5, column=0, sticky='ew', pady=5)
        ttk.Button(actions, text='Pick color…', command=self.choose_color).pack(side='left')
        ttk.Button(actions, text='Recolor material…', command=lambda: self.choose_color(True)).pack(side='left', padx=6)
        history = tk.Frame(right, bg=BG)
        history.grid(row=6, column=0, sticky='ew', pady=5)
        self.undo_button = ttk.Button(history, text='Undo', command=lambda: self.history(False))
        self.undo_button.pack(side='left')
        self.redo_button = ttk.Button(history, text='Redo', command=lambda: self.history(True))
        self.redo_button.pack(side='left', padx=6)
        ttk.Button(history, text='Reset material', command=self.reset_material).pack(side='left')
        files = tk.Frame(right, bg=BG)
        files.grid(row=7, column=0, sticky='ew', pady=(8, 0))
        ttk.Button(files, text='Import PNG / DDS…', command=self.import_image).pack(side='left')
        ttk.Button(files, text='Export PNG / DDS…', command=self.save_image).pack(side='left', padx=6)
        ttk.Button(right, text='Export mod ZIP…', style='Accent.TButton', command=lambda: self.export('zip')).grid(row=8, column=0, sticky='ew', pady=(8, 0))
        self.apply_button = ttk.Button(right, text='Apply palette to game…', style='Accent.TButton', command=self.open_apply, state='disabled')
        self.apply_button.grid(row=9, column=0, sticky='ew', pady=(8, 0))
        self.status = tk.StringVar(value='Choose the game folder above, then load a character and palette slot.')
        tk.Label(self, textvariable=self.status, bg=BG, fg=MUTED, wraplength=900, justify='left').grid(row=3, column=0, sticky='ew', pady=(10, 0))
        self.refresh()
        self.poll_id = self.after(100, self.poll)
        self.bind('<Destroy>', self.cleanup)
        self.auto_scan_id = self.after(250, self.auto_scan)
        self.draft_id = self.after(1500, self.draft_tick)

    def cleanup(self, event):
        if event.widget is self:
            self.after_cancel(self.poll_id)
            if self.auto_scan_id is not None:
                self.after_cancel(self.auto_scan_id)
            self.after_cancel(self.draft_id)
            if self.doc is self.discarded_document:
                self.remove_draft(self.doc)
            elif self.doc and not self.applying:
                self.autosave()

    def confirm_discard(self):
        if self.loading and not self.applying:
            self.status.set('Wait for the palette or project to finish loading.')
            return False
        self.discarded_document = None
        if self.applying:
            self.status.set('Applying palette. Keep the editor open until verification finishes.')
            return False
        if self.mod_dialog and self.mod_dialog.winfo_exists():
            self.mod_dialog.lift()
            self.mod_dialog.focus_set()
            return False
        if self.picker:
            self.picker.lift()
            self.picker.focus_set()
            return False
        if not self.doc or not self.doc.dirty:
            return True
        choice = messagebox.askyesnocancel('Unsaved project',
                                          'Save your editable palette project before continuing?\n'
                                          'Yes: save project. No: discard these edits. Cancel: keep editing.', parent=self)
        if choice is None:
            return False
        if choice:
            return self.save_project()
        self.discarded_document = self.doc
        return True

    def remove_draft(self, document):
        if document is None:
            return
        try:
            self.drafts.remove(document)
        except OSError as exc:
            self.status.set(f'Could not remove the recovery draft: {exc}')

    def autosave(self):
        if not self.doc or self.picker or self.loading:
            return
        try:
            if self.doc.dirty:
                self.drafts.write(self.doc)
            else:
                self.drafts.remove(self.doc)
            self.draft_error = None
        except (OSError, ValueError) as exc:
            if str(exc) != self.draft_error:
                self.status.set(f'Draft recovery could not be saved: {exc}. Use Save project to keep your work.')
                self.draft_error = str(exc)

    def draft_tick(self):
        self.autosave()
        self.draft_id = self.after(1500, self.draft_tick)

    def project_action_available(self):
        return not self.loading and not self.picker and not (self.mod_dialog and self.mod_dialog.winfo_exists())

    def save_project(self, save_as=False):
        if not self.doc or not self.project_action_available():
            return False
        path = self.doc.project_path if not save_as else None
        if path is None:
            path = filedialog.asksaveasfilename(parent=self, title='Save editable palette project',
                                               initialfile=f'{self.doc.character}_{self.doc.slot}p.sgpalette',
                                               defaultextension='.sgpalette', filetypes=[('Palette project', '*.sgpalette')])
        if not path:
            return False
        try:
            self.doc.save_project(path)
            self.remove_draft(self.doc)
            self.discarded_document = None
            self.status.set(f'Project saved: {path}')
            self.refresh()
            return True
        except (OSError, ValueError) as exc:
            self.error(exc)
            return False

    def edit_details(self):
        if not self.doc or not self.project_action_available():
            return
        def keep(details):
            self.doc.mod_details = details.copy()
            self.refresh()
            return True
        self.mod_dialog = ModDetailsDialog(self, self.doc.mod_details, keep,
                                           save_label='Keep details',
                                           note='Saved with your editable project and used for mod ZIP export.')

    def open_project(self, path=None, recovered=False, use_selected_source=False):
        if not self.project_action_available():
            return
        if path is None:
            path = filedialog.askopenfilename(parent=self, title='Open editable palette project',
                                              filetypes=[('Palette project', '*.sgpalette')])
        if not path:
            return
        try:
            data, _ = read_json(path)
            if recovered:
                data = data.get('document') if isinstance(data, dict) else None
            validate_project(data)
            game = self.game.get().strip() if use_selected_source else None
            if use_selected_source and not game:
                raise ValueError('Choose the matching game folder above before opening the project with that source.')
            if game is None and not (Path(data['source']['folder']) / 'sprites.gfs').is_file():
                game = filedialog.askdirectory(parent=self, title='Locate the game folder for this project')
                if not game:
                    return
            if self.confirm_discard():
                self.start_load(lambda: open_project(path, game, recovered))
        except (OSError, ValueError) as exc:
            self.error(exc)

    def recover_draft(self, use_selected_source=False):
        if not self.project_action_available():
            return
        try:
            pending = self.drafts.pending()
            if not pending:
                self.status.set('No recovery drafts found.')
                return
            path = filedialog.askopenfilename(parent=self, title='Recover a palette draft',
                                              initialdir=str(self.drafts.directory), initialfile=pending[0].name,
                                              filetypes=[('Palette recovery draft', '*.sgdraft')])
            if path and messagebox.askyesno('Recover draft', self.drafts.recovery_note(path), parent=self):
                self.open_project(path, recovered=True, use_selected_source=use_selected_source)
        except (OSError, ValueError) as exc:
            self.error(exc)

    def key(self):
        return next(k for k, name in NAMES.items() if name == self.character.get())

    def scan(self):
        if self.loading:
            return
        try:
            names = available_characters(self.game.get())
            if not names:
                raise ValueError('No characters with DDS palettes were found. Legacy embedded palette builds are unsupported; choose a DDS-based game build.')
            self.characters['values'] = [NAMES[n] for n in names]
            if self.character.get() not in self.characters['values']:
                self.character.set(NAMES[names[0]])
            self.scan_slots()
        except Exception as exc:
            self.error(exc)

    def auto_scan(self):
        self.auto_scan_id = None
        if self.doc is None and not self.loading:
            self.scan_slots(silent=True)
        try:
            count = len(self.drafts.pending())
            if count:
                self.status.set(f'{count} recovery draft(s) available. Use Recover draft to review them.')
        except OSError as exc:
            self.status.set(f'Cannot check recovery drafts: {exc}')

    def change_character(self, event=None):
        if self.scan_slots():
            self.load()

    def scan_slots(self, event=None, silent=False):
        if self.loading:
            return False
        try:
            slots = palette_slots(self.game.get(), self.key())
            self.slots['values'] = [str(slot) for slot in slots]
            if self.slot.get() not in self.slots['values']:
                self.slot.set(str(slots[0]) if slots else '')
            self.palette_count.set(f'{len(slots)} palettes')
            self.palette_browser_button.state(['!disabled'] if self.doc and self.doc.character == self.key() else ['disabled'])
            return bool(slots)
        except Exception as exc:
            if not silent:
                self.error(exc)
            return False

    def choose_palette(self):
        if not self.doc or self.loading or self.picker:
            return
        try:
            catalog = PaletteCatalog(self.doc, self.index())
            def choose(slot):
                if slot != self.doc.slot:
                    self.character.set(NAMES[self.doc.character])
                    self.slot.set(str(slot))
                    self.after_idle(self.load)
            self.sprite_browser = SpriteBrowser(self, catalog, self.doc.slot, choose, palettes=True)
        except Exception as exc:
            self.error(exc)

    def load(self):
        if self.loading or not self.confirm_discard():
            if self.doc:
                self.character.set(NAMES[self.doc.character])
                self.slot.set(str(self.doc.slot))
                self.scan_slots(silent=True)
            return
        try:
            game, character, slot = self.game.get(), self.key(), int(self.slot.get())
        except Exception as exc:
            self.discarded_document = None
            self.error(exc)
            return
        self.start_load(lambda: PaletteDocument(game, character, slot))

    def start_load(self, factory):
        self.loading = True
        self.load_button.state(['disabled'])
        self.apply_button.state(['disabled'])
        self.status.set('Loading palette and sprite frames…')
        def work():
            try:
                self.events.put((True, factory()))
            except Exception as exc:
                self.events.put((False, exc))
        threading.Thread(target=work, daemon=True).start()

    def poll(self):
        try:
            event = self.events.get_nowait()
        except queue.Empty:
            pass
        else:
            if len(event) == 3:
                _, success, result = event
                self.applying = self.loading = False
                self.load_button.state(['!disabled'])
                self.character.set(NAMES[self.doc.character])
                self.slot.set(str(self.doc.slot))
                if success:
                    self.status.set(f'Palette {self.doc.slot} applied and verified. Backups: {result["backups"]}')
                else:
                    self.error(result)
                self.refresh()
                self.poll_id = self.after(100, self.poll)
                return
            success, result = event
            self.loading = False
            self.load_button.state(['!disabled'])
            if success:
                opening = result if isinstance(result, ProjectOpening) else None
                if opening:
                    choice = True
                    if opening.source_changed:
                        choice = messagebox.askyesnocancel('Project source changed',
                            'The game palette or character metadata changed since this project was saved.\n\n'
                            'Yes: reapply only your edited shades to the current source for review.\n'
                            'No: reload the current game palette without project edits.\n'
                            'Cancel: keep your current work.\n\n'
                            'Save the reviewed result as a project before exporting.', parent=self)
                    if choice is None:
                        self.discarded_document = None
                        self.status.set('Project opening cancelled. Your current work is unchanged.')
                        self.refresh()
                        self.poll_id = self.after(100, self.poll)
                        return
                    result = opening.finish(choice)
                self.remove_draft(self.doc)
                self.discarded_document = None
                self.doc = result
                if opening:
                    self.game.set(str(result.source))
                self.character.set(NAMES[result.character])
                self.slot.set(str(result.slot))
                self.choose_sprite_button.state(['!disabled'])
                self.palette_browser_button.state(['!disabled'])
                self.scan_slots(silent=True)
                representative = next((i for i, index in enumerate(result.frame_indices)
                                       if sum(m['used'] for k, m in result.frames[index]['images'].items() if k in (0, 1)) > 32), 0)
                self.frame.set(str(representative + 1))
                self.compare.set(False)
                self.preview_mode.set('Requested')
                self.row, self.shade = min(1, len(result.colors) - 1), 15
                self.frame_box.configure(to=len(result.frame_indices))
                self.status.set(('Recovered as an unsaved copy. Save project as to keep it.' if opening and opening.recovered else
                                 'Source changed: review the current palette and your edits, then save project.' if opening and opening.source_changed else
                                 f'Project opened: {result.project_path}' if result.project_path else
                                 f'{NAMES[result.character]} · palette {result.slot} · {len(result.colors)} materials. Save a project to resume editing later.'))
                self.refresh()
            else:
                self.discarded_document = None
                self.error(result)
                self.refresh()
        self.poll_id = self.after(100, self.poll)

    def index(self):
        position = max(1, min(int(self.frame.get()), len(self.doc.frame_indices)))
        self.frame.set(str(position))
        return self.doc.frame_indices[position - 1]

    def step(self, delta):
        if self.doc:
            try:
                self.frame.set(str((int(self.frame.get()) - 1 + delta) % len(self.doc.frame_indices) + 1))
            except ValueError:
                self.frame.set('1')
            self.render()

    def choose_sprite(self):
        if not self.doc or self.loading or self.picker:
            return
        if self.sprite_browser and self.sprite_browser.winfo_exists():
            self.sprite_browser.lift()
            return
        try:
            index = self.index()
        except ValueError:
            self.frame.set('1')
            index = self.index()
        def select(index):
            self.frame.set(str(self.doc.frame_indices.index(index) + 1))
            self.render()
        self.sprite_browser = SpriteBrowser(self, self.doc, index, select, self.compare.get())

    def change_preview_mode(self, event=None):
        self.compare.set(False)
        self.refresh()

    def render(self, event=None):
        self.canvas.delete('all')
        self.transform = None
        if not self.doc:
            self.canvas.create_text(max(140, self.canvas.winfo_width() // 2), max(100, self.canvas.winfo_height() // 2), text='Load a palette to begin', fill=MUTED)
            return
        try:
            index = self.index()
            mode = 'Original' if self.compare.get() else self.preview_mode.get()
            image = self.doc.render(index, self.compare.get())
            if mode in ('Stored', 'Difference'):
                stored, _ = self.doc.storage_preview()
                stored_image = self.doc.render(index, palette=stored)
                if mode == 'Stored':
                    image = stored_image
                else:
                    # Opaque grayscale also reveals encoded-alpha/render differences.
                    delta = np.abs(np.array(image).astype(int) - np.array(stored_image).astype(int))
                    intensity = delta.max(axis=2).astype(np.uint8)
                    image = Image.fromarray(intensity).convert('RGBA')
            w, h = max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())
            scale = min((w - 24) / image.width, (h - 24) / image.height, 4)
            scale = max(.01, scale)
            size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
            image = image.resize(size, Image.Resampling.NEAREST)
            board = Image.new('RGBA', size, '#30292e')
            draw = ImageDraw.Draw(board)
            for y in range(0, size[1], 16):
                for x in range(0, size[0], 16):
                    if (x // 16 + y // 16) % 2:
                        draw.rectangle((x, y, x + 15, y + 15), fill='#3c343a')
            board.alpha_composite(image)
            self.photo = ImageTk.PhotoImage(board, master=self)
            ox, oy = (w - size[0]) // 2, (h - size[1]) // 2
            self.canvas.create_image(ox, oy, anchor='nw', image=self.photo)
            raw_size = (max(a.shape[1] for a in self.doc.layers(index)), max(a.shape[0] for a in self.doc.layers(index)))
            self.transform = (ox, oy, size[0] / raw_size[0], size[1] / raw_size[1], index)
            self.frame_info.set(f'{mode} · {NAMES[self.doc.character]} {self.doc.slot}p · frame {index} · {self.frame.get()} / {len(self.doc.frame_indices)}')
        except Exception as exc:
            self.frame_info.set(f'Cannot preview frame: {exc}')

    def refresh(self):
        for button in (self.save_project_button, self.save_as_button, self.details_button):
            button.state(['!disabled'] if self.doc and not self.loading else ['disabled'])
        self.apply_button.state(['!disabled'] if self.doc and not self.loading else ['disabled'])
        self.swatches.delete('all')
        self.undo_button.state(['!disabled'] if self.doc and self.doc.undo_stack else ['disabled'])
        self.redo_button.state(['!disabled'] if self.doc and self.doc.redo_stack else ['disabled'])
        if self.doc:
            palette = self.doc.colors
            errors = None
            try:
                stored, difference = self.doc.storage_preview()
                errors = difference.max(axis=(1, 2))
                worst = sorted((row for row, error in enumerate(errors) if error),
                               key=lambda row: (-int(errors[row]), row))[:3]
                if worst:
                    self.storage_info.set('Largest storage differences (RGBA, 0–255): ' +
                                          ', '.join(f'{row:03}: {errors[row]}' for row in worst) +
                                          '. Highlighted rows differ. Recoloring a whole material usually fits more closely. '
                                          'Difference: black = exact; brighter = larger error.')
                else:
                    self.storage_info.set('Exact storage fit: requested and stored colors match. '
                                          'Difference: black = exact; brighter = larger error.')
                if self.preview_mode.get() == 'Stored':
                    palette = stored
                elif self.preview_mode.get() == 'Difference':
                    palette = np.repeat(difference.max(axis=2)[:, :, None], 4, axis=2)
            except ValueError as exc:
                self.storage_info.set(f'Storage preview unavailable: {exc} PNG/DDS editing and export remain available.')
            for row, ramp in enumerate(palette):
                y = row * 23 + 4
                differs = errors is not None and errors[row] > 0
                self.swatches.create_text(27, y + 10, text=f'{row:03}', fill=ACCENT if row == self.row or differs else MUTED, anchor='e')
                if differs:
                    self.swatches.create_rectangle(30, y, 33, y + 20, fill=ACCENT, outline='')
                for shade, color in enumerate(ramp):
                    x = 36 + shade * 21
                    self.swatches.create_rectangle(x, y, x + 20, y + 20, fill='#%02x%02x%02x' % tuple(color[:3]), outline=PANEL)
                    if row == self.row and shade == self.shade:
                        self.swatches.create_rectangle(x - 1, y - 1, x + 21, y + 21, outline=ACCENT, width=2)
            self.swatches.configure(scrollregion=(0, 0, 380, len(self.doc.colors) * 23 + 8))
            color = self.doc.colors[self.row, self.shade]
            self.hex.set('#%02x%02x%02x' % tuple(color[:3]))
            self.alpha.set(str(color[3]))
            self.selection.set(f'Material {self.row:03} · shade {self.shade + 1} / 16' + ('  •  Unsaved project' if self.doc.dirty else ''))
        self.render()

    def pick_swatch(self, event):
        if self.doc and not self.loading:
            row, shade = int((self.swatches.canvasy(event.y) - 4) // 23), int((event.x - 36) // 21)
            if 0 <= row < len(self.doc.colors) and 0 <= shade < 16:
                self.row, self.shade = row, shade
                self.refresh()

    def pick_sprite(self, event):
        if self.doc and self.transform and not self.loading:
            ox, oy, sx, sy, index = self.transform
            x, y = (event.x - ox) / sx, (event.y - oy) / sy
            if x < 0 or y < 0:
                return
            selected = self.doc.sample(index, int(x), int(y))
            if selected:
                self.row, self.shade = selected
                self.swatches.yview_moveto(max(0, (self.row * 23 - 60) / (len(self.doc.colors) * 23 + 8)))
                self.refresh()

    def set_color(self):
        if not self.doc or self.loading:
            return
        try:
            text = self.hex.get().strip().lstrip('#')
            if len(text) != 6:
                raise ValueError('Enter a six-digit hex color such as #E6BC68.')
            rgba = [int(text[i:i + 2], 16) for i in (0, 2, 4)] + [int(self.alpha.get())]
            self.doc.set_color(self.row, self.shade, rgba)
            self.refresh()
        except Exception as exc:
            self.error(exc)

    def choose_color(self, ramp=False):
        if not self.doc or self.loading:
            return
        if self.picker:
            self.picker.lift()
            return
        session = ColorPreview(self.doc, self.row, self.shade, ramp)
        rgb = tuple(int(c) for c in self.doc.colors[self.row, self.shade, :3])
        # Show edits even if the user was comparing the original before opening.
        comparing = self.compare.get()
        preview_mode = self.preview_mode.get()
        self.compare.set(False)
        self.preview_mode.set('Requested')
        self.refresh()
        def change(color):
            session.preview(color)
            self.refresh()
        def finish(commit):
            session.finish(commit)
            self.picker = None
            if not commit:
                self.compare.set(comparing)
                self.preview_mode.set(preview_mode)
            if self.canvas.winfo_exists() and self.swatches.winfo_exists():
                self.refresh()
        self.picker = ColorWheel(self, rgb, change, finish,
                                 f'Material {self.row:03} · shade {self.shade + 1}' + (' reference' if ramp else ''))

    def history(self, redo):
        if self.doc and not self.loading:
            (self.doc.redo if redo else self.doc.undo)()
            self.refresh()

    def reset_material(self):
        if self.doc and not self.loading:
            colors = self.doc.colors.copy()
            colors[self.row] = self.doc.original[self.row]
            self.doc.replace(colors)
            self.refresh()

    def import_image(self):
        if not self.doc or self.loading:
            return
        path = filedialog.askopenfilename(parent=self, title='Import palette image', filetypes=[('Palette images', '*.png *.dds')])
        if path:
            try:
                self.doc.import_image(path)
                self.refresh()
            except Exception as exc:
                self.error(exc)

    def save_image(self):
        self.export('image')

    def open_apply(self):
        if not self.doc or self.loading:
            return
        if self.mod_dialog and self.mod_dialog.winfo_exists():
            self.mod_dialog.lift()
            return
        note = (f'{NAMES[self.doc.character]} · palette {self.doc.slot}\n{self.doc.source}\n'
                'Close Skullgirls first. Applies enabled mods and keeps verified backups.')
        self.mod_dialog = ModDetailsDialog(self, self.doc.mod_details, self.start_apply, apply_to=note)

    def start_apply(self, details):
        base = Path(sys.executable if getattr(sys, 'frozen', False) else __file__).resolve().parent
        manager = base.parent / 'Skullgirls Mod Manager'
        if not (manager / 'Mods').is_dir() or not (manager / 'Data').is_dir():
            selected = filedialog.askdirectory(parent=self.mod_dialog, title='Choose Skullgirls Mod Manager folder')
            if not selected:
                return False
            manager = Path(selected)
        self.loading = self.applying = True
        self.load_button.state(['disabled'])
        self.apply_button.state(['disabled'])
        self.status.set('Preparing and applying palette through Mod Manager. Keep the editor open…')
        document = self.doc
        document.mod_details = details.copy()
        try:
            self.drafts.write(document)
        except (OSError, ValueError) as exc:
            self.status.set(f'Applying palette; recovery draft could not be saved: {exc}. Keep the editor open…')
        def work():
            try:
                result = apply_palette(document, details, manager, base / 'Direct Apply')
                self.events.put(('apply', True, result))
            except Exception as exc:
                self.events.put(('apply', False, exc))
        threading.Thread(target=work, daemon=True).start()
        return True

    def export(self, kind):
        if not self.doc or self.loading:
            return
        if kind == 'zip':
            if self.mod_dialog and self.mod_dialog.winfo_exists():
                self.mod_dialog.lift()
                return
            _, note, issue = export_notes(self.doc, 'zip')
            self.mod_dialog = ModDetailsDialog(self, self.doc.mod_details,
                                               lambda details: self.save_export('zip', details, self.mod_dialog),
                                               note=note, export_error=issue, save_label='Export ZIP…')
            return
        if kind == 'image':
            if self.mod_dialog and self.mod_dialog.winfo_exists():
                self.mod_dialog.lift()
                return
            self.mod_dialog = ImageExportDialog(self, self.doc,
                                                lambda fmt, parent: self.save_export(fmt, parent=parent))
            return
        self.save_export(kind)

    def save_export(self, kind, details=None, parent=None):
        parent = parent or self
        types = {'zip': [('Mod ZIP', '*.zip')], 'png': [('Palette PNG', '*.png')], 'dds': [('Palette DDS', '*.dds')]}
        extension = '.' + kind
        path = filedialog.asksaveasfilename(parent=parent, title=f'Export {kind.upper()}', initialfile=f'{self.doc.character}_{self.doc.slot}p{extension}', defaultextension=extension, filetypes=types[kind])
        if path:
            try:
                fmt = Path(path).suffix.lower().lstrip('.')
                if fmt != kind:
                    raise ValueError(f'This export is {kind.upper()}. Use the .{kind} extension, or select another export format.')
                self.doc.export(path, fmt, details)
                self.status.set(f'Exported {path}. Use Save project to save editable work.')
                self.refresh()
                return True
            except Exception as exc:
                self.status.set(str(exc))
                messagebox.showerror('Palette editor', str(exc), parent=parent)
        return False

    def error(self, exc):
        self.status.set(str(exc))
        messagebox.showerror('Palette editor', str(exc), parent=self)
