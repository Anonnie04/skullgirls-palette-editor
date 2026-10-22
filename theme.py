"""Shared visual style of the Skullgirls desktop tools."""
from tkinter import ttk
BG='#181416';PANEL='#292124';TEXT='#f5ead5';MUTED='#c2b39e';ACCENT='#e6bc68'
BURGUNDY='#542733';BORDER='#806345';HOVER='#403038';DISABLED='#8f827b'

def configure_theme(root):
 style=ttk.Style(root);style.theme_use('clam')
 root.option_add('*Font',('Segoe UI',10))
 root.option_add('*Listbox.background',PANEL);root.option_add('*Listbox.foreground',TEXT)
 root.option_add('*Listbox.selectBackground',BURGUNDY);root.option_add('*Listbox.selectForeground',TEXT)
 style.configure('.',background=BG,foreground=TEXT,font=('Segoe UI',10),bordercolor=BORDER,lightcolor=BORDER,darkcolor=BG,focuscolor=ACCENT)
 for name in ('TEntry','TCombobox','TSpinbox'):
  style.configure(name,fieldbackground=PANEL,foreground=TEXT,insertcolor=TEXT,padding=7,arrowcolor=ACCENT)
  style.map(name,fieldbackground=[('disabled',BG),('readonly',PANEL)],foreground=[('disabled',DISABLED),('readonly',TEXT)],bordercolor=[('focus',ACCENT)])
 style.configure('TButton',background=PANEL,foreground=TEXT,padding=(12,8),borderwidth=1)
 style.map('TButton',background=[('disabled',BG),('pressed',BURGUNDY),('active',HOVER)],foreground=[('disabled',DISABLED)],bordercolor=[('focus',ACCENT),('active',ACCENT)])
 style.configure('Accent.TButton',background=ACCENT,foreground=BG,font=('Segoe UI',11,'bold'))
 style.map('Accent.TButton',background=[('disabled',PANEL),('pressed','#c79b4e'),('active','#f6d897')],foreground=[('disabled',DISABLED),('!disabled',BG)])
 style.configure('TCheckbutton',background=PANEL,foreground=TEXT,padding=4,indicatorbackground=BG,indicatorforeground=BG)
 style.map('TCheckbutton',background=[('active',HOVER)],foreground=[('disabled',DISABLED)],indicatorbackground=[('disabled',PANEL),('selected',ACCENT)],bordercolor=[('focus',ACCENT)])
 style.configure('TProgressbar',troughcolor=PANEL,background=ACCENT,bordercolor=BORDER,lightcolor=ACCENT,darkcolor=ACCENT)
 style.configure('TNotebook',background=BG,borderwidth=1,tabmargins=(0,0,0,0))
 style.configure('TNotebook.Tab',background=PANEL,foreground=MUTED,padding=(20,10),font=('Segoe UI',10,'bold'))
 style.map('TNotebook.Tab',background=[('selected',BURGUNDY),('active',HOVER)],foreground=[('selected',ACCENT),('active',TEXT)])
 style.configure('Treeview',background=PANEL,fieldbackground=PANEL,foreground=TEXT,rowheight=28)
 style.map('Treeview',background=[('selected',BURGUNDY)],foreground=[('selected',TEXT)])
 style.configure('Treeview.Heading',background=BURGUNDY,foreground=ACCENT,font=('Segoe UI',10,'bold'),padding=(8,6))
 style.map('Treeview.Heading',background=[('active',HOVER)])
 style.configure('TScrollbar',background=PANEL,troughcolor=BG,arrowcolor=ACCENT)
 style.map('TScrollbar',background=[('active',HOVER),('pressed',BURGUNDY)])
