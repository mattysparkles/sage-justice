import json
import random
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk, filedialog, scrolledtext

import requests

TEMPLATES_PATH = Path("config/templates.json")
COMMUNITY_INDEX_URL = (
    "https://raw.githubusercontent.com/swe-agent/community-templates/main/templates.json"
)
COMMUNITY_UPLOAD_URL = (
    "https://swe-agent-community-templates.fly.dev/upload"
)
SITE_CATEGORIES = [
    "Auto Services",
    "Food",
    "Retail",
    "Professional Services",
]


class TemplateManagerFrame(ttk.Frame):
    """GUI for creating and managing review templates."""

    def __init__(self, master, *, on_update=None):
        super().__init__(master)
        self.on_update = on_update
        self.templates: list[dict] = []
        self._load_templates()
        self._build_widgets()
        self._refresh_list()

    # ------------------------------------------------------------------
    # Data helpers
    def _load_templates(self) -> None:
        try:
            with open(TEMPLATES_PATH, "r", encoding="utf-8") as f:
                self.templates = json.load(f)
        except FileNotFoundError:
            self.templates = []

    def _save_templates(self) -> None:
        with open(TEMPLATES_PATH, "w", encoding="utf-8") as f:
            json.dump(self.templates, f, indent=2)
        if self.on_update:
            self.on_update()

    def _next_id(self) -> str:
        ids = [int(t["id"].split("-")[-1]) for t in self.templates if t.get("id", "").startswith("tmpl-")]
        nxt = max(ids, default=0) + 1
        return f"tmpl-{nxt:03d}"

    # ------------------------------------------------------------------
    # UI setup
    def _build_widgets(self) -> None:
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)
        local = ttk.Frame(notebook)
        community = ttk.Frame(notebook)
        notebook.add(local, text="Local")
        notebook.add(community, text="Community")
        self._build_local_tab(local)
        self._build_community_tab(community)

    def _build_local_tab(self, parent) -> None:
        left = ttk.Frame(parent)
        left.pack(side="left", fill="y")

        search_frame = ttk.Frame(left)
        search_frame.pack(fill="x", pady=2)
        ttk.Label(search_frame, text="Filter:").pack(side="left")
        self.filter_var = tk.StringVar()
        ent = ttk.Entry(search_frame, textvariable=self.filter_var)
        ent.pack(side="left", fill="x", expand=True)
        ent.bind("<KeyRelease>", lambda _e: self._refresh_list())

        cols = ("name", "category", "count")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", height=12)
        headings = {"name": "Name", "category": "Category", "count": "Reviews"}
        for col in cols:
            self.tree.heading(col, text=headings[col], command=lambda c=col: self._sort_by(c, False))
            self.tree.column(col, width=120)
        self.tree.pack(fill="y", expand=True)
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self._load_selected())

        btns = ttk.Frame(left)
        btns.pack(fill="x", pady=4)
        ttk.Button(btns, text="New", command=self._new_template).pack(side="left")
        ttk.Button(btns, text="Duplicate", command=self._duplicate_template).pack(side="left", padx=4)
        ttk.Button(btns, text="Delete", command=self._delete_template).pack(side="left")
        ttk.Button(btns, text="Import", command=self._import_template).pack(side="left", padx=4)
        ttk.Button(btns, text="Export", command=self._export_template).pack(side="left")

        right = ttk.Frame(parent)
        right.pack(side="left", fill="both", expand=True, padx=5)

        form = ttk.Frame(right)
        form.pack(fill="x", pady=2)
        ttk.Label(form, text="Name").grid(row=0, column=0, sticky="w")
        self.name_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.name_var).grid(row=0, column=1, sticky="ew")
        ttk.Label(form, text="Category").grid(row=1, column=0, sticky="w")
        self.category_var = tk.StringVar()
        ttk.Combobox(form, values=SITE_CATEGORIES, textvariable=self.category_var, state="readonly").grid(row=1, column=1, sticky="ew")
        form.columnconfigure(1, weight=1)

        tone = ttk.LabelFrame(right, text="Tone")
        tone.pack(fill="x", pady=2)
        self.formality_var = tk.DoubleVar()
        self.positivity_var = tk.DoubleVar()
        self.emotion_var = tk.DoubleVar()
        self._make_slider(tone, "Formality", self.formality_var, 0)
        self._make_slider(tone, "Positivity", self.positivity_var, 1)
        self._make_slider(tone, "Emotion", self.emotion_var, 2)
        tone.columnconfigure(1, weight=1)

        blocks_frame = ttk.LabelFrame(right, text="Review Blocks")
        blocks_frame.pack(fill="both", expand=True, pady=2)
        self.block_list = tk.Listbox(blocks_frame)
        self.block_list.pack(side="left", fill="both", expand=True)
        blk_btns = ttk.Frame(blocks_frame)
        blk_btns.pack(side="left", fill="y")
        ttk.Button(blk_btns, text="Add", command=self._add_block).pack(fill="x")
        ttk.Button(blk_btns, text="Remove", command=self._remove_block).pack(fill="x", pady=2)
        ttk.Button(blk_btns, text="Up", command=lambda: self._move_block(-1)).pack(fill="x")
        ttk.Button(blk_btns, text="Down", command=lambda: self._move_block(1)).pack(fill="x", pady=2)
        self.new_block_var = tk.StringVar()
        ttk.Entry(blocks_frame, textvariable=self.new_block_var).pack(fill="x", pady=2)

        action = ttk.Frame(right)
        action.pack(fill="x", pady=4)
        ttk.Button(action, text="Save Template", command=self._save_template).pack(side="left")
        ttk.Button(action, text="Generate Preview", command=self._generate_preview).pack(side="left", padx=4)

        self.preview_box = scrolledtext.ScrolledText(right, height=8, state="disabled")
        self.preview_box.pack(fill="both", expand=True, pady=4)

    def _build_community_tab(self, parent) -> None:
        top = ttk.Frame(parent)
        top.pack(fill="both", expand=True)
        cols = ("name", "category")
        self.community_tree = ttk.Treeview(top, columns=cols, show="headings", height=12)
        self.community_tree.heading("name", text="Name")
        self.community_tree.heading("category", text="Category")
        self.community_tree.column("name", width=160)
        self.community_tree.column("category", width=120)
        self.community_tree.pack(fill="both", expand=True)

        btns = ttk.Frame(parent)
        btns.pack(fill="x", pady=4)
        ttk.Button(btns, text="Refresh", command=self._fetch_community_templates).pack(
            side="left"
        )
        ttk.Button(btns, text="Download", command=self._download_community_template).pack(
            side="left", padx=4
        )
        ttk.Button(btns, text="Upload Current", command=self._upload_current_template).pack(
            side="left"
        )

        self.community_templates: list[dict] = []
        self._fetch_community_templates()

    def _make_slider(self, frame, text, var, row):
        ttk.Label(frame, text=text).grid(row=row, column=0, sticky="w")
        ttk.Scale(frame, from_=0.0, to=1.0, orient="horizontal", variable=var).grid(row=row, column=1, sticky="ew")

    # ------------------------------------------------------------------
    # Template list operations
    def _refresh_list(self) -> None:
        flt = self.filter_var.get().lower()
        for item in self.tree.get_children():
            self.tree.delete(item)
        for tmpl in self.templates:
            tid = tmpl.get("id")
            if not tid:
                # Skip entries that don't conform to the review template schema
                continue
            if flt and flt not in tmpl.get("name", "").lower():
                continue
            self.tree.insert(
                "",
                "end",
                iid=tid,
                values=(tmpl.get("name", ""), tmpl.get("category", ""), len(tmpl.get("review_blocks", []))),
            )

    def _sort_by(self, col: str, reverse: bool) -> None:
        data = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        data.sort(reverse=reverse)
        for idx, (_, k) in enumerate(data):
            self.tree.move(k, "", idx)
        self.tree.heading(col, command=lambda: self._sort_by(col, not reverse))

    def _load_selected(self) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        tmpl = next((t for t in self.templates if t.get("id") == sel[0]), None)
        if not tmpl:
            return
        self.current_template = tmpl
        self.name_var.set(tmpl.get("name", ""))
        self.category_var.set(tmpl.get("category", SITE_CATEGORIES[0]))
        tone = tmpl.get("tone", {})
        self.formality_var.set(tone.get("formality", 0.0))
        self.positivity_var.set(tone.get("positivity", 0.0))
        self.emotion_var.set(tone.get("emotion", 0.0))
        self.block_list.delete(0, tk.END)
        for blk in tmpl.get("review_blocks", []):
            self.block_list.insert(tk.END, blk)

    def _new_template(self) -> None:
        self.current_template = None
        self.name_var.set("")
        self.category_var.set(SITE_CATEGORIES[0])
        self.formality_var.set(0.0)
        self.positivity_var.set(0.0)
        self.emotion_var.set(0.0)
        self.block_list.delete(0, tk.END)

    def _duplicate_template(self) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        tmpl = next((t for t in self.templates if t.get("id") == sel[0]), None)
        if not tmpl:
            return
        new_tmpl = json.loads(json.dumps(tmpl))
        new_tmpl["id"] = self._next_id()
        new_tmpl["name"] += " Copy"
        self.templates.append(new_tmpl)
        self._save_templates()
        self._refresh_list()

    def _delete_template(self) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        self.templates = [t for t in self.templates if t.get("id") != sel[0]]
        self._save_templates()
        self._refresh_list()
        self._new_template()

    def _import_template(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                tmpl = json.load(f)
            tmpl["id"] = self._next_id()
            self.templates.append(tmpl)
            self._save_templates()
            self._refresh_list()
        except Exception as exc:
            messagebox.showerror("Import", str(exc))

    def _export_template(self) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        tmpl = next((t for t in self.templates if t.get("id") == sel[0]), None)
        if not tmpl:
            return
        path = filedialog.asksaveasfilename(defaultextension=".json")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            json.dump(tmpl, f, indent=2)

    # ------------------------------------------------------------------
    # Community operations
    def _fetch_community_templates(self) -> None:
        try:
            resp = requests.get(COMMUNITY_INDEX_URL, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            self.community_templates = data if isinstance(data, list) else []
        except Exception as exc:
            messagebox.showerror("Community", f"Failed to fetch templates: {exc}")
            self.community_templates = []
        self._refresh_community_list()

    def _refresh_community_list(self) -> None:
        if not hasattr(self, "community_tree"):
            return
        for item in self.community_tree.get_children():
            self.community_tree.delete(item)
        for tmpl in self.community_templates:
            self.community_tree.insert(
                "",
                "end",
                iid=tmpl.get("id", ""),
                values=(tmpl.get("name", ""), tmpl.get("category", "")),
            )

    def _download_community_template(self) -> None:
        sel = self.community_tree.selection()
        if not sel:
            return
        tmpl = next((t for t in self.community_templates if t.get("id") == sel[0]), None)
        if not tmpl:
            return
        url = tmpl.get("url")
        if not url:
            messagebox.showerror("Download", "Template URL missing")
            return
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            messagebox.showerror("Download", str(exc))
            return
        data["id"] = self._next_id()
        self.templates.append(data)
        self._save_templates()
        self._refresh_list()
        messagebox.showinfo("Community", f"Imported template '{data.get('name', '')}'")

    def _upload_current_template(self) -> None:
        tmpl = getattr(self, "current_template", None)
        if not tmpl:
            messagebox.showwarning("Upload", "No template selected")
            return
        try:
            resp = requests.post(COMMUNITY_UPLOAD_URL, json=tmpl, timeout=10)
            resp.raise_for_status()
            messagebox.showinfo("Upload", "Template uploaded")
        except Exception as exc:
            messagebox.showerror("Upload", str(exc))

    # ------------------------------------------------------------------
    # Block operations
    def _add_block(self) -> None:
        text = self.new_block_var.get().strip()
        if text:
            self.block_list.insert(tk.END, text)
            self.new_block_var.set("")

    def _remove_block(self) -> None:
        sel = self.block_list.curselection()
        if sel:
            self.block_list.delete(sel[0])

    def _move_block(self, direction: int) -> None:
        sel = self.block_list.curselection()
        if not sel:
            return
        idx = sel[0]
        new_idx = idx + direction
        if new_idx < 0 or new_idx >= self.block_list.size():
            return
        text = self.block_list.get(idx)
        self.block_list.delete(idx)
        self.block_list.insert(new_idx, text)
        self.block_list.selection_set(new_idx)

    # ------------------------------------------------------------------
    def _save_template(self) -> None:
        data = {
            "id": self.current_template.get("id") if getattr(self, "current_template", None) else self._next_id(),
            "name": self.name_var.get().strip(),
            "category": self.category_var.get(),
            "tone": {
                "formality": self.formality_var.get(),
                "positivity": self.positivity_var.get(),
                "emotion": self.emotion_var.get(),
            },
            "review_blocks": list(self.block_list.get(0, tk.END)),
        }
        if not data["name"]:
            messagebox.showwarning("Template", "Name required")
            return
        if getattr(self, "current_template", None):
            for idx, tmpl in enumerate(self.templates):
                if tmpl.get("id") == self.current_template["id"]:
                    self.templates[idx] = data
                    break
        else:
            self.templates.append(data)
        self._save_templates()
        self._refresh_list()
        self.tree.selection_set(data["id"])

    def _generate_preview(self) -> None:
        sel = self.tree.selection()
        if not sel:
            tmpl = {
                "review_blocks": list(self.block_list.get(0, tk.END)),
                "tone": {
                    "formality": self.formality_var.get(),
                    "positivity": self.positivity_var.get(),
                    "emotion": self.emotion_var.get(),
                },
            }
        else:
            tmpl = next((t for t in self.templates if t.get("id") == sel[0]), None)
        if not tmpl:
            return
        blocks = tmpl.get("review_blocks", [])
        if not blocks:
            return
        blocks = blocks[:]
        random.shuffle(blocks)
        text = " ".join(blocks)
        self.preview_box.configure(state="normal")
        self.preview_box.delete("1.0", "end")
        self.preview_box.insert("1.0", text)
        self.preview_box.configure(state="disabled")
        return text
