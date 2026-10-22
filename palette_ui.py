"""Left sprite / right palette workspace shared by the Workshop and launcher."""
import queue
import threading
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from PIL import Image, ImageTk, ImageDraw
from decoder import NAMES, available_characters
from palette import PaletteDocument, ColorPreview, palette_slots
from color_wheel import ColorWheel
from sprite_browser import SpriteBrowser
from mod_details import ModDetailsDialog
from palette_browser import PaletteCatalog
from direct_apply import apply_palette

BG = '#181416'
PANEL = '#292124'
TEXT = '#f5ead5'
MUTED = '#c2b39e'
ACCENT = '#e6bc68'


class PaletteEditor(tk.Frame):
    def __init__(self, parent, game):
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
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
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
        body = tk.PanedWindow(self, orient='horizontal', bg=BG, sashwidth=10, borderwidth=0)
        body.grid(row=1, column=0, sticky='nsew')
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
        self.canvas = tk.Canvas(left, bg=PANEL, highlightthickness=0, width=280, height=260)
        self.canvas.grid(row=2, column=0, sticky='nsew')
        self.canvas.bind('<Configure>', self.render)
        self.canvas.bind('<Button-1>', self.pick_sprite)
        self.frame_info = tk.StringVar(value='Load a character to preview its sprites.')
        tk.Label(left, textvariable=self.frame_info, bg=BG, fg=MUTED, wraplength=350, justify='left').grid(row=3, column=0, sticky='w', pady=8)
        tk.Label(left, text='Click the sprite to select its material and shade.\nPreview uses neutral lighting; stage effects can differ.', bg=BG, fg=MUTED, justify='left').grid(row=4, column=0, sticky='w')
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
        ttk.Button(files, text='Save palette…', command=self.save_image).pack(side='left', padx=6)
        ttk.Button(right, text='Save Mod Manager ZIP…', style='Accent.TButton', command=lambda: self.export('zip')).grid(row=8, column=0, sticky='ew', pady=(8, 0))
        self.apply_button = ttk.Button(right, text='Apply palette to game…', style='Accent.TButton', command=self.open_apply, state='disabled')
        self.apply_button.grid(row=9, column=0, sticky='ew', pady=(8, 0))
        self.status = tk.StringVar(value='Choose the game folder above, then load a character and palette slot.')
        tk.Label(self, textvariable=self.status, bg=BG, fg=MUTED, wraplength=900, justify='left').grid(row=2, column=0, sticky='ew', pady=(10, 0))
        self.refresh()
        self.poll_id = self.after(100, self.poll)
        self.bind('<Destroy>', self.cleanup)
        self.auto_scan_id = self.after(250, self.auto_scan)

    def cleanup(self, event):
        if event.widget is self:
            self.after_cancel(self.poll_id)
            if self.auto_scan_id is not None:
                self.after_cancel(self.auto_scan_id)

    def confirm_discard(self):
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
        return not self.doc or not self.doc.dirty or messagebox.askyesno('Unsaved palette', 'Discard palette changes that have not been saved?', parent=self)

    def key(self):
        return next(k for k, name in NAMES.items() if name == self.character.get())

    def scan(self):
        if self.loading:
            return
        try:
            names = available_characters(self.game.get())
            if not names:
                raise ValueError('No characters with DDS palettes were found.')
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
            self.error(exc)
            return
        self.loading = True
        self.load_button.state(['disabled'])
        self.apply_button.state(['disabled'])
        self.status.set('Loading palette and sprite frames…')
        def work():
            try:
                self.events.put((True, PaletteDocument(game, character, slot)))
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
                self.doc = result
                self.choose_sprite_button.state(['!disabled'])
                self.palette_browser_button.state(['!disabled'])
                self.scan_slots(silent=True)
                representative = next((i for i, index in enumerate(result.frame_indices)
                                       if sum(m['used'] for k, m in result.frames[index]['images'].items() if k in (0, 1)) > 32), 0)
                self.frame.set(str(representative + 1))
                self.compare.set(False)
                self.row, self.shade = min(1, len(result.colors) - 1), 15
                self.frame_box.configure(to=len(result.frame_indices))
                self.status.set(f'{NAMES[result.character]} · palette {result.slot} · {len(result.colors)} materials. Apply directly or save a mod ZIP.')
                self.refresh()
            else:
                self.error(result)
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

    def render(self, event=None):
        self.canvas.delete('all')
        self.transform = None
        if not self.doc:
            self.canvas.create_text(max(140, self.canvas.winfo_width() // 2), max(100, self.canvas.winfo_height() // 2), text='Load a palette to begin', fill=MUTED)
            return
        try:
            index = self.index()
            image = self.doc.render(index, self.compare.get())
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
            mode = 'Original' if self.compare.get() else 'Edited'
            self.frame_info.set(f'{mode} · {NAMES[self.doc.character]} {self.doc.slot}p · frame {index} · {self.frame.get()} / {len(self.doc.frame_indices)}')
        except Exception as exc:
            self.frame_info.set(f'Cannot preview frame: {exc}')

    def refresh(self):
        self.apply_button.state(['!disabled'] if self.doc and not self.loading else ['disabled'])
        self.swatches.delete('all')
        self.undo_button.state(['!disabled'] if self.doc and self.doc.undo_stack else ['disabled'])
        self.redo_button.state(['!disabled'] if self.doc and self.doc.redo_stack else ['disabled'])
        if self.doc:
            for row, ramp in enumerate(self.doc.colors):
                y = row * 23 + 4
                self.swatches.create_text(27, y + 10, text=f'{row:03}', fill=ACCENT if row == self.row else MUTED, anchor='e')
                for shade, color in enumerate(ramp):
                    x = 36 + shade * 21
                    self.swatches.create_rectangle(x, y, x + 20, y + 20, fill='#%02x%02x%02x' % tuple(color[:3]), outline=PANEL)
                    if row == self.row and shade == self.shade:
                        self.swatches.create_rectangle(x - 1, y - 1, x + 21, y + 21, outline=ACCENT, width=2)
            self.swatches.configure(scrollregion=(0, 0, 380, len(self.doc.colors) * 23 + 8))
            color = self.doc.colors[self.row, self.shade]
            self.hex.set('#%02x%02x%02x' % tuple(color[:3]))
            self.alpha.set(str(color[3]))
            self.selection.set(f'Material {self.row:03} · shade {self.shade + 1} / 16' + ('  •  Unsaved' if self.doc.dirty else ''))
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
        self.compare.set(False)
        self.render()
        def change(color):
            session.preview(color)
            self.refresh()
        def finish(commit):
            session.finish(commit)
            self.picker = None
            if not commit:
                self.compare.set(comparing)
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
            self.mod_dialog = ModDetailsDialog(self, self.doc.mod_details,
                                               lambda details: self.save_export('zip', details, self.mod_dialog))
            return
        self.save_export(kind)

    def save_export(self, kind, details=None, parent=None):
        parent = parent or self
        types = [('Mod ZIP', '*.zip')] if kind == 'zip' else [('Palette PNG', '*.png'), ('Palette DDS', '*.dds')]
        extension = '.zip' if kind == 'zip' else '.png'
        path = filedialog.asksaveasfilename(parent=parent, title='Save mod ZIP' if kind == 'zip' else 'Save palette', initialfile=f'{self.doc.character}_{self.doc.slot}p{extension}', defaultextension=extension, filetypes=types)
        if path:
            try:
                fmt = Path(path).suffix.lower().lstrip('.')
                if fmt not in (['zip'] if kind == 'zip' else ['png', 'dds']):
                    raise ValueError('Choose one of the listed file formats.')
                self.doc.export(path, fmt, details)
                self.status.set(f'Saved {path}' + (' — import this ZIP in Mod Manager.' if fmt == 'zip' else ''))
                self.refresh()
                return True
            except Exception as exc:
                self.status.set(str(exc))
                messagebox.showerror('Palette editor', str(exc), parent=parent)
        return False

    def error(self, exc):
        self.status.set(str(exc))
        messagebox.showerror('Palette editor', str(exc), parent=self)
