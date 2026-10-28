"""Edit the mod's display details before choosing an export destination."""
import tkinter as tk
from tkinter import ttk
from theme import BG, PANEL, TEXT, MUTED, ACCENT, BORDER
from mod_info import validate_details


class ModDetailsDialog(tk.Toplevel):
    def __init__(self, parent, details, on_save, apply_to=None, save_label=None, note=None, export_error=None):
        super().__init__(parent)
        self.withdraw()
        self.title('Apply palette to game' if apply_to else 'Mod details')
        self.configure(bg=BG, padx=20, pady=16)
        self.transient(parent.winfo_toplevel())
        self.resizable(True, True)
        self.minsize(480, 420)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(7, weight=1)
        self.on_save = on_save
        tk.Label(self, text='APPLY PALETTE' if apply_to else 'MOD DETAILS', bg=BG, fg=ACCENT, font=('Segoe UI', 13, 'bold')).grid(row=0, column=0, sticky='w')
        self.note = apply_to or note or 'These details appear in Mod Manager.'
        tk.Label(self, text=self.note, bg=BG, fg=MUTED, wraplength=470, justify='left').grid(row=1, column=0, sticky='w', pady=(2, 16))
        tk.Label(self, text='NAME', bg=BG, fg=MUTED).grid(row=2, column=0, sticky='w')
        self.name = tk.StringVar(value=details['name'])
        self.name_entry = ttk.Entry(self, textvariable=self.name, width=55)
        self.name_entry.grid(row=3, column=0, sticky='ew', pady=(4, 12))
        tk.Label(self, text='VERSION', bg=BG, fg=MUTED).grid(row=4, column=0, sticky='w')
        self.version = tk.StringVar(value=details['version'])
        ttk.Entry(self, textvariable=self.version, width=16).grid(row=5, column=0, sticky='w', pady=(4, 12))
        tk.Label(self, text='DESCRIPTION', bg=BG, fg=MUTED).grid(row=6, column=0, sticky='w')
        self.description = tk.Text(self, height=4 if note else 7, width=55, wrap='word', bg=PANEL, fg=TEXT,
                                   insertbackground=TEXT, selectbackground='#542733',
                                   borderwidth=0, highlightthickness=1, highlightbackground=BORDER,
                                   highlightcolor=ACCENT, padx=10, pady=8, undo=True)
        self.description.grid(row=7, column=0, sticky='nsew', pady=(4, 10))
        self.description.insert('1.0', details['desc'])
        self.export_error = export_error
        self.error = tk.StringVar(value=export_error or '')
        tk.Label(self, textvariable=self.error, bg=BG, fg='#f0aaa5', wraplength=470, justify='left').grid(row=8, column=0, sticky='ew', pady=(0, 8))
        buttons = tk.Frame(self, bg=BG)
        buttons.grid(row=9, column=0, sticky='ew')
        ttk.Button(buttons, text='Cancel', command=self.destroy).pack(side='left')
        self.save_button = ttk.Button(buttons, text='Apply to game' if apply_to else save_label or 'Save ZIP…',
                                      style='Accent.TButton', command=self.submit,
                                      state='disabled' if export_error else 'normal')
        self.save_button.pack(side='right')
        self.bind('<Escape>', lambda event: self.destroy())
        self.update_idletasks()
        root = parent.winfo_toplevel()
        width, height = self.winfo_reqwidth(), self.winfo_reqheight()
        x = max(0, min(root.winfo_rootx() + (root.winfo_width() - width) // 2, self.winfo_screenwidth() - width))
        y = max(0, min(root.winfo_rooty() + 100, self.winfo_screenheight() - height - 60))
        self.geometry(f'+{x}+{y}')
        self.deiconify()
        self.grab_set()
        self.name_entry.focus_set()

    def submit(self):
        if self.export_error:
            return
        try:
            details = validate_details(dict(name=self.name.get(), version=self.version.get(),
                                            desc=self.description.get('1.0', 'end-1c')))
        except ValueError as exc:
            self.error.set(str(exc))
            return
        self.error.set('')
        if self.on_save(details):
            self.destroy()
