import tkinter as tk
from tkinter import ttk, messagebox

import requests

from proxy.manager import ProxyManager


class ProxyManagerFrame(ttk.Frame):
    """UI component for managing proxies."""

    def __init__(self, master, manager: ProxyManager):
        super().__init__(master)
        self.manager = manager
        self.create_widgets()
        self.refresh_list()

    def create_widgets(self) -> None:
        self.tree = ttk.Treeview(self, columns=("proxy", "status"), show="headings")
        self.tree.heading("proxy", text="Proxy")
        self.tree.heading("status", text="Status")
        self.tree.column("status", width=80, anchor="center")
        self.tree.tag_configure("Working", foreground="green")
        self.tree.tag_configure("Down", foreground="red")
        self.tree.tag_configure("Unknown", foreground="orange")
        self.tree.pack(fill='both', expand=True, padx=5, pady=5)

        entry_frame = ttk.Frame(self)
        entry_frame.pack(fill='x', padx=5, pady=5)

        self.entry = ttk.Entry(entry_frame)
        self.entry.pack(side='left', fill='x', expand=True)

        ttk.Button(entry_frame, text="Add", command=self.add_proxy).pack(side='left', padx=5)
        ttk.Button(entry_frame, text="Remove", command=self.remove_selected).pack(side='left')
        ttk.Button(entry_frame, text="Check Health", command=self.update_health).pack(side='left', padx=5)

    def refresh_list(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        for proxy in self.manager.proxies:
            self.tree.insert("", tk.END, values=(proxy, "Unknown"), tags=("Unknown",))
        # schedule health update
        self.after(1000, self.update_health)

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
        sel = self.tree.selection()
        if sel:
            proxy = self.tree.item(sel[0], "values")[0]
            try:
                self.manager.remove_proxy(proxy)
                self.refresh_list()
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def update_health(self) -> None:
        """Ping proxies and update status colors."""
        for item in self.tree.get_children():
            proxy = self.tree.item(item, "values")[0]
            status = self._ping_proxy(proxy)
            self.tree.item(item, values=(proxy, status), tags=(status,))
        # refresh again in 60s
        self.after(60000, self.update_health)

    def _ping_proxy(self, proxy: str) -> str:
        proxies = {"http": proxy, "https": proxy}
        try:
            requests.get("https://www.google.com", proxies=proxies, timeout=5)
            return "Working"
        except Exception:
            return "Down"
