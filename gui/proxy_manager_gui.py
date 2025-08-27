import tkinter as tk
from tkinter import ttk, messagebox
from proxy.manager import ProxyManager


class ProxyManagerFrame(ttk.Frame):
    """UI component for managing proxies."""

    def __init__(self, master, manager: ProxyManager):
        super().__init__(master)
        self.manager = manager
        self.create_widgets()
        self.refresh_list()

    def create_widgets(self) -> None:
        self.listbox = tk.Listbox(self)
        self.listbox.pack(fill='both', expand=True, padx=5, pady=5)

        entry_frame = ttk.Frame(self)
        entry_frame.pack(fill='x', padx=5, pady=5)

        self.entry = ttk.Entry(entry_frame)
        self.entry.pack(side='left', fill='x', expand=True)

        ttk.Button(entry_frame, text="Add", command=self.add_proxy).pack(side='left', padx=5)
        ttk.Button(entry_frame, text="Remove", command=self.remove_selected).pack(side='left')

    def refresh_list(self) -> None:
        self.listbox.delete(0, tk.END)
        for proxy in self.manager.proxies:
            self.listbox.insert(tk.END, proxy)

    def add_proxy(self) -> None:
        proxy = self.entry.get().strip()
        if proxy:
            try:
                self.manager.add_proxy(proxy)
                self.refresh_list()
                self.entry.delete(0, tk.END)
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def remove_selected(self) -> None:
        selection = self.listbox.curselection()
        if selection:
            proxy = self.listbox.get(selection[0])
            try:
                self.manager.remove_proxy(proxy)
                self.refresh_list()
            except Exception as e:
                messagebox.showerror("Error", str(e))
