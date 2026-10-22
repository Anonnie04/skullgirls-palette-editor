"""Hue ring and saturation/value picker with coalesced live callbacks."""
import colorsys
import math
from functools import lru_cache
import tkinter as tk
from tkinter import ttk
import numpy as np
from PIL import Image, ImageTk
from theme import BG, PANEL, TEXT, MUTED, ACCENT

SIZE = 288
CENTER = SIZE / 2
INNER, OUTER = 118, 140
SQUARE = 156
START = (SIZE - SQUARE) // 2


@lru_cache(maxsize=1)
def hue_ring():
    scale = 3
    y, x = np.mgrid[:SIZE * scale, :SIZE * scale].astype(float)
    dx, dy = (x + .5) / scale - CENTER, (y + .5) / scale - CENTER
    radius = np.hypot(dx, dy)
    hue = np.mod(np.arctan2(-dy, dx) / (2 * math.pi), 1)
    hsv = np.empty((SIZE * scale, SIZE * scale, 3), dtype=np.uint8)
    hsv[:, :, 0] = np.rint(hue * 255).astype(np.uint8)
    hsv[:, :, 1:] = 255
    ring = Image.fromarray(hsv, 'HSV').convert('RGBA')
    ring.putalpha(Image.fromarray(np.where((radius >= INNER) & (radius <= OUTER), 255, 0).astype(np.uint8)))
    board = Image.new('RGBA', ring.size, PANEL)
    board.alpha_composite(ring)
    return board.resize((SIZE, SIZE), Image.Resampling.LANCZOS)


