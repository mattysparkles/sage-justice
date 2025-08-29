import json
import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, messagebox, scrolledtext

from core.site_registry import (
    delete_site,
    export_site,
    get_site,
    get_sites,
    import_site,
    save_site,
)
from tools.guided_mapper import run_guided_mapper
from core import database, project_hub

CAPTCHA_OPTIONS = ["manual", "solver", "none"]


class SiteManagerFrame(ttk.Frame):
    """GUI for managing review site configurations."""

    def __init__(self, master, *, on_update=None):
        super().__init__(master)
        self.on_update = on_update
        self.sites: list[dict] = []
        self.current_name: str | None = None
        self._load_sites()
        self._build_widgets()
        self._refresh_list()

    # ------------------------------------------------------------------
    # Data helpers
    def _load_sites(self) -> None:
        self.sites = get_sites()
        for entry in self.sites:
            entry["projects"] = database.get_site_projects(entry["name"])

    def _save_current(self) -> None:
        data = {
            "site": self.name_var.get().strip(),
            "category": self.category_var.get().strip(),
            "url": self.url_var.get().strip(),
            "requires_login": self.login_var.get(),
            "captcha": self.captcha_var.get(),
            "geolocation_spoofing": self.geo_var.get(),
        }
        try:
            selectors = json.loads(self.selectors_text.get("1.0", "end"))
            steps = json.loads(self.steps_text.get("1.0", "end"))
        except json.JSONDecodeError as exc:
            messagebox.showerror("Site", f"Invalid JSON: {exc}")
            return
        data["selectors"] = selectors
        data["navigation_steps"] = steps
        try:
            filename = save_site(data)
        except ValueError as exc:
            messagebox.showerror("Site", str(exc))
            return
        old_name = self.current_name
        self.current_name = data["site"]
        if old_name and old_name != self.current_name:
            for proj in database.get_site_projects(old_name):
                database.remove_site_from_project(old_name, proj)
                database.assign_site_to_project(self.current_name, proj)
        self._load_sites()
        self._refresh_list()
        self.tree.selection_set(filename)
        if self.on_update:
            self.on_update()

    # ------------------------------------------------------------------
    # UI setup
    def _build_widgets(self) -> None:
        left = ttk.Frame(self)
        left.pack(side="left", fill="y")

        cols = ("name", "category", "projects", "login", "captcha")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", height=12)
        headings = {
            "name": "Site",
            "category": "Category",
            "projects": "Projects",
            "login": "Login",
            "captcha": "Captcha",
        }
        for col in cols:
            self.tree.heading(col, text=headings[col])
            width = 150 if col == "projects" else 120
            self.tree.column(col, width=width)
        self.tree.pack(fill="y", expand=True)
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self._load_selected())

        btns = ttk.Frame(left)
        btns.pack(fill="x", pady=4)
        ttk.Button(btns, text="New Site", command=self._new_site).pack(side="left")
        ttk.Button(btns, text="Delete", command=self._delete_site).pack(side="left", padx=4)
        ttk.Button(btns, text="Import", command=self._import_site).pack(side="left")
        ttk.Button(btns, text="Export", command=self._export_site).pack(side="left", padx=4)
        ttk.Button(btns, text="Map Fields", command=self._guided_mapper).pack(side="left")
        ttk.Button(btns, text="Assign to Project", command=self._assign_to_project).pack(side="left", padx=4)
        ttk.Button(btns, text="Unassign", command=self._unassign_from_project).pack(side="left")

        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=5)

        form = ttk.Frame(right)
        form.pack(fill="x")
        ttk.Label(form, text="Name").grid(row=0, column=0, sticky="w")
        self.name_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.name_var).grid(row=0, column=1, sticky="ew")
        ttk.Label(form, text="Category").grid(row=1, column=0, sticky="w")
        self.category_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.category_var).grid(row=1, column=1, sticky="ew")
        ttk.Label(form, text="URL").grid(row=2, column=0, sticky="w")
        self.url_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.url_var).grid(row=2, column=1, sticky="ew")
        ttk.Label(form, text="Captcha").grid(row=3, column=0, sticky="w")
        self.captcha_var = tk.StringVar(value=CAPTCHA_OPTIONS[0])
        ttk.Combobox(form, values=CAPTCHA_OPTIONS, textvariable=self.captcha_var, state="readonly").grid(row=3, column=1, sticky="ew")
        self.login_var = tk.BooleanVar()
        ttk.Checkbutton(form, text="Requires Login", variable=self.login_var).grid(row=4, column=1, sticky="w")
        self.geo_var = tk.BooleanVar()
        ttk.Checkbutton(form, text="Geolocation Spoofing", variable=self.geo_var).grid(row=5, column=1, sticky="w")
        form.columnconfigure(1, weight=1)

        ttk.Label(right, text="Selectors").pack(anchor="w")
        self.selectors_text = scrolledtext.ScrolledText(right, height=6)
        self.selectors_text.pack(fill="both", expand=True)
        ttk.Label(right, text="Navigation Steps").pack(anchor="w")
        self.steps_text = scrolledtext.ScrolledText(right, height=6)
        self.steps_text.pack(fill="both", expand=True)

        action = ttk.Frame(right)
        action.pack(fill="x", pady=4)
        ttk.Button(action, text="Load from File", command=self._load_from_file).pack(side="left")
        ttk.Button(action, text="Save Site", command=self._save_current).pack(side="left", padx=4)

    # ------------------------------------------------------------------
    # List operations
    def _refresh_list(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        for entry in self.sites:
            self.tree.insert(
                "",
                "end",
                iid=entry["filename"],
                values=(
                    entry.get("name"),
                    entry.get("category", ""),
                    ", ".join(entry.get("projects", [])),
                    "yes" if entry.get("requires_login") else "no",
                    entry.get("captcha", ""),
                ),
            )

    def _load_selected(self) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        fname = sel[0]
        data = get_site(Path(fname).stem)
        self.current_name = data.get("site")
        self.name_var.set(data.get("site", ""))
        self.category_var.set(data.get("category", ""))
        self.url_var.set(data.get("url", ""))
        self.captcha_var.set(data.get("captcha", CAPTCHA_OPTIONS[0]))
        self.login_var.set(bool(data.get("requires_login", False)))
        self.geo_var.set(bool(data.get("geolocation_spoofing", False)))
        self.selectors_text.delete("1.0", "end")
        self.selectors_text.insert("end", json.dumps(data.get("selectors", {}), indent=2))
        self.steps_text.delete("1.0", "end")
        self.steps_text.insert("end", json.dumps(data.get("navigation_steps", []), indent=2))

    def _new_site(self) -> None:
        self.current_name = None
        self.name_var.set("")
        self.category_var.set("")
        self.url_var.set("")
        self.captcha_var.set(CAPTCHA_OPTIONS[0])
        self.login_var.set(False)
        self.geo_var.set(False)
        self.selectors_text.delete("1.0", "end")
        self.steps_text.delete("1.0", "end")

    def _delete_site(self) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        if not messagebox.askyesno("Delete", "Delete selected site?"):
            return
        site_name = self.tree.item(sel[0])["values"][0]
        for proj in database.get_site_projects(site_name):
            database.remove_site_from_project(site_name, proj)
        delete_site(sel[0])
        self._load_sites()
        self._refresh_list()
        self._new_site()
        if self.on_update:
            self.on_update()

    def _assign_to_project(self) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        site_name = self.tree.item(sel[0])["values"][0]
        projects = project_hub.list_projects()
        if not projects:
            messagebox.showinfo("Projects", "No projects available.")
            return
        dialog = tk.Toplevel(self)
        dialog.title("Assign to Project")
        ttk.Label(dialog, text="Project:").pack(anchor="w", padx=10, pady=10)
        proj_var = tk.StringVar(value=projects[0])
        ttk.Combobox(dialog, values=projects, textvariable=proj_var, state="readonly").pack(padx=10, pady=5)

        def save() -> None:
            database.assign_site_to_project(site_name, proj_var.get())
            dialog.destroy()
            self._load_sites()
            self._refresh_list()
            if self.on_update:
                self.on_update()

        ttk.Button(dialog, text="Assign", command=save).pack(pady=10)

    def _unassign_from_project(self) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        site_name = self.tree.item(sel[0])["values"][0]
        projects = database.get_site_projects(site_name)
        if not projects:
            messagebox.showinfo("Unassign", "Site not assigned to any project.")
            return
        dialog = tk.Toplevel(self)
        dialog.title("Unassign from Project")
        ttk.Label(dialog, text="Project:").pack(anchor="w", padx=10, pady=10)
        proj_var = tk.StringVar(value=projects[0])
        ttk.Combobox(dialog, values=projects, textvariable=proj_var, state="readonly").pack(padx=10, pady=5)

        def remove() -> None:
            database.remove_site_from_project(site_name, proj_var.get())
            dialog.destroy()
            self._load_sites()
            self._refresh_list()
            if self.on_update:
                self.on_update()

        ttk.Button(dialog, text="Remove", command=remove).pack(pady=10)

    def _import_site(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            import_site(Path(path))
            self._load_sites()
            self._refresh_list()
            if self.on_update:
                self.on_update()
        except Exception as exc:
            messagebox.showerror("Import", str(exc))

    def _export_site(self) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        path = filedialog.asksaveasfilename(defaultextension=".json")
        if not path:
            return
        export_site(Path(sel[0]).stem, Path(path))

    def _guided_mapper(self) -> None:
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("Guided Mapper", "Enter a site URL first")
            return
        mapping = run_guided_mapper(self.winfo_toplevel(), url)
        if not mapping:
            return
        self.selectors_text.delete("1.0", "end")
        self.selectors_text.insert("end", json.dumps(mapping, indent=2))
        messagebox.showinfo("Guided Mapper", f"Captured {len(mapping)} fields")

    def _load_from_file(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.name_var.set(data.get("site", ""))
            self.category_var.set(data.get("category", ""))
            self.url_var.set(data.get("url", ""))
            self.captcha_var.set(data.get("captcha", CAPTCHA_OPTIONS[0]))
            self.login_var.set(bool(data.get("requires_login", False)))
            self.geo_var.set(bool(data.get("geolocation_spoofing", False)))
            self.selectors_text.delete("1.0", "end")
            self.selectors_text.insert("end", json.dumps(data.get("selectors", {}), indent=2))
            self.steps_text.delete("1.0", "end")
            self.steps_text.insert("end", json.dumps(data.get("navigation_steps", []), indent=2))
        except Exception as exc:
            messagebox.showerror("Load", str(exc))
