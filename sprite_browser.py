"""A paged thumbnail selector for the loaded character's decoded sprites."""
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageDraw, ImageTk
from theme import BG, PANEL, TEXT, MUTED, ACCENT, BORDER


class SpriteBrowser(tk.Toplevel):
    PAGE_SIZE = 12

    def __init__(self, parent, document, current, on_select, original=False, palettes=False):
        super().__init__(parent)
        self.withdraw()
        self.palettes = palettes
        self.title('Choose palette to edit' if palettes else 'Choose preview sprite')
        self.configure(bg=BG)
        self.transient(parent.winfo_toplevel())
        self.resizable(False, False)
        self.document, self.on_select, self.original = document, on_select, original
        self.indices = list(document.frame_indices)
        self.selected = self.indices.index(current) if current in self.indices else 0
        self.page = self.selected // self.PAGE_SIZE
        self.photos, self.tiles = [], []
        self.pending = None
        self.generation = 0
        self.failed = set()
        tk.Label(self, text='CHOOSE PALETTE TO EDIT' if palettes else 'CHOOSE PREVIEW SPRITE', bg=BG, fg=ACCENT,
                 font=('Segoe UI', 12, 'bold')).pack(anchor='w', padx=16, pady=(14, 3))
        tk.Label(self, text='Select a palette to edit. Double-click to choose immediately.' if palettes else 'Select a thumbnail, then Use sprite. Double-click to choose immediately.',
                 bg=BG, fg=MUTED).pack(anchor='w', padx=16, pady=(0, 10))
        self.grid_frame = tk.Frame(self, bg=BG)
        self.grid_frame.pack(padx=12)
        for i in range(self.PAGE_SIZE):
            tile = tk.Frame(self.grid_frame, bg=PANEL, highlightthickness=2, highlightbackground=BORDER)
            tile.grid(row=i // 4, column=i % 4, padx=4, pady=4)
            picture = tk.Label(tile, bg=PANEL, width=1, height=1)
            picture.pack()
            caption = tk.Label(tile, bg=PANEL, fg=TEXT, font=('Segoe UI', 9), pady=4)
            caption.pack(fill='x')
            self.tiles.append((tile, picture, caption))
        nav = tk.Frame(self, bg=BG)
        nav.pack(fill='x', padx=16, pady=(10, 5))
        self.previous = ttk.Button(nav, text='‹ Previous', command=lambda: self.change_page(-1))
        self.previous.pack(side='left')
        self.page_text = tk.StringVar()
        tk.Label(nav, textvariable=self.page_text, bg=BG, fg=TEXT).pack(side='left', expand=True)
        self.next = ttk.Button(nav, text='Next ›', command=lambda: self.change_page(1))
        self.next.pack(side='right')
        jump = tk.Frame(self, bg=BG)
        jump.pack(fill='x', padx=16, pady=5)
        tk.Label(jump, text='Go to palette' if palettes else 'Go to sprite', bg=BG, fg=MUTED).pack(side='left')
        self.jump = tk.StringVar(value=str(self.indices[self.selected]) if palettes else str(self.selected + 1))
        entry = ttk.Entry(jump, width=7, textvariable=self.jump)
        entry.pack(side='left', padx=6)
        entry.bind('<Return>', self.go_to)
        ttk.Button(jump, text='Go', width=5, command=self.go_to).pack(side='left')
        self.note = tk.StringVar()
        tk.Label(self, textvariable=self.note, bg=BG, fg=MUTED).pack(anchor='w', padx=16, pady=5)
        buttons = tk.Frame(self, bg=BG)
        buttons.pack(fill='x', padx=16, pady=(4, 14))
        ttk.Button(buttons, text='Cancel', command=self.destroy).pack(side='left')
        self.use_button = ttk.Button(buttons, text='Edit palette' if palettes else 'Use sprite', style='Accent.TButton', command=self.use)
        self.use_button.pack(side='right')
        self.bind('<Escape>', lambda event: self.destroy())
        self.bind('<Destroy>', self.cleanup)
        self.show_page()
        self.update_idletasks()
        root = parent.winfo_toplevel()
        width, height = self.winfo_reqwidth(), self.winfo_reqheight()
        x = max(0, min(root.winfo_rootx() + (root.winfo_width() - width) // 2, self.winfo_screenwidth() - width))
        y = max(0, min(root.winfo_rooty() + 60, self.winfo_screenheight() - height - 60))
        self.geometry(f'+{x}+{y}')
        self.deiconify()
        self.grab_set()

    @staticmethod
    def thumbnail(image=None):
        board = Image.new('RGBA', (144, 116), '#30292e')
        draw = ImageDraw.Draw(board)
        for y in range(0, 116, 12):
            for x in range(0, 144, 12):
                if (x // 12 + y // 12) % 2:
                    draw.rectangle((x, y, x + 11, y + 11), fill='#3c343a')
        if image is not None:
            image = image.convert('RGBA')
            box = image.getbbox()
            if box:
                image = image.crop(box)
                image.thumbnail((132, 104), Image.Resampling.LANCZOS)
                board.alpha_composite(image, ((144 - image.width) // 2, (116 - image.height) // 2))
        return board

    def cleanup(self, event):
        if event.widget is self and self.pending is not None:
            self.after_cancel(self.pending)
            self.pending = None

    def show_page(self):
        if self.pending is not None:
            self.after_cancel(self.pending)
            self.pending = None
        self.generation += 1
        generation = self.generation
        self.photos = []
        start = self.page * self.PAGE_SIZE
        stop = min(start + self.PAGE_SIZE, len(self.indices))
        self.page_text.set(f'{start + 1}–{stop} of {len(self.indices):,}')
        self.previous.state(['disabled'] if self.page == 0 else ['!disabled'])
        self.next.state(['disabled'] if stop == len(self.indices) else ['!disabled'])
        blank = ImageTk.PhotoImage(self.thumbnail(), master=self)
        self.photos.append(blank)
        for i, (tile, picture, caption) in enumerate(self.tiles):
            position = start + i
            if position >= stop:
                tile.grid_remove()
                continue
            tile.grid()
            picture.configure(image=blank, width=144, height=116)
            caption.configure(text=f'Palette {self.indices[position]}' if self.palettes else f'Sprite {position + 1} · frame {self.indices[position]}')
            for widget in (tile, picture, caption):
                widget.bind('<Button-1>', lambda event, p=position: self.select(p))
                widget.bind('<Double-Button-1>', lambda event, p=position: self.choose(p))
        self.highlight()
        self.pending = self.after(1, lambda: self.render_next(0, generation))

    def render_next(self, tile_index, generation):
        self.pending = None
        if generation != self.generation:
            return
        position = self.page * self.PAGE_SIZE + tile_index
        if tile_index >= self.PAGE_SIZE or position >= len(self.indices):
            return
        _, picture, caption = self.tiles[tile_index]
        try:
            image = self.document.render(self.indices[position], self.original)
            photo = ImageTk.PhotoImage(self.thumbnail(image), master=self)
            self.photos.append(photo)
            picture.configure(image=photo)
            self.failed.discard(position)
        except Exception:
            self.failed.add(position)
            caption.configure(text=f'Palette {self.indices[position]} · unavailable' if self.palettes else f'Sprite {position + 1} · unavailable')
        self.highlight()
        self.pending = self.after(1, lambda: self.render_next(tile_index + 1, generation))

    def highlight(self):
        start = self.page * self.PAGE_SIZE
        for i, (tile, _, _) in enumerate(self.tiles):
            tile.configure(highlightbackground=ACCENT if start + i == self.selected else BORDER)
        self.note.set(f'Selected: palette {self.indices[self.selected]}' if self.palettes else f'Selected: sprite {self.selected + 1} · frame {self.indices[self.selected]}')
        self.use_button.state(['disabled'] if self.selected in self.failed else ['!disabled'])

    def select(self, position):
        self.selected = position
        self.highlight()

    def choose(self, position):
        self.select(position)
        self.use()

    def use(self):
        if self.selected not in self.failed:
            self.on_select(self.indices[self.selected])
            self.destroy()

    def change_page(self, direction):
        self.page = max(0, min((len(self.indices) - 1) // self.PAGE_SIZE, self.page + direction))
        self.show_page()

    def go_to(self, event=None):
        try:
            position = self.indices.index(int(self.jump.get())) if self.palettes else int(self.jump.get()) - 1
            if not 0 <= position < len(self.indices):
                raise ValueError()
        except ValueError:
            self.note.set(f'Enter a sprite number from 1 to {len(self.indices):,}.')
            return
        self.page = position // self.PAGE_SIZE
        self.selected = position
        self.show_page()
