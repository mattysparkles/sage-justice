"""Main Tkinter GUI for Sage Justice dashboard."""

import json
import math
import random
import tkinter as tk
from datetime import datetime, timedelta
from pathlib import Path
from tkinter import messagebox, simpledialog
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

import requests

from core import database
from core.config_loader import load_json_config
from core.review_generator import generate_reviews
from core.review_spinner import generate_variants
from core.site_config_loader import SiteConfigLoader
from scheduler.schedule_engine import ReviewScheduler
from gui.template_manager_gui import TemplateManagerFrame
from core.queue_manager import JobQueueManager

SETTINGS_PATH = Path("config/settings.local.json")
DEFAULT_SETTINGS_PATH = Path("config/settings.json")
LOG_PATH = Path("logs/app.log")
POST_LOG_PATH = Path("logs/post_log.csv")
ACCOUNTS_PATH = Path("accounts/accounts.json")
TEMPLATES_DIR = Path("templates")
TEMPLATES_PATH = Path("config/templates.json")
PROJECTS_PATH = Path("config/project.json")
QUEUED_DIR = Path("output/queued_reviews")


class GuardianDeck(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Guardian Deck")
        self.geometry("900x700")
        self.scheduler = ReviewScheduler()
        self.job_manager = JobQueueManager()
        self.create_widgets()

    # --- UI SETUP -----------------------------------------------------
    def create_widgets(self) -> None:
        ttk.Label(self, text="SAGE JUSTICE - Guardian Deck", font=("Helvetica", 16)).pack(pady=10)

        self.create_overview_panel()

        notebook = ttk.Notebook(self)
        notebook.pack(expand=True, fill="both")

        tabs = {
            "Review Generator": self.create_review_tab,
            "Templates": self.create_templates_tab,
            "Accounts": self.create_accounts_tab,
            "Proxies": self.create_proxy_tab,
            "Sites": self.create_sites_tab,
            "Schedule": self.create_scheduler_tab,
            "Jobs": self.create_jobs_tab,
            "Logs": self.create_logs_tab,
            "Settings": self.create_settings_tab,
        }

        for name, creator in tabs.items():
            frame = ttk.Frame(notebook)
            notebook.add(frame, text=name)
            creator(frame)

    def create_overview_panel(self) -> None:
        panel = ttk.Frame(self)
        panel.pack(fill="x", padx=10, pady=5)

        stats_frame = ttk.Frame(panel)
        stats_frame.pack(side="left", fill="x", expand=True)
        self.job_status_var = tk.StringVar()
        ttk.Label(stats_frame, textvariable=self.job_status_var).pack(anchor="w")
        self.review_count_var = tk.StringVar()
        ttk.Label(stats_frame, textvariable=self.review_count_var).pack(anchor="w")

        charts_frame = ttk.Frame(panel)
        charts_frame.pack(side="right")
        self.accounts_canvas = tk.Canvas(charts_frame, width=100, height=100)
        self.accounts_canvas.pack(side="left", padx=5)
        self.proxies_canvas = tk.Canvas(charts_frame, width=100, height=100)
        self.proxies_canvas.pack(side="left", padx=5)

        self.refresh_overview()

    def refresh_overview(self) -> None:
        counts = database.job_counts()
        pending = counts.get("Pending", 0)
        running = counts.get("Running", 0)
        failed = counts.get("Failed", 0)
        self.job_status_var.set(f"Job Queue: {pending} Pending, {running} Running, {failed} Failed")
        reviews_today = database.count_reviews_today()
        self.review_count_var.set(f"Reviews Posted Today: {reviews_today}")
        self.draw_pie_chart(self.accounts_canvas, database.accounts_status_counts())
        self.draw_pie_chart(self.proxies_canvas, database.proxies_region_counts())
        self.after(60000, self.refresh_overview)

    def draw_pie_chart(self, canvas: tk.Canvas, data: dict[str, int]) -> None:
        canvas.delete("all")
        total = sum(data.values()) or 1
        start = 0.0
        colors = ["green", "orange", "red", "blue", "purple", "gray"]
        for i, (label, value) in enumerate(data.items()):
            extent = 360 * (value / total)
            canvas.create_arc(10, 10, 90, 90, start=start, extent=extent, fill=colors[i % len(colors)])
            start += extent

    # --- REVIEW GENERATOR --------------------------------------------
    def create_review_tab(self, frame: ttk.Frame) -> None:
        ttk.Label(frame, text="Prompt:").pack(anchor="w")
        self.prompt_text = ScrolledText(frame, height=4)
        self.prompt_text.pack(fill="x", padx=10, pady=5)

        options = ttk.Frame(frame)
        options.pack(fill="x", padx=10)
        ttk.Label(options, text="Count:").pack(side="left")
        self.count_var = tk.IntVar(value=1)
        ttk.Spinbox(options, from_=1, to=10, textvariable=self.count_var, width=5).pack(side="left", padx=5)
        self.rewrite_var = tk.BooleanVar()
        ttk.Checkbutton(options, text="Rewrite", variable=self.rewrite_var).pack(side="left", padx=5)
        ttk.Button(options, text="Generate", command=self.run_generation).pack(side="left", padx=5)
        ttk.Label(options, text="Template:").pack(side="left", padx=(10, 0))
        self.template_var = tk.StringVar()
        self.template_box = ttk.Combobox(options, textvariable=self.template_var, state="readonly", width=25)
        self.template_box.pack(side="left", padx=5)
        self.refresh_template_dropdown()
        ttk.Label(options, text="Assign to Project:").pack(side="left", padx=(10, 0))
        self.project_var = tk.StringVar()
        self.project_box = ttk.Combobox(options, textvariable=self.project_var, state="readonly", width=20)
        self.project_box.pack(side="left", padx=5)
        self.project_box.bind("<<ComboboxSelected>>", self.handle_project_selection)
        self.refresh_projects()
        ttk.Button(options, text="Assign & Queue", command=self.assign_and_queue).pack(side="left", padx=5)

        tone_frame = ttk.Frame(frame)
        tone_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(tone_frame, text="Formality").grid(row=0, column=0, sticky="w")
        self.formality_var = tk.IntVar(value=5)
        ttk.Scale(tone_frame, from_=0, to=10, orient="horizontal", variable=self.formality_var).grid(row=0, column=1, sticky="ew")
        ttk.Label(tone_frame, text="Emotion").grid(row=1, column=0, sticky="w")
        self.emotion_var = tk.IntVar(value=5)
        ttk.Scale(tone_frame, from_=0, to=10, orient="horizontal", variable=self.emotion_var).grid(row=1, column=1, sticky="ew")
        tone_frame.columnconfigure(1, weight=1)

        select_top = ttk.Frame(frame)
        select_top.pack(fill="x", padx=10, pady=(5, 0))
        self.select_all_button_top = ttk.Button(select_top, text="Select All", command=self.toggle_select_all)
        self.select_all_button_top.pack(side="left")
        self.selected_label_var = tk.StringVar(value="Selected: 0")
        ttk.Label(select_top, textvariable=self.selected_label_var).pack(side="right")

        canvas_frame = ttk.Frame(frame)
        canvas_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.review_canvas = tk.Canvas(canvas_frame)
        self.review_canvas.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.review_canvas.yview)
        scrollbar.pack(side="right", fill="y")
        self.review_canvas.configure(yscrollcommand=scrollbar.set)
        # Use a regular Tk frame rather than ttk so that background color can
        # be queried and configured. ttk.Frame does not support the "background"
        # option which leads to a TclError when calling cget("background").
        self.review_container = tk.Frame(self.review_canvas)
        self.review_canvas.create_window((0, 0), window=self.review_container, anchor="nw")
        self.review_container.bind(
            "<Configure>",
            lambda e: self.review_canvas.configure(scrollregion=self.review_canvas.bbox("all")),
        )
        self.default_review_bg = self.review_container.cget("background")

        select_bottom = ttk.Frame(frame)
        select_bottom.pack(fill="x", padx=10, pady=(0, 5))
        self.select_all_button_bottom = ttk.Button(select_bottom, text="Select All", command=self.toggle_select_all)
        self.select_all_button_bottom.pack(side="left")

        self.reviews = []

    def run_generation(self) -> None:
        tmpl = getattr(self, "template_options", {}).get(self.template_var.get())
        count = self.count_var.get()
        if tmpl:
            reviews = [self.generate_preview_from_template(tmpl) for _ in range(count)]
            if self.rewrite_var.get():
                spun = []
                for review in reviews:
                    variants = generate_variants(review, n=1)
                    spun.append(variants[0] if variants else review)
                reviews = spun
        else:
            prompt = self.prompt_text.get("1.0", "end").strip()
            if not prompt:
                messagebox.showwarning("Input", "Please provide a prompt.")
                return
            try:
                reviews = generate_reviews(
                    prompt,
                    count=count,
                    formality=self.formality_var.get(),
                    emotion=self.emotion_var.get(),
                )
                if self.rewrite_var.get():
                    spun = []
                    for review in reviews:
                        variants = generate_variants(review, n=1)
                        spun.append(variants[0] if variants else review)
                    reviews = spun
            except Exception as e:
                messagebox.showerror("OpenAI", f"Failed to generate reviews: {e}")
                return
        reviews = reviews[:count]
        self.display_reviews(reviews)

    def display_reviews(self, reviews: list[str]) -> None:
        for child in self.review_container.winfo_children():
            child.destroy()
        self.reviews = []
        for review in reviews:
            var = tk.BooleanVar()
            cb = tk.Checkbutton(
                self.review_container,
                text=review,
                variable=var,
                anchor="w",
                justify="left",
                wraplength=750,
                bg=self.default_review_bg,
            )
            cb.configure(command=lambda v=var, w=cb: self.on_review_toggle(v, w))
            cb.pack(fill="x", anchor="w", pady=2)
            self.reviews.append({"var": var, "text": review, "widget": cb})
        self.update_selected_count()

    def on_review_toggle(self, var: tk.BooleanVar, widget: tk.Checkbutton) -> None:
        widget.configure(bg="#e0f7fa" if var.get() else self.default_review_bg)
        self.update_selected_count()

    def update_selected_count(self) -> None:
        selected = sum(1 for r in self.reviews if r["var"].get())
        self.selected_label_var.set(f"Selected: {selected}")
        text = "Deselect All" if self.reviews and selected == len(self.reviews) else "Select All"
        self.select_all_button_top.config(text=text)
        self.select_all_button_bottom.config(text=text)

    def toggle_select_all(self) -> None:
        select = any(not r["var"].get() for r in self.reviews)
        for r in self.reviews:
            r["var"].set(select)
            r["widget"].configure(bg="#e0f7fa" if select else self.default_review_bg)
        self.update_selected_count()

    def generate_preview_from_template(self, tmpl: dict) -> str:
        blocks = tmpl.get("review_blocks", [])
        blocks = blocks[:]
        random.shuffle(blocks)
        return " ".join(blocks)

    def load_templates_list(self) -> list[dict]:
        try:
            with open(TEMPLATES_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return []

    def refresh_template_dropdown(self) -> None:
        templates = self.load_templates_list()
        self.template_options = {t["name"]: t for t in templates}
        values = list(self.template_options.keys())
        self.template_box["values"] = values
        if values:
            self.template_var.set(values[0])
        else:
            self.template_var.set("")

    def load_projects_list(self) -> list[str]:
        try:
            data = load_json_config(PROJECTS_PATH)
            if isinstance(data, list):
                return data
            return data.get("projects", [])
        except FileNotFoundError:
            return []

    def refresh_projects(self) -> None:
        projects = self.load_projects_list()
        values = projects + ["Create New Project..."]
        self.project_box["values"] = values
        if projects:
            self.project_var.set(projects[0])
        else:
            self.project_var.set("")

    def handle_project_selection(self, event=None) -> None:
        if self.project_var.get() == "Create New Project...":
            name = simpledialog.askstring("New Project", "Project name:")
            if name:
                projects = self.load_projects_list()
                if name not in projects:
                    projects.append(name)
                    with open(PROJECTS_PATH, "w", encoding="utf-8") as f:
                        json.dump(projects, f, indent=2)
                self.refresh_projects()
                self.project_var.set(name)
            else:
                self.project_var.set("")

    def assign_and_queue(self) -> None:
        project = self.project_var.get()
        if not project or project == "Create New Project...":
            messagebox.showwarning("Project", "Please select a project.")
            return
        selected = [r["text"] for r in self.reviews if r["var"].get()]
        if not selected:
            messagebox.showinfo("Assign & Queue", "No reviews selected.")
            return
        QUEUED_DIR.mkdir(parents=True, exist_ok=True)
        file_path = QUEUED_DIR / f"{project}.json"
        try:
            existing = json.load(open(file_path, "r", encoding="utf-8"))
        except FileNotFoundError:
            existing = []
        for text in selected:
            existing.append({
                "text": text,
                "timestamp": datetime.utcnow().isoformat(),
                "project": project,
            })
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)
        messagebox.showinfo(
            "Assign & Queue", f"Queued {len(selected)} review(s) for project '{project}'."
        )

    # --- TEMPLATES ----------------------------------------------------
    def create_templates_tab(self, frame: ttk.Frame) -> None:
        manager = TemplateManagerFrame(frame, on_update=self.refresh_template_dropdown)
        manager.pack(fill="both", expand=True)

    # --- ACCOUNTS -----------------------------------------------------
    def create_accounts_tab(self, frame: ttk.Frame) -> None:
        columns = ("username", "category", "status", "last_used")
        self.accounts_tree = ttk.Treeview(frame, columns=columns, show="headings")
        for col in columns:
            self.accounts_tree.heading(col, text=col.replace("_", " ").title())
        self.accounts_tree.column("status", width=100, anchor="center")
        self.accounts_tree.pack(fill="both", expand=True, padx=10, pady=5)
        self.accounts_tree.tag_configure("healthy", foreground="green")
        self.accounts_tree.tag_configure("warning", foreground="orange")
        self.accounts_tree.tag_configure("failed", foreground="red")

        btns = ttk.Frame(frame)
        btns.pack(pady=5)
        ttk.Button(btns, text="Add Account", command=self.add_account_dialog).pack(side="left", padx=5)
        ttk.Button(btns, text="Delete Selected", command=self.delete_selected_account).pack(side="left", padx=5)
        ttk.Button(btns, text="Mark as Failed", command=self.mark_account_failed).pack(side="left", padx=5)

        self.refresh_accounts()

    def refresh_accounts(self) -> None:
        for item in self.accounts_tree.get_children():
            self.accounts_tree.delete(item)
        for acc in database.get_all_accounts():
            status = acc.get("health_status") or "warning"
            tag = status if status in ("healthy", "failed") else "warning"
            self.accounts_tree.insert(
                "",
                "end",
                iid=acc["id"],
                values=(
                    acc.get("username"),
                    acc.get("category"),
                    status,
                    acc.get("last_used", ""),
                ),
                tags=(tag,),
            )

    def add_account_dialog(self) -> None:
        username = simpledialog.askstring("Add Account", "Username:")
        if not username:
            return
        password = simpledialog.askstring("Add Account", "Password:", show="*")
        if password is None:
            return
        category = simpledialog.askstring("Add Account", "Category:") or "general"
        database.add_account(username, password, category)
        self.refresh_accounts()

    def delete_selected_account(self) -> None:
        sel = self.accounts_tree.selection()
        if not sel:
            return
        account_id = int(sel[0])
        database.delete_account(account_id)
        self.refresh_accounts()

    def mark_account_failed(self) -> None:
        sel = self.accounts_tree.selection()
        if not sel:
            return
        account_id = int(sel[0])
        database.update_account_health(account_id, "failed")
        self.refresh_accounts()

    # --- PROXIES ------------------------------------------------------
    def create_proxy_tab(self, frame: ttk.Frame) -> None:
        columns = ("ip", "port", "region", "status")
        self.proxy_tree = ttk.Treeview(frame, columns=columns, show="headings")
        for col in columns:
            self.proxy_tree.heading(col, text=col.title())
        self.proxy_tree.column("status", width=100, anchor="center")
        self.proxy_tree.pack(fill="both", expand=True, padx=10, pady=5)
        self.proxy_tree.tag_configure("Working", foreground="green")
        self.proxy_tree.tag_configure("Down", foreground="red")
        self.proxy_tree.tag_configure("Unknown", foreground="orange")

        entry = ttk.Frame(frame)
        entry.pack(fill="x", padx=10, pady=5)
        self.proxy_entry = ttk.Entry(entry)
        self.proxy_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(entry, text="Add", command=self.add_proxy).pack(side="left", padx=5)
        ttk.Button(entry, text="Delete Selected", command=self.delete_proxy).pack(side="left", padx=5)
        ttk.Button(entry, text="Test Proxy", command=self.test_selected_proxy).pack(side="left")

        self.refresh_proxies()

    def refresh_proxies(self) -> None:
        for item in self.proxy_tree.get_children():
            self.proxy_tree.delete(item)
        for proxy in database.get_all_proxies():
            tag = proxy.get("status") or "Unknown"
            self.proxy_tree.insert(
                "",
                "end",
                iid=proxy["id"],
                values=(
                    proxy.get("ip_address"),
                    proxy.get("port"),
                    proxy.get("region", ""),
                    proxy.get("status", "Unknown"),
                ),
                tags=(tag,),
            )

    def add_proxy(self) -> None:
        entry = self.proxy_entry.get().strip()
        if not entry or ":" not in entry:
            return
        ip, port = entry.split(":", 1)
        region = self.lookup_region(ip)
        database.add_proxy(ip, port, region, "Unknown")
        self.proxy_entry.delete(0, tk.END)
        self.refresh_proxies()

    def delete_proxy(self) -> None:
        sel = self.proxy_tree.selection()
        if not sel:
            return
        proxy_id = int(sel[0])
        database.delete_proxy(proxy_id)
        self.refresh_proxies()

    def test_selected_proxy(self) -> None:
        sel = self.proxy_tree.selection()
        if not sel:
            return
        proxy_id = int(sel[0])
        item = self.proxy_tree.item(sel[0])
        ip, port = item["values"][0], item["values"][1]
        status = self.ping_proxy(f"{ip}:{port}")
        region = self.lookup_region(ip)
        database.update_proxy(proxy_id, status=status, region=region)
        self.refresh_proxies()

    def lookup_region(self, ip: str) -> str | None:
        try:
            resp = requests.get(f"http://ip-api.com/json/{ip}", timeout=5).json()
            if resp.get("status") == "success":
                return resp.get("countryCode")
        except Exception:
            return None
        return None

    def ping_proxy(self, proxy: str) -> str:
        proxies = {"http": proxy, "https": proxy}
        try:
            requests.get("https://www.google.com", proxies=proxies, timeout=5)
            return "Working"
        except Exception:
            return "Down"

    # --- SITES --------------------------------------------------------
    def create_sites_tab(self, frame: ttk.Frame) -> None:
        loader = SiteConfigLoader(TEMPLATES_DIR)
        sites = loader.load_templates()
        text = ScrolledText(frame)
        text.pack(fill="both", expand=True, padx=10, pady=5)
        for name, conf in sites.items():
            text.insert("end", f"{name}: {list(conf.get('fields', {}).keys())}\n")
        text.config(state="disabled")

    # --- SCHEDULER ----------------------------------------------------
    def create_scheduler_tab(self, frame: ttk.Frame) -> None:
        columns = ("site", "time", "status", "repeat")
        self.schedule_tree = ttk.Treeview(frame, columns=columns, show="headings")
        for col in columns:
            self.schedule_tree.heading(col, text=col.title())
        self.schedule_tree.pack(fill="both", expand=True, side="left", padx=5, pady=5)

        controls = ttk.Frame(frame)
        controls.pack(side="left", fill="y", padx=5, pady=5)
        ttk.Button(controls, text="Add Scheduled Job", command=self.add_schedule_job).pack(fill="x", pady=2)
        ttk.Button(controls, text="Remove Selected", command=self.remove_schedule).pack(fill="x", pady=2)
        ttk.Button(controls, text="Toggle Scheduler", command=self.toggle_scheduler).pack(fill="x", pady=2)
        self.scheduler_banner = ttk.Label(controls, text="Scheduler: Stopped", foreground="red")
        self.scheduler_banner.pack(anchor="w", pady=5)

        self.refresh_schedule_table()

    def refresh_schedule_table(self) -> None:
        for item in getattr(self, "schedule_tree").get_children():
            self.schedule_tree.delete(item)
        for idx, task in enumerate(self.scheduler.schedule):
            repeat = "Y" if task.get("interval_minutes") else "N"
            self.schedule_tree.insert(
                "",
                "end",
                iid=str(idx),
                values=(task.get("site"), task.get("next_run"), task.get("status"), repeat),
            )

    def add_schedule_job(self) -> None:
        site = simpledialog.askstring("Scheduled Job", "Site:")
        if not site:
            return
        prompt = simpledialog.askstring("Scheduled Job", "Prompt:") or ""
        interval = simpledialog.askinteger("Scheduled Job", "Interval minutes", minvalue=1, initialvalue=60)
        task = {
            "site": site,
            "prompt": prompt,
            "interval_minutes": interval,
            "next_run": self.scheduler.get_next_run(interval),
            "status": "Queued",
        }
        self.scheduler.schedule.append(task)
        self.scheduler.save_schedule()
        self.refresh_schedule_table()

    def remove_schedule(self) -> None:
        sel = self.schedule_tree.selection()
        if not sel:
            return
        index = int(sel[0])
        if 0 <= index < len(self.scheduler.schedule):
            del self.scheduler.schedule[index]
            self.scheduler.save_schedule()
            self.refresh_schedule_table()

    def toggle_scheduler(self) -> None:
        if self.scheduler.running:
            self.scheduler.stop()
            self.scheduler_banner.config(text="Scheduler: Stopped", foreground="red")
        else:
            self.scheduler.start()
            self.scheduler_banner.config(text="Scheduler: Running", foreground="green")

    # --- JOBS --------------------------------------------------------
    def create_jobs_tab(self, frame: ttk.Frame) -> None:
        controls = ttk.Frame(frame)
        controls.pack(fill="x", pady=5)
        self.show_failed_var = tk.BooleanVar()
        ttk.Checkbutton(
            controls,
            text="Show only failed",
            variable=self.show_failed_var,
            command=self.refresh_jobs_view,
        ).pack(side="left")
        ttk.Button(controls, text="Retry Selected", command=self.retry_selected_job).pack(
            side="left", padx=5
        )
        ttk.Button(controls, text="Refresh", command=self.refresh_jobs_view).pack(
            side="right"
        )

        columns = ("job_id", "site", "status", "scheduled")
        self.jobs_tree = ttk.Treeview(frame, columns=columns, show="headings")
        headings = ["Job ID", "Site", "Status", "Time Scheduled"]
        for col, head in zip(columns, headings):
            self.jobs_tree.heading(col, text=head)
            self.jobs_tree.column(col, anchor="center")
        self.jobs_tree.pack(fill="both", expand=True, padx=5, pady=5)

        # color coding
        self.jobs_tree.tag_configure("Pending", foreground="orange")
        self.jobs_tree.tag_configure("Running", foreground="blue")
        self.jobs_tree.tag_configure("Posted", foreground="green")
        self.jobs_tree.tag_configure("Failed", foreground="red")

        self.refresh_jobs_view()

    def refresh_jobs_view(self) -> None:
        self.job_manager.load_queue()
        for item in self.jobs_tree.get_children():
            self.jobs_tree.delete(item)
        for job in self.job_manager.queue:
            if self.show_failed_var.get() and job["status"] != "Failed":
                continue
            sched = datetime.fromtimestamp(job["scheduled_time"]).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            self.jobs_tree.insert(
                "",
                "end",
                values=(job["job_id"], job["site_name"], job["status"], sched),
                tags=(job["status"],),
            )
        if hasattr(self, "_jobs_refresh_id"):
            self.after_cancel(self._jobs_refresh_id)
        self._jobs_refresh_id = self.after(3000, self.refresh_jobs_view)

    def retry_selected_job(self) -> None:
        for item in self.jobs_tree.selection():
            job_id = self.jobs_tree.item(item, "values")[0]
            self.job_manager.mark_job_as(job_id, "Pending")
        self.refresh_jobs_view()

    # --- LOGS ---------------------------------------------------------
    def create_logs_tab(self, frame: ttk.Frame) -> None:
        self.log_output = ScrolledText(frame, height=20)
        self.log_output.pack(fill="both", expand=True, padx=10, pady=5)
        ttk.Button(frame, text="Refresh", command=self.load_logs).pack(pady=5)
        self.load_logs()

    def load_logs(self) -> None:
        self.log_output.delete("1.0", "end")
        path = POST_LOG_PATH if POST_LOG_PATH.exists() else LOG_PATH
        if path.exists():
            lines = path.read_text(encoding="utf-8").splitlines()[-100:]
            self.log_output.insert("end", "\n".join(lines))
        else:
            self.log_output.insert("end", "Log file not found.")

    # --- SETTINGS -----------------------------------------------------
    def create_settings_tab(self, frame: ttk.Frame) -> None:
        ttk.Label(frame, text="OpenAI API Key:").pack(anchor="w", padx=10, pady=5)
        self.api_key_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.api_key_var, width=60).pack(padx=10, pady=5)
        ttk.Label(frame, text="Model:").pack(anchor="w", padx=10, pady=5)
        self.model_var = tk.StringVar()
        ttk.Combobox(
            frame,
            textvariable=self.model_var,
            values=["gpt-3.5-turbo", "gpt-4"],
            state="readonly",
            width=20,
        ).pack(padx=10, pady=5)
        ttk.Button(frame, text="Save", command=self.save_settings).pack(pady=5)
        self.load_settings()

    def load_settings(self) -> None:
        path = SETTINGS_PATH if SETTINGS_PATH.exists() else DEFAULT_SETTINGS_PATH
        try:
            data = load_json_config(path)
        except FileNotFoundError:
            data = {}
        self.api_key_var.set(data.get("openai_api_key", ""))
        self.model_var.set(data.get("model", "gpt-4"))

    def save_settings(self) -> None:
        data = {
            "openai_api_key": self.api_key_var.get(),
            "model": self.model_var.get(),
        }
        SETTINGS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
        messagebox.showinfo("Settings", "Settings saved.")


if __name__ == "__main__":
    app = GuardianDeck()
    app.mainloop()
