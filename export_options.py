"""Explain standalone export contents and compatibility before choosing a path."""
import tkinter as tk
from tkinter import ttk
from decoder import NAMES
from theme import BG, MUTED, ACCENT


CONTENTS = {
    'png': ('PNG palette image',
            'RGBA palette colors for sharing and reimporting. Contains 16 shades per material; '
            'gameplay changes and installation files are supplied by mod ZIP export.'),
    'dds': ('DDS palette texture',
            'The character-select palette texture, using this source game\'s texture layout. '
            'Use with a matching game build. Gameplay changes and installation files are supplied by mod ZIP export.'),
    'zip': ('Menu + gameplay mod ZIP',
            'Includes the character-select DDS, the full character metadata with gameplay palette changes, '
            'and mod details. Use the same game build and character mods as this source.\n\n'
            'Any mod replacing this character metadata can override palette changes, regardless of installer. '
            'The package contains all palette slots in that metadata.\n\n'
            'Export works without Mod Manager or Sprite Workshop. Installing the ZIP requires a compatible mod installer.'),
}


def export_notes(document, kind):
    title, contents = CONTENTS[kind]
    note = (f'{contents}\n\n{NAMES[document.character]} · palette {document.slot} · '
            f'16 × {len(document.colors)} colors\nSource data: {document.source}\n\n'
            'Save project separately to resume editable work.')
    issue = None
    if kind == 'zip':
        try:
            document.export_metadata()
        except (OSError, ValueError, KeyError) as exc:
            issue = f'Mod ZIP unavailable: {exc}\nYou can still export PNG/DDS palette colors.'
    return title, note, issue


class ImageExportDialog(tk.Toplevel):
    def __init__(self, parent, document, on_save):
        super().__init__(parent)
        self.withdraw()
        self.title('Export palette image')
        self.configure(bg=BG, padx=20, pady=16)
        self.transient(parent.winfo_toplevel())
        self.resizable(False, False)
        self.document, self.on_save = document, on_save
        tk.Label(self, text='EXPORT PALETTE IMAGE', bg=BG, fg=ACCENT,
                 font=('Segoe UI', 13, 'bold')).pack(anchor='w')
        self.kind = tk.StringVar(value='png')
        choices = tk.Frame(self, bg=BG)
        choices.pack(fill='x', pady=12)
        for kind in ('png', 'dds'):
            ttk.Radiobutton(choices, text=CONTENTS[kind][0], variable=self.kind,
                            value=kind, command=self.update_note).pack(side='left', padx=(0, 16))
        self.note = tk.StringVar()
        tk.Label(self, textvariable=self.note, bg=BG, fg=MUTED, wraplength=470,
                 justify='left').pack(fill='x', pady=(0, 16))
        buttons = tk.Frame(self, bg=BG)
        buttons.pack(fill='x')
        ttk.Button(buttons, text='Cancel', command=self.destroy).pack(side='left')
        self.export_button = ttk.Button(buttons, text='Export PNG…', style='Accent.TButton', command=self.submit)
        self.export_button.pack(side='right')
        self.bind('<Escape>', lambda event: self.destroy())
        self.update_note()
        self.update_idletasks()
        root = parent.winfo_toplevel()
        x = max(0, min(root.winfo_rootx() + (root.winfo_width() - self.winfo_reqwidth()) // 2,
                       self.winfo_screenwidth() - self.winfo_reqwidth()))
        y = max(0, min(root.winfo_rooty() + 80, self.winfo_screenheight() - self.winfo_reqheight() - 60))
        self.geometry(f'+{x}+{y}')
        self.deiconify()
        self.grab_set()
        self.export_button.focus_set()

    def update_note(self):
        _, note, _ = export_notes(self.document, self.kind.get())
        self.note.set(note)
        self.export_button.configure(text=f'Export {self.kind.get().upper()}…')

    def submit(self):
        if self.on_save(self.kind.get(), self):
            self.destroy()
