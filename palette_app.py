"""Standalone Skullgirls Palette Editor entry point."""
from pathlib import Path
import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog
from theme import configure_theme, BG, MUTED
from palette_ui import PaletteEditor


def create_app(recovery_directory=None):
    root = tk.Tk()
    root.title('Skullgirls Palette Editor')
    root.geometry('1120x820')
    root.minsize(900, 720)
    root.configure(bg=BG)
    configure_theme(root)
    root.columnconfigure(0, weight=1)
    root.rowconfigure(2, weight=1)
    tk.Label(root, text='S K U L L G I R L S   /   PALETTE EDITOR', bg=BG, fg=MUTED, font=('Georgia', 18, 'bold')).grid(row=0, column=0, pady=16)
    bar = tk.Frame(root, bg=BG)
    bar.grid(row=1, column=0, sticky='ew', padx=20)
    bar.columnconfigure(1, weight=1)
    base = Path(sys.executable if getattr(sys, 'frozen', False) else __file__).resolve()
    candidates = [base.parents[2] / 'steamapps' / 'common' / 'Skullgirls']
    if os.name == 'nt':
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam') as key:
                candidates.insert(0, Path(winreg.QueryValueEx(key, 'SteamPath')[0]) / 'steamapps' / 'common' / 'Skullgirls')
        except OSError:
            pass
    candidates.append(Path(os.environ.get('PROGRAMFILES(X86)', 'C:/Program Files (x86)')) / 'Steam' / 'steamapps' / 'common' / 'Skullgirls')
    guess = next((path for path in candidates if path.is_dir()), '')
    game = tk.StringVar(value=str(guess))
    tk.Label(bar, text='GAME FOLDER', bg=BG, fg=MUTED).grid(row=0, column=0, padx=(0, 10))
    ttk.Entry(bar, textvariable=game).grid(row=0, column=1, sticky='ew')
    def browse():
        path = filedialog.askdirectory(parent=root, title='Select Skullgirls game folder')
        if path:
            game.set(path)
    ttk.Button(bar, text='Browse…', command=browse).grid(row=0, column=2, padx=(10, 0))
    editor = PaletteEditor(root, game, recovery_directory)
    editor.grid(row=2, column=0, sticky='nsew', padx=8, pady=8)
    root.protocol('WM_DELETE_WINDOW', lambda: root.destroy() if editor.confirm_discard() else None)
    return root, editor


def main():
    if '--export-apply-source' in sys.argv:
        import shutil
        base = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
        shutil.copyfile(base / 'manager_bridge' / 'source.zip', sys.argv[sys.argv.index('--export-apply-source') + 1])
        return
    if '--self-test' in sys.argv:
        from test_palette import run
        run()
        from test_direct_apply import run as test_apply
        test_apply()
        return
    root, editor = create_app()
    if '--smoke-test' in sys.argv:
        import json
        root.withdraw()
        root.update_idletasks()
        assert root.title() == 'Skullgirls Palette Editor'
        assert editor.winfo_reqheight() < 720
        root.destroy()
        Path(sys.argv[sys.argv.index('--smoke-test') + 1]).write_text(json.dumps({'ui': 'passed', 'app': 'Skullgirls Palette Editor'}))
    else:
        root.mainloop()


if __name__ == '__main__':
    main()