class ColorWheel(tk.Toplevel):
    def __init__(self, parent, rgb, on_change, on_finish, title='Choose color'):
        super().__init__(parent)
        self.withdraw()
        self.title(title)
        self.configure(bg=PANEL)
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        self.on_change, self.on_finish = on_change, on_finish
        self.h, self.s, self.v = colorsys.rgb_to_hsv(*(c / 255 for c in rgb))
        self.original = tuple(rgb)
        self.pending = None
        self.closed = False
        self.drag_mode = None
        self._square_hue = None
        self.columnconfigure(0, weight=1)
        tk.Label(self, text='COLOR WHEEL', bg=PANEL, fg=ACCENT, font=('Segoe UI', 12, 'bold')).grid(row=0, column=0, sticky='w', padx=20, pady=(16, 2))
        tk.Label(self, text='Drag to preview changes on the sprite.', bg=PANEL, fg=MUTED).grid(row=1, column=0, sticky='w', padx=20)
        self.canvas = tk.Canvas(self, width=SIZE, height=SIZE, bg=PANEL, highlightthickness=0, cursor='crosshair')
        self.canvas.grid(row=2, column=0, padx=20, pady=8)
        self.ring_photo = ImageTk.PhotoImage(hue_ring(), master=self)
        self.canvas.create_image(0, 0, anchor='nw', image=self.ring_photo)
        self.square_id = self.canvas.create_image(START, START, anchor='nw')
        self.hue_outer = self.canvas.create_oval(0, 0, 0, 0, outline='#101014', width=4)
        self.hue_inner = self.canvas.create_oval(0, 0, 0, 0, outline='white', width=2)
        self.sv_outer = self.canvas.create_oval(0, 0, 0, 0, outline='#101014', width=4)
        self.sv_inner = self.canvas.create_oval(0, 0, 0, 0, outline='white', width=2)
        self.canvas.bind('<Button-1>', self.press)
        self.canvas.bind('<B1-Motion>', self.drag)
        self.canvas.bind('<ButtonRelease-1>', self.release)
        fields = tk.Frame(self, bg=PANEL)
        fields.grid(row=3, column=0, sticky='ew', padx=20)
        self.before = tk.Label(fields, width=5, bg=self.hex_color(rgb), text=' ', relief='flat')
        self.before.pack(side='left', ipady=5)
        self.after_swatch = tk.Label(fields, width=5, text=' ', relief='flat')
        self.after_swatch.pack(side='left', padx=(3, 12), ipady=5)
        self.hex = tk.StringVar()
        self.hex_entry = ttk.Entry(fields, textvariable=self.hex, width=10)
        self.hex_entry.pack(side='left')
        self.hex_entry.bind('<Return>', self.apply_hex)
        self.hex_entry.bind('<FocusOut>', self.apply_hex)
        ttk.Button(fields, text='Set', width=5, command=self.apply_hex).pack(side='left', padx=(5, 0))
        self.values = tk.StringVar()
        tk.Label(self, textvariable=self.values, bg=PANEL, fg=MUTED, font=('Segoe UI', 9)).grid(row=4, column=0, sticky='w', padx=20, pady=(7, 2))
        self.note = tk.StringVar(value='Before / after · alpha stays unchanged')
        tk.Label(self, textvariable=self.note, bg=PANEL, fg=MUTED, font=('Segoe UI', 9)).grid(row=5, column=0, sticky='w', padx=20, pady=(0, 10))
        buttons = tk.Frame(self, bg=PANEL)
        buttons.grid(row=6, column=0, sticky='ew', padx=20, pady=(0, 16))
        ttk.Button(buttons, text='Cancel', command=lambda: self.finish(False)).pack(side='left')
        ttk.Button(buttons, text='Apply color', style='Accent.TButton', command=lambda: self.finish(True)).pack(side='right')
        self.protocol('WM_DELETE_WINDOW', lambda: self.finish(False))
        self.bind('<Escape>', lambda e: self.finish(False))
        self.bind('<Destroy>', self.destroyed)
        self.draw()
        self.update_idletasks()
        root = parent.winfo_toplevel()
        # Cover the palette panel, leaving the left sprite preview visible.
        width, height = self.winfo_reqwidth(), self.winfo_reqheight()
        x = root.winfo_rootx() + root.winfo_width() - width - 20
        y = root.winfo_rooty() + 140
        x = max(0, min(x, self.winfo_screenwidth() - width))
        y = max(0, min(y, self.winfo_screenheight() - height - 60))
        self.geometry(f'+{x}+{y}')
        self.deiconify()
        self.grab_set()
        self.focus_set()

    @staticmethod
    def hex_color(rgb):
        return '#%02X%02X%02X' % tuple(rgb)

    def rgb(self):
        return tuple(round(c * 255) for c in colorsys.hsv_to_rgb(self.h, self.s, self.v))

    def draw(self):
        if self._square_hue != self.h:
            hsv = np.empty((SQUARE, SQUARE, 3), dtype=np.uint8)
            hsv[:, :, 0] = round(self.h * 255)
            hsv[:, :, 1] = np.rint(np.linspace(0, 255, SQUARE)).astype(np.uint8)[None, :]
            hsv[:, :, 2] = np.rint(np.linspace(255, 0, SQUARE)).astype(np.uint8)[:, None]
            self.square_photo = ImageTk.PhotoImage(Image.fromarray(hsv, 'HSV').convert('RGB'), master=self)
            self.canvas.itemconfigure(self.square_id, image=self.square_photo)
            self._square_hue = self.h
        angle = self.h * 2 * math.pi
        radius = (INNER + OUTER) / 2
        hx, hy = CENTER + radius * math.cos(angle), CENTER - radius * math.sin(angle)
        sx, sy = START + self.s * (SQUARE - 1), START + (1 - self.v) * (SQUARE - 1)
        for item in (self.hue_outer, self.hue_inner):
            self.canvas.coords(item, hx - 6, hy - 6, hx + 6, hy + 6)
        for item in (self.sv_outer, self.sv_inner):
            self.canvas.coords(item, sx - 5, sy - 5, sx + 5, sy + 5)
        rgb = self.rgb()
        self.hex.set(self.hex_color(rgb))
        self.after_swatch.configure(bg=self.hex_color(rgb))
        self.values.set(f'RGB  {rgb[0]}  {rgb[1]}  {rgb[2]}     HSV  {round(self.h * 360)}°  {round(self.s * 100)}%  {round(self.v * 100)}%')

    def press(self, event):
        radius = math.hypot(event.x - CENTER, event.y - CENTER)
        if INNER - 4 <= radius <= OUTER + 8:
            self.drag_mode = 'hue'
        elif START <= event.x < START + SQUARE and START <= event.y < START + SQUARE:
            self.drag_mode = 'sv'
        else:
            self.drag_mode = None
        self.drag(event)

    def drag(self, event):
        if self.closed or not self.drag_mode:
            return
        if self.drag_mode == 'hue':
            self.h = math.atan2(CENTER - event.y, event.x - CENTER) / (2 * math.pi) % 1
        else:
            self.s = max(0, min(1, (event.x - START) / (SQUARE - 1)))
            self.v = max(0, min(1, 1 - (event.y - START) / (SQUARE - 1)))
        self.draw()
        self.schedule()

    def release(self, event):
        if self.drag_mode:
            self.drag(event)
            self.drag_mode = None
            self.flush()

    def schedule(self):
        if self.pending is None:
            self.pending = self.after(25, self.flush)

    def flush(self):
        if self.pending is not None:
            self.after_cancel(self.pending)
            self.pending = None
        if not self.closed:
            self.on_change(self.rgb())

    def apply_hex(self, event=None):
        text = self.hex.get().strip().lstrip('#')
        try:
            if len(text) != 6:
                raise ValueError()
            rgb = tuple(int(text[i:i + 2], 16) for i in (0, 2, 4))
        except ValueError:
            self.note.set('Enter six hex digits, for example #E6BC68.')
            return False
        self.h, self.s, self.v = colorsys.rgb_to_hsv(*(c / 255 for c in rgb))
        self.note.set('Before / after · alpha stays unchanged')
        self.draw()
        self.schedule()
        return True

    def finish(self, commit):
        if self.closed:
            return
        # A typed hex value is accepted even if Apply is clicked before focus changes.
        if commit and self.hex.get().upper() != self.hex_color(self.rgb()):
            if not self.apply_hex():
                return
        if commit and self.pending is not None:
            self.flush()
        self.closed = True
        if self.pending is not None:
            self.after_cancel(self.pending)
            self.pending = None
        self.grab_release()
        self.on_finish(commit)
        self.destroy()

    def destroyed(self, event):
        if event.widget is self and not self.closed:
            self.closed = True
            if self.pending is not None:
                self.after_cancel(self.pending)
                self.pending = None
            self.on_finish(False)
