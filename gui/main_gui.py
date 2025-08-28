"""Tkinter dashboard wiring multiple Sage Justice modules."""

from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox

try:
    from site_manager_gui import SiteManagerFrame
except Exception:
    from gui.site_manager_gui import SiteManagerFrame

from core.style_generator import generate_styled_reviews, tones
from core.async_queue import AsyncReviewQueue
from core.proxy_manager import get_random_proxy
from core.account_manager import get_random_account
from core.report_generator import generate_report
from core.exporter import export_reviews
from core.logger import logger

# Predefined categories and available resources for project management
SITE_CATEGORIES = [
    "Auto Services",
    "Food",
    "Retail",
    "Professional Services",
]

LOG_PATH = "output/post_log.csv"


class MainGUI:
    """Main Guardian Deck interface."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Sage Justice – Guardian Deck")

        self.queue = AsyncReviewQueue()
        self.queue.start()

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True)

        self._build_projects_tab()
        self._build_schedule_tab()
        self._build_logs_tab()
        self._build_template_tab()
        self._build_sites_tab()
        self._build_reports_tab()
        self._build_settings_tab()

        self.status_var = tk.StringVar(value="Ready")
        tk.Label(root, textvariable=self.status_var, relief="sunken", anchor="w").pack(
            fill="x", side="bottom"
        )

        self._refresh_queue_view()
        self._refresh_logs()

    # ------------------------------------------------------------------
    # Projects tab
    def _build_projects_tab(self) -> None:
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Projects")

        self.projects = self._load_projects()

        cols = ("name", "created", "sites", "templates", "reviews", "proxies", "accounts")
        self.project_tree = ttk.Treeview(frame, columns=cols, show="headings", height=8)
        headings = {
            "name": "Project Name",
            "created": "Created",
            "sites": "Sites",
            "templates": "Templates",
            "reviews": "Reviews",
            "proxies": "Proxies",
            "accounts": "Accounts",
        }
        for col in cols:
            self.project_tree.heading(
                col,
                text=headings[col],
                command=lambda c=col: self._sort_projects_tree(c, False),
            )
            self.project_tree.column(col, width=100)
        self.project_tree.pack(fill="both", expand=True)
        self.project_tree.bind("<<TreeviewSelect>>", lambda _e: self._on_project_select())

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x", pady=4)
        ttk.Button(btn_frame, text="New Project", command=self._new_project).pack(side="left")
        ttk.Button(btn_frame, text="Edit Selected", command=self._edit_project).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Delete", command=self._delete_project).pack(side="left")

        res_nb = ttk.Notebook(frame)
        res_nb.pack(fill="both", expand=True)
        self.resources_nb = res_nb

        self.site_list = tk.Listbox(res_nb, selectmode="multiple")
        res_nb.add(self.site_list, text="Sites")
        self.available_sites = self._load_sites()
        for s in self.available_sites:
            self.site_list.insert("end", s.get("name"))

        self.review_list = tk.Listbox(res_nb, selectmode="multiple")
        res_nb.add(self.review_list, text="Reviews")

        self.available_templates = self._load_templates()
        self.template_list = tk.Listbox(res_nb, selectmode="multiple")
        res_nb.add(self.template_list, text="Templates")
        for tmpl in self.available_templates:
            self.template_list.insert("end", f"{tmpl['id']}:{tmpl.get('name', '')}")

        self.available_accounts = self._load_accounts()
        self.account_list = tk.Listbox(res_nb, selectmode="multiple")
        res_nb.add(self.account_list, text="Accounts")
        for idx, acc in enumerate(self.available_accounts):
            self.account_list.insert("end", f"acct-{idx}:{acc.get('username', '')}")

        self.available_proxies = self._load_proxies()
        self.proxy_list = tk.Listbox(res_nb, selectmode="multiple")
        res_nb.add(self.proxy_list, text="Proxies")
        for idx, _p in enumerate(self.available_proxies):
            self.proxy_list.insert("end", f"proxy-{idx}")

        ttk.Button(frame, text="Save Changes", command=self._save_project_resources).pack(pady=4)

        self._refresh_projects_view()

    def _load_projects(self) -> list:
        try:
            with open("config/projects.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return []

    def _save_projects(self) -> None:
        with open("config/projects.json", "w", encoding="utf-8") as f:
            json.dump(self.projects, f, indent=2)

    def _load_accounts(self) -> list:
        try:
            with open("accounts/accounts.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return []

    def _load_proxies(self) -> list:
        try:
            with open("config/proxies.txt", "r", encoding="utf-8") as f:
                return [l.strip() for l in f if l.strip() and not l.startswith("#")]
        except FileNotFoundError:
            return []

    def _load_templates(self) -> list:
        try:
            with open("config/templates.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return []

    def _load_sites(self) -> list:
        try:
            from core.site_registry import get_sites
            return get_sites()
        except Exception:
            return []

    def _refresh_site_list(self) -> None:
        if not hasattr(self, "site_list"):
            return
        self.available_sites = self._load_sites()
        self.site_list.delete(0, tk.END)
        for s in self.available_sites:
            self.site_list.insert(tk.END, s.get("name"))



    def _refresh_projects_view(self) -> None:
        tree = getattr(self, "project_tree", None)
        if not tree:
            return
        for item in tree.get_children():
            tree.delete(item)
        for proj in getattr(self, "projects", []):
            tree.insert(
                "",
                "end",
                iid=proj["id"],
                values=(
                    proj.get("name", ""),
                    proj.get("created", ""),
                    len(proj.get("assigned_sites", [])),
                    len(proj.get("assigned_templates", [])),
                    len(proj.get("assigned_reviews", [])),
                    len(proj.get("assigned_proxies", [])),
                    len(proj.get("assigned_accounts", [])),
                ),
            )

    def _get_selected_project(self) -> dict | None:
        sel = self.project_tree.selection()
        if not sel:
            return None
        pid = sel[0]
        for proj in self.projects:
            if proj["id"] == pid:
                return proj
        return None

    def _on_project_select(self) -> None:
        proj = self._get_selected_project()
        if not proj:
            return
        self.selected_project = proj

        def set_selection(listbox: tk.Listbox, total: int, names: list, selected: list) -> None:
            listbox.selection_clear(0, "end")
            for idx in range(total):
                ident = names[idx]
                if ident in selected:
                    listbox.selection_set(idx)

        set_selection(self.site_list, len(self.available_sites), [s["name"] for s in self.available_sites], proj.get("assigned_sites", []))
        set_selection(self.review_list, 0, [], proj.get("assigned_reviews", []))
        template_ids = [t["id"] for t in self.available_templates]
        set_selection(
            self.template_list,
            len(template_ids),
            template_ids,
            proj.get("assigned_templates", []),
        )
        account_ids = [f"acct-{i}" for i in range(len(self.available_accounts))]
        set_selection(self.account_list, len(account_ids), account_ids, proj.get("assigned_accounts", []))
        proxy_ids = [f"proxy-{i}" for i in range(len(self.available_proxies))]
        set_selection(self.proxy_list, len(proxy_ids), proxy_ids, proj.get("assigned_proxies", []))

    def _new_project(self) -> None:
        data = self._project_dialog()
        if not data:
            return
        new_id = f"proj-{len(self.projects) + 1:03d}"
        project = {
            "id": new_id,
            "name": data["name"],
            "description": data["description"],
            "category": data["category"],
            "created": datetime.utcnow().isoformat() + "Z",
            "assigned_sites": [],
            "default_site": data.get("default_site"),
            "assigned_reviews": [],
            "assigned_accounts": [],
            "assigned_proxies": [],
            "assigned_templates": [],
            "scheduled_tasks": [],
            "template_overrides": {},
            "last_run": None,
        }
        self.projects.append(project)
        self._save_projects()
        self._refresh_projects_view()

    def _edit_project(self) -> None:
        proj = self._get_selected_project()
        if not proj:
            messagebox.showwarning("Project", "Select a project")
            return
        data = self._project_dialog(proj)
        if not data:
            return
        proj.update(data)
        self._save_projects()
        self._refresh_projects_view()

    def _delete_project(self) -> None:
        proj = self._get_selected_project()
        if not proj:
            messagebox.showwarning("Project", "Select a project")
            return
        if not messagebox.askyesno("Delete", "Delete selected project?"):
            return
        self.projects = [p for p in self.projects if p["id"] != proj["id"]]
        self._save_projects()
        self._refresh_projects_view()

    def _save_project_resources(self) -> None:
        proj = getattr(self, "selected_project", None)
        if not proj:
            messagebox.showwarning("Project", "Select a project first")
            return
        proj["assigned_sites"] = [self.available_sites[i]["name"] for i in self.site_list.curselection()]
        proj["assigned_reviews"] = []
        proj["assigned_templates"] = [
            self.available_templates[i]["id"] for i in self.template_list.curselection()
        ]
        proj["assigned_accounts"] = [f"acct-{i}" for i in self.account_list.curselection()]
        proj["assigned_proxies"] = [f"proxy-{i}" for i in self.proxy_list.curselection()]
        self._save_projects()
        self._refresh_projects_view()

    def _project_dialog(self, project: dict | None = None) -> dict | None:
        top = tk.Toplevel(self.root)
        top.title("Project" if project else "New Project")
        tk.Label(top, text="Name").grid(row=0, column=0, sticky="w")
        name_var = tk.StringVar(value=project.get("name") if project else "")
        tk.Entry(top, textvariable=name_var).grid(row=0, column=1, sticky="ew")
        tk.Label(top, text="Description").grid(row=1, column=0, sticky="w")
        desc_var = tk.StringVar(value=project.get("description") if project else "")
        tk.Entry(top, textvariable=desc_var).grid(row=1, column=1, sticky="ew")
        tk.Label(top, text="Category").grid(row=2, column=0, sticky="w")
        cat_var = tk.StringVar(value=project.get("category") if project else SITE_CATEGORIES[0])
        ttk.Combobox(top, values=SITE_CATEGORIES, textvariable=cat_var, state="readonly").grid(
            row=2, column=1, sticky="ew"
        )
        tk.Label(top, text="Default Site").grid(row=3, column=0, sticky="w")
        site_names = [s.get("name") for s in self.available_sites]
        site_var = tk.StringVar(value=project.get("default_site") if project else (site_names[0] if site_names else ""))
        ttk.Combobox(top, values=site_names, textvariable=site_var, state="readonly").grid(row=3, column=1, sticky="ew")

        result: dict = {}

        def on_ok() -> None:
            if not name_var.get().strip():
                messagebox.showwarning("Project", "Name required")
                return
            result.update(
                name=name_var.get().strip(),
                description=desc_var.get().strip(),
                category=cat_var.get(),
                default_site=site_var.get(),
            )
            top.destroy()

        ttk.Button(top, text="Save", command=on_ok).grid(row=4, column=0, pady=4)
        ttk.Button(top, text="Cancel", command=top.destroy).grid(row=4, column=1, pady=4)
        top.columnconfigure(1, weight=1)
        top.grab_set()
        top.wait_window()
        return result if result else None

    def _sort_projects_tree(self, col: str, reverse: bool) -> None:
        data = [(self.project_tree.set(k, col), k) for k in self.project_tree.get_children("")]
        data.sort(reverse=reverse)
        for idx, (_val, k) in enumerate(data):
            self.project_tree.move(k, "", idx)
        self.project_tree.heading(col, command=lambda: self._sort_projects_tree(col, not reverse))

    # ------------------------------------------------------------------
    # Schedule tab
    def _build_schedule_tab(self) -> None:
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Schedule")

        tk.Label(frame, text="Prompt").pack(anchor="w")
        self.prompt_entry = scrolledtext.ScrolledText(frame, height=5)
        self.prompt_entry.pack(fill="both", expand=True)

        tk.Label(frame, text="Tone").pack(anchor="w")
        tone_opts = list(tones.keys()) + ["random"]
        self.tone_var = tk.StringVar(value="professional")
        ttk.Combobox(frame, values=tone_opts, textvariable=self.tone_var, state="readonly").pack(
            fill="x"
        )

        tk.Label(frame, text="Template").pack(anchor="w")
        temp_frame = ttk.Frame(frame)
        temp_frame.pack(fill="x")
        self.template_var = tk.StringVar(value="templates/google_review.json")
        tk.Entry(temp_frame, textvariable=self.template_var).pack(side="left", fill="x", expand=True)
        ttk.Button(temp_frame, text="Browse", command=self._browse_template).pack(side="left", padx=4)

        tk.Label(frame, text="Post at (YYYY-mm-dd HH:MM)").pack(anchor="w")
        self.time_entry = tk.Entry(frame)
        self.time_entry.pack(fill="x")

        ttk.Button(frame, text="Preview Reviews", command=self._preview_reviews).pack(pady=4)
        self.preview_box = scrolledtext.ScrolledText(frame, height=8)
        self.preview_box.pack(fill="both", expand=True)

        ttk.Button(frame, text="Schedule Reviews", command=self._schedule_reviews).pack(pady=4)

        self.queue_tree = ttk.Treeview(
            frame,
            columns=("time", "template", "proxy", "account"),
            show="headings",
            height=6,
        )
        for col in ("time", "template", "proxy", "account"):
            self.queue_tree.heading(col, text=col.title())
        self.queue_tree.pack(fill="both", expand=True, pady=4)

    def _browse_template(self) -> None:
        path = filedialog.askopenfilename(initialdir="templates", filetypes=[("JSON", "*.json")])
        if path:
            self.template_var.set(path)

    def _preview_reviews(self) -> None:
        prompt = self.prompt_entry.get("1.0", "end").strip()
        if not prompt:
            messagebox.showwarning("Prompt", "Please enter a prompt")
            return
        tone = self.tone_var.get()
        reviews = generate_styled_reviews(prompt, count=3, tone=tone)
        self.preview_box.delete("1.0", "end")
        for r in reviews:
            self.preview_box.insert("end", r + "\n\n")
        self.previewed_reviews = reviews

    def _schedule_reviews(self) -> None:
        reviews = getattr(self, "previewed_reviews", [])
        if not reviews:
            messagebox.showwarning("Reviews", "Generate reviews first")
            return
        template = self.template_var.get()
        time_str = self.time_entry.get().strip()
        if time_str:
            try:
                ts = datetime.strptime(time_str, "%Y-%m-%d %H:%M").timestamp()
            except ValueError:
                messagebox.showerror("Time", "Invalid format")
                return
        else:
            ts = time.time()

        for review in reviews:
            proxy = get_random_proxy()
            account = get_random_account()
            self.queue.add(review, template, ts, proxy=proxy, account=account)
        self.status_var.set(f"Scheduled {len(reviews)} review(s)")
        self._refresh_queue_view()

    def _refresh_queue_view(self) -> None:
        for item in self.queue_tree.get_children():
            self.queue_tree.delete(item)
        for ts, _review, template, proxy, account in list(self.queue.queue.queue):
            acc = account.get("username") if isinstance(account, dict) else ""
            self.queue_tree.insert(
                "",
                "end",
                values=(
                    datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M"),
                    os.path.basename(template),
                    proxy or "",
                    acc,
                ),
            )
        self.root.after(5000, self._refresh_queue_view)

    # ------------------------------------------------------------------
    # Logs tab
    def _build_logs_tab(self) -> None:
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Logs")

        self.log_text = scrolledtext.ScrolledText(frame, height=20)
        self.log_text.pack(fill="both", expand=True)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x")
        ttk.Button(btn_frame, text="Refresh", command=self._refresh_logs).pack(side="left")
        ttk.Button(btn_frame, text="Export", command=self._export_logs).pack(side="left", padx=4)

    def _refresh_logs(self) -> None:
        path = LOG_PATH if os.path.exists(LOG_PATH) else "logs/app.log"
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            content = ""
        self.log_text.delete("1.0", "end")
        self.log_text.insert("end", content)
        self.root.after(30000, self._refresh_logs)

    def _export_logs(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".txt")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.log_text.get("1.0", "end"))


    def _build_sites_tab(self) -> None:
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Sites")
        mgr = SiteManagerFrame(frame, on_update=self._refresh_site_list)
        mgr.pack(fill="both", expand=True)

    # ------------------------------------------------------------------
    # Reports & Export tab
    def _build_reports_tab(self) -> None:
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Reports & Export")

        ttk.Label(frame, text="Start Date (YYYY-MM-DD)").grid(row=0, column=0, sticky="w")
        self.report_start_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.report_start_var, width=15).grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(frame, text="End Date (YYYY-MM-DD)").grid(row=1, column=0, sticky="w")
        self.report_end_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.report_end_var, width=15).grid(row=1, column=1, padx=5, pady=2)

        fmt_frame = ttk.Frame(frame)
        fmt_frame.grid(row=2, column=0, columnspan=2, pady=4, sticky="w")
        self.export_csv_var = tk.BooleanVar(value=True)
        self.export_json_var = tk.BooleanVar(value=False)
        self.export_pdf_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(fmt_frame, text="CSV", variable=self.export_csv_var).pack(side="left")
        ttk.Checkbutton(fmt_frame, text="JSON", variable=self.export_json_var).pack(side="left", padx=4)
        ttk.Checkbutton(fmt_frame, text="PDF", variable=self.export_pdf_var).pack(side="left")

        ttk.Button(frame, text="Generate Report", command=self._generate_report).grid(row=3, column=0, columnspan=2, pady=4)
        self.report_msg = tk.StringVar()
        ttk.Label(frame, textvariable=self.report_msg).grid(row=4, column=0, columnspan=2, sticky="w")
        frame.columnconfigure(1, weight=1)

    def _generate_report(self) -> None:
        start_text = self.report_start_var.get().strip()
        end_text = self.report_end_var.get().strip()
        try:
            start_dt = datetime.fromisoformat(start_text) if start_text else None
            end_dt = datetime.fromisoformat(end_text) if end_text else None
        except ValueError:
            messagebox.showerror("Reports", "Dates must be in YYYY-MM-DD format")
            return

        formats: list[str] = []
        if self.export_csv_var.get():
            formats.append("csv")
        if self.export_json_var.get():
            formats.append("json")
        if self.export_pdf_var.get():
            formats.append("pdf")

        try:
            summary = generate_report(start_dt, end_dt)
            paths = export_reviews(start_dt, end_dt, formats)
            msg = f"Report generated: {', '.join(p.name for p in paths)}"
            self.report_msg.set(msg)
            self.status_var.set(msg)
            logger.info("Report summary: %s", summary)
        except Exception as exc:
            logger.exception("Failed to generate report: %s", exc)
            messagebox.showerror("Reports", str(exc))

    # ------------------------------------------------------------------
    # Template tab
    def _build_template_tab(self) -> None:
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Templates")

        path_frame = ttk.Frame(frame)
        path_frame.pack(fill="x")
        self.template_edit_path = tk.StringVar()
        ttk.Entry(path_frame, textvariable=self.template_edit_path).pack(side="left", fill="x", expand=True)
        ttk.Button(path_frame, text="Load", command=self._load_template).pack(side="left", padx=4)
        ttk.Button(path_frame, text="Save", command=self._save_template).pack(side="left")

        self.template_text = scrolledtext.ScrolledText(frame, height=20)
        self.template_text.pack(fill="both", expand=True)

        action = ttk.Frame(frame)
        action.pack(fill="x", pady=4)
        ttk.Button(action, text="Validate", command=self._validate_template).pack(side="left")
        ttk.Button(action, text="Field Mapper", command=self._launch_field_mapper).pack(side="left", padx=4)
        ttk.Button(action, text="Auto-Detect Fields", command=self._auto_detect_fields).pack(side="left")

    def _load_template(self) -> None:
        path = filedialog.askopenfilename(initialdir="templates", filetypes=[("JSON", "*.json")])
        if path:
            self.template_edit_path.set(path)
            with open(path, "r", encoding="utf-8") as f:
                self.template_text.delete("1.0", "end")
                self.template_text.insert("end", f.read())

    def _save_template(self) -> None:
        path = self.template_edit_path.get()
        if not path:
            path = filedialog.asksaveasfilename(defaultextension=".json")
            if not path:
                return
            self.template_edit_path.set(path)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.template_text.get("1.0", "end"))

    def _validate_template(self) -> None:
        try:
            json.loads(self.template_text.get("1.0", "end"))
            messagebox.showinfo("Valid", "Template JSON is valid")
        except json.JSONDecodeError as exc:
            messagebox.showerror("Invalid", str(exc))

    def _launch_field_mapper(self) -> None:
        threading.Thread(
            target=lambda: os.system("python gui/field_mapper_gui.py"),
            daemon=True,
        ).start()

    def _auto_detect_fields(self) -> None:
        try:
            data = json.loads(self.template_text.get("1.0", "end"))
            url = data.get("url")
        except Exception:
            url = None
        if not url:
            messagebox.showwarning("Template", "Template must include 'url'")
            return

        def run() -> None:
            from selenium import webdriver
            from core.field_auto_detector import auto_detect_fields

            driver = webdriver.Chrome()
            driver.get(url)
            auto_detect_fields(driver)
            driver.quit()

        threading.Thread(target=run, daemon=True).start()

    # ------------------------------------------------------------------
    # Settings tab
    def _build_settings_tab(self) -> None:
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Settings")

        try:
            with open("config/settings.json", "r", encoding="utf-8") as f:
                self.settings = json.load(f)
        except FileNotFoundError:
            self.settings = {}

        self.api_key_var = tk.StringVar(value=self.settings.get("openai_api_key", ""))
        self.captcha_var = tk.StringVar(value=self.settings.get("captcha_api_key", ""))
        self.headless_var = tk.BooleanVar(value=self.settings.get("headless", False))
        self.test_mode_var = tk.BooleanVar(value=self.settings.get("test_mode", False))
        self.rotate_ip_var = tk.BooleanVar(value=self.settings.get("auto_rotate_ip", False))

        ttk.Label(frame, text="OpenAI Key").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.api_key_var, width=40).grid(row=0, column=1, sticky="ew")
        ttk.Label(frame, text="CAPTCHA Key").grid(row=1, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.captcha_var, width=40).grid(row=1, column=1, sticky="ew")

        ttk.Checkbutton(frame, text="Headless", variable=self.headless_var).grid(row=2, column=0, sticky="w")
        ttk.Checkbutton(frame, text="Test Mode", variable=self.test_mode_var).grid(row=2, column=1, sticky="w")
        ttk.Checkbutton(frame, text="Auto Rotate IP", variable=self.rotate_ip_var).grid(row=3, column=0, sticky="w")

        ttk.Button(frame, text="Save", command=self._save_settings).grid(row=4, column=0, pady=8)
        frame.columnconfigure(1, weight=1)

    def _save_settings(self) -> None:
        data = {
            "openai_api_key": self.api_key_var.get(),
            "captcha_api_key": self.captcha_var.get(),
            "headless": self.headless_var.get(),
            "test_mode": self.test_mode_var.get(),
            "auto_rotate_ip": self.rotate_ip_var.get(),
            "model": self.settings.get("model", "gpt-4"),
        }
        with open("config/settings.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        messagebox.showinfo("Saved", "Settings saved")


if __name__ == "__main__":
    root = tk.Tk()
    MainGUI(root)
    root.mainloop()

