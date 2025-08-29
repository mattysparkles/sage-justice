"""Main Tkinter GUI for Sage Justice dashboard."""

import json
import math
import random
import tkinter as tk
from datetime import datetime, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

import requests
import socket

from core import database
from core.config_loader import load_json_config
from core.style_generator import generate_styled_reviews
from core import project_hub
from scheduler.schedule_engine import ReviewScheduler
from gui.template_manager_gui import TemplateManagerFrame
from gui.site_manager_gui import SiteManagerFrame
from core.queue_manager import JobQueueManager
from core.logger import logger
from core.serp_scanner import check_review_visibility
from core.captcha_solver import solve_captcha
from core.geospoofer import get_random_location
from core.async_queue import AsyncReviewQueue
from core.log_manager import LogManager

SETTINGS_PATH = Path("config/settings.local.json")
DEFAULT_SETTINGS_PATH = Path("config/settings.json")
LOG_SETTINGS_PATH = Path("config/log_settings.json")
ACCOUNTS_PATH = Path("accounts/accounts.json")
TEMPLATES_DIR = Path("templates")
TEMPLATES_PATH = Path("config/templates.json")
QUEUED_DIR = Path("output/queued_reviews")


class GuardianDeck(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Guardian Deck")
        self.geometry("900x700")
        self.scheduler = ReviewScheduler()
        self.job_manager = JobQueueManager()
        self.async_queue = AsyncReviewQueue()
        self.async_queue.start()
        log_cfg = load_json_config(LOG_SETTINGS_PATH) if LOG_SETTINGS_PATH.exists() else {}
        max_per = log_cfg.get("max_size_per_project", 1024 * 1024)
        max_all = log_cfg.get("max_size_overall", 10 * 1024 * 1024)
        self.log_manager = LogManager(
            max_size_per_project=max_per, max_size_overall=max_all
        )
        self.create_widgets()

    # --- UI SETUP -----------------------------------------------------
    def create_widgets(self) -> None:
        ttk.Label(self, text="SAGE JUSTICE - Guardian Deck", font=("Helvetica", 16)).pack(pady=10)

        self.create_overview_panel()

        notebook = ttk.Notebook(self)
        notebook.pack(expand=True, fill="both")

        tabs = {
            "Review Generator": self.create_review_tab,
            "Review Queue": self.create_queue_tab,
            "Projects": self.create_projects_tab,
            "Templates": self.create_templates_tab,
            "Accounts": self.create_accounts_tab,
            "Proxies": self.create_proxy_tab,
            "Sites": self.create_sites_tab,
            "Schedule": self.create_scheduler_tab,
            "Jobs": self.create_jobs_tab,
            "Logs": self.create_logs_tab,
            "Tools": self.create_tools_tab,
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
        ttk.Label(frame, text="Tell us about your experience").pack(anchor="w")
        self.prompt_text = ScrolledText(frame, height=4)
        self.prompt_text.pack(fill="x", padx=10, pady=5)

        options = ttk.Frame(frame)
        options.pack(fill="x", padx=10)
        ttk.Label(options, text="Count:").pack(side="left")
        self.count_var = tk.IntVar(value=1)
        ttk.Spinbox(options, from_=1, to=10, textvariable=self.count_var, width=5).pack(side="left", padx=5)
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

        style_frame = ttk.Frame(frame)
        style_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(style_frame, text="Tone:").pack(side="left")
        self.tone_var = tk.StringVar(value="professional")
        for tone in ["professional", "rhetorical", "outraged", "legalese"]:
            ttk.Radiobutton(style_frame, text=tone.title(), value=tone, variable=self.tone_var).pack(side="left", padx=2)

        rating_frame = ttk.Frame(frame)
        rating_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(rating_frame, text="Min Stars").grid(row=0, column=0, sticky="w")
        self.min_star_var = tk.IntVar(value=1)
        ttk.Spinbox(rating_frame, from_=1, to=5, textvariable=self.min_star_var, width=5).grid(row=0, column=1, padx=5, sticky="w")
        ttk.Label(rating_frame, text="Max Stars").grid(row=0, column=2, padx=(10, 0), sticky="w")
        self.max_star_var = tk.IntVar(value=5)
        ttk.Spinbox(rating_frame, from_=1, to=5, textvariable=self.max_star_var, width=5).grid(row=0, column=3, padx=5, sticky="w")

        select_top = ttk.Frame(frame)
        select_top.pack(fill="x", padx=10, pady=(5, 0))
        self.select_all_button_top = ttk.Button(select_top, text="Select All", command=self.toggle_select_all)
        self.select_all_button_top.pack(side="left")
        self.selected_label_var = tk.StringVar(value="Selected: 0/0")
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
        min_star = self.min_star_var.get()
        max_star = self.max_star_var.get()
        if min_star > max_star:
            messagebox.showwarning("Star Rating", "Min stars cannot exceed max stars.")
            return
        if tmpl:
            reviews = [self.generate_preview_from_template(tmpl) for _ in range(count)]
        else:
            prompt = self.prompt_text.get("1.0", "end").strip()
            if not prompt:
                messagebox.showwarning("Input", "Please provide your experience.")
                return
            try:
                reviews = generate_styled_reviews(prompt, count=count, tone=self.tone_var.get())
            except Exception as e:
                messagebox.showerror("OpenAI", f"Failed to generate reviews: {e}")
                logger.error(f"Review generation failed: {e}")
                return
        reviews = reviews[:count]
        self.display_reviews(reviews)

    def display_reviews(self, reviews: list[str]) -> None:
        for child in self.review_container.winfo_children():
            child.destroy()
        self.reviews = []
        min_star = self.min_star_var.get()
        max_star = self.max_star_var.get()
        for review in reviews:
            rating = random.randint(min_star, max_star)
            var = tk.BooleanVar()
            cb = tk.Checkbutton(
                self.review_container,
                text=f"[{rating}\u2605] {review}",
                variable=var,
                anchor="w",
                justify="left",
                wraplength=750,
                bg=self.default_review_bg,
            )
            cb.configure(command=lambda v=var, w=cb: self.on_review_toggle(v, w))
            cb.pack(fill="x", anchor="w", pady=2)
            self.reviews.append({"var": var, "text": review, "rating": rating, "widget": cb})
        self.update_selected_count()

    def on_review_toggle(self, var: tk.BooleanVar, widget: tk.Checkbutton) -> None:
        widget.configure(bg="#e0f7fa" if var.get() else self.default_review_bg)
        self.update_selected_count()

    def update_selected_count(self) -> None:
        selected = sum(1 for r in self.reviews if r["var"].get())
        total = len(self.reviews)
        self.selected_label_var.set(f"Selected: {selected}/{total}")
        text = "Deselect All" if self.reviews and selected == total else "Select All"
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
        return project_hub.list_projects()

    def save_projects_list(self, projects: list[str]) -> None:
        # Project persistence handled by project_hub
        pass

    def refresh_projects(self) -> None:
        projects = self.load_projects_list()
        values = projects + ["Create New Project..."]
        self.project_box["values"] = values
        if projects:
            self.project_var.set(projects[0])
        else:
            self.project_var.set("")
        self.refresh_log_projects()

    def refresh_log_projects(self) -> None:
        if hasattr(self, "log_project_box"):
            projects = ["All"] + self.load_projects_list()
            self.log_project_box["values"] = projects
            if self.log_project_var.get() not in projects:
                self.log_project_var.set(projects[0] if projects else "All")

    def handle_project_selection(self, event=None) -> None:
        if self.project_var.get() == "Create New Project...":
            name = simpledialog.askstring("New Project", "Project name:")
            if name:
                project_hub.add_project(name)
                self.refresh_projects()
                self.project_var.set(name)
            else:
                self.project_var.set("")

    def assign_and_queue(self) -> None:
        project = self.project_var.get()
        if not project or project == "Create New Project...":
            messagebox.showwarning("Project", "Please select a project.")
            return
        selected = [r for r in self.reviews if r["var"].get()]
        if not selected:
            messagebox.showinfo("Assign & Queue", "No reviews selected.")
            return
        if project_hub.get_status(project) != "active":
            messagebox.showwarning("Project", f"Project '{project}' is not active.")
            return
        QUEUED_DIR.mkdir(parents=True, exist_ok=True)
        file_path = QUEUED_DIR / f"{project}.json"
        try:
            existing = json.load(open(file_path, "r", encoding="utf-8"))
        except FileNotFoundError:
            existing = []
        added = 0
        for item in selected:
            record = {
                "text": item["text"],
                "rating": item["rating"],
                "timestamp": datetime.utcnow().isoformat(),
                "project": project,
            }
            if project_hub.add_resource(project, "reviews", record):
                existing.append(record)
                added += 1
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)
        messagebox.showinfo(
            "Assign & Queue", f"Queued {added} review(s) for project '{project}'."
        )
        logger.info(f"Queued {added} review(s) for project '{project}'")
    # --- PROJECTS ----------------------------------------------------
    def create_projects_tab(self, frame: ttk.Frame) -> None:
        list_frame = ttk.Frame(frame)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.project_listbox = tk.Listbox(list_frame)
        self.project_listbox.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.project_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.project_listbox.configure(yscrollcommand=scrollbar.set)
        self.project_listbox.bind(
            "<<ListboxSelect>>",
            lambda e: (
                self.refresh_project_accounts(),
                self.refresh_project_proxies(),
                self.refresh_project_templates(),
                self.refresh_project_sites(),
                self.refresh_project_schedule(),
            ),
        )

        btns = ttk.Frame(frame)
        btns.pack(pady=5)
        ttk.Button(btns, text="Add", command=self.add_project).pack(side="left", padx=5)
        ttk.Button(btns, text="Rename", command=self.rename_project).pack(side="left", padx=5)
        ttk.Button(btns, text="Delete", command=self.delete_project).pack(side="left", padx=5)

        accounts_frame = ttk.LabelFrame(frame, text="Accounts")
        accounts_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.project_accounts_list = tk.Listbox(accounts_frame)
        self.project_accounts_list.pack(side="left", fill="both", expand=True)
        acc_scroll = ttk.Scrollbar(accounts_frame, orient="vertical", command=self.project_accounts_list.yview)
        acc_scroll.pack(side="right", fill="y")
        self.project_accounts_list.configure(yscrollcommand=acc_scroll.set)

        acc_btns = ttk.Frame(frame)
        acc_btns.pack(pady=5)
        ttk.Button(
            acc_btns,
            text="Assign Account",
            command=self.assign_account_to_project_from_projects_tab,
        ).pack(side="left", padx=5)
        ttk.Button(
            acc_btns,
            text="Unassign Selected",
            command=self.unassign_account_from_project_from_projects_tab,
        ).pack(side="left", padx=5)

        proxies_frame = ttk.LabelFrame(frame, text="Proxies")
        proxies_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.project_proxies_list = tk.Listbox(proxies_frame)
        self.project_proxies_list.pack(side="left", fill="both", expand=True)
        proxy_scroll = ttk.Scrollbar(proxies_frame, orient="vertical", command=self.project_proxies_list.yview)
        proxy_scroll.pack(side="right", fill="y")
        self.project_proxies_list.configure(yscrollcommand=proxy_scroll.set)

        proxy_btns = ttk.Frame(frame)
        proxy_btns.pack(pady=5)
        ttk.Button(
            proxy_btns,
            text="Assign Proxy",
            command=self.assign_proxy_to_project_from_projects_tab,
        ).pack(side="left", padx=5)
        ttk.Button(
            proxy_btns,
            text="Unassign Selected",
            command=self.unassign_proxy_from_project_from_projects_tab,
        ).pack(side="left", padx=5)

        templates_frame = ttk.LabelFrame(frame, text="Templates")
        templates_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.project_templates_list = tk.Listbox(templates_frame)
        self.project_templates_list.pack(side="left", fill="both", expand=True)
        tmpl_scroll = ttk.Scrollbar(templates_frame, orient="vertical", command=self.project_templates_list.yview)
        tmpl_scroll.pack(side="right", fill="y")
        self.project_templates_list.configure(yscrollcommand=tmpl_scroll.set)

        tmpl_btns = ttk.Frame(frame)
        tmpl_btns.pack(pady=5)
        ttk.Button(
            tmpl_btns,
            text="Assign Template",
            command=self.assign_template_to_project_from_projects_tab,
        ).pack(side="left", padx=5)
        ttk.Button(
            tmpl_btns,
            text="Unassign Selected",
            command=self.unassign_template_from_project_from_projects_tab,
        ).pack(side="left", padx=5)

        sites_frame = ttk.LabelFrame(frame, text="Sites")
        sites_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.project_sites_list = tk.Listbox(sites_frame)
        self.project_sites_list.pack(side="left", fill="both", expand=True)
        site_scroll = ttk.Scrollbar(sites_frame, orient="vertical", command=self.project_sites_list.yview)
        site_scroll.pack(side="right", fill="y")
        self.project_sites_list.configure(yscrollcommand=site_scroll.set)

        site_btns = ttk.Frame(frame)
        site_btns.pack(pady=5)
        ttk.Button(
            site_btns,
            text="Assign Site",
            command=self.assign_site_to_project_from_projects_tab,
        ).pack(side="left", padx=5)
        ttk.Button(
            site_btns,
            text="Unassign Selected",
            command=self.unassign_site_from_project_from_projects_tab,
        ).pack(side="left", padx=5)

        schedule_frame = ttk.LabelFrame(frame, text="Schedule Config")
        schedule_frame.pack(fill="x", padx=10, pady=5)
        self.project_schedule_var = tk.StringVar()
        ttk.Label(schedule_frame, textvariable=self.project_schedule_var).pack(side="left", padx=5)

        schedule_btns = ttk.Frame(frame)
        schedule_btns.pack(pady=5)
        ttk.Button(
            schedule_btns,
            text="Set Schedule",
            command=self.assign_schedule_to_project_from_projects_tab,
        ).pack(side="left", padx=5)
        ttk.Button(
            schedule_btns,
            text="Clear Schedule",
            command=self.clear_schedule_from_project_from_projects_tab,
        ).pack(side="left", padx=5)

        self.project_account_ids: list[int] = []
        self.project_proxy_ids: list[int] = []

        self.refresh_projects_tab()
        self.refresh_project_accounts()
        self.refresh_project_proxies()
        self.refresh_project_templates()
        self.refresh_project_sites()
        self.refresh_project_schedule()

    def refresh_projects_tab(self) -> None:
        self.project_listbox.delete(0, "end")
        for name in self.load_projects_list():
            self.project_listbox.insert("end", name)

    def add_project(self) -> None:
        name = simpledialog.askstring("Add Project", "Project name:")
        if not name:
            return
        projects = self.load_projects_list()
        if name in projects:
            messagebox.showinfo("Project", "Project already exists.")
            return
        project_hub.add_project(name)
        self.refresh_projects_tab()
        self.refresh_projects()
        self.refresh_queue_projects()

    def rename_project(self) -> None:
        sel = self.project_listbox.curselection()
        if not sel:
            messagebox.showinfo("Rename", "No project selected.")
            return
        index = sel[0]
        projects = self.load_projects_list()
        old_name = projects[index]
        new_name = simpledialog.askstring("Rename Project", "New name:", initialvalue=old_name)
        if not new_name or new_name == old_name:
            return
        if new_name in projects:
            messagebox.showinfo("Rename", "Project with that name already exists.")
            return
        project_hub.rename_project(old_name, new_name)
        old_file = QUEUED_DIR / f"{old_name}.json"
        new_file = QUEUED_DIR / f"{new_name}.json"
        if old_file.exists():
            old_file.rename(new_file)
        self.refresh_projects_tab()
        self.refresh_projects()
        self.refresh_queue_projects()

    def delete_project(self) -> None:
        sel = self.project_listbox.curselection()
        if not sel:
            messagebox.showinfo("Delete", "No project selected.")
            return
        index = sel[0]
        projects = self.load_projects_list()
        name = projects[index]
        if messagebox.askyesno("Delete", f"Delete project '{name}'?"):
            project_hub.delete_project(name)
            file_path = QUEUED_DIR / f"{name}.json"
            if file_path.exists():
                file_path.unlink()
            self.refresh_projects_tab()
            self.refresh_projects()
            self.refresh_queue_projects()

    def refresh_project_accounts(self) -> None:
        self.project_accounts_list.delete(0, "end")
        self.project_account_ids = []
        sel = self.project_listbox.curselection()
        if not sel:
            return
        project = self.project_listbox.get(sel[0])
        accounts = database.get_accounts_for_project(project)
        for acc in accounts:
            self.project_accounts_list.insert("end", acc.get("username"))
            self.project_account_ids.append(acc["id"])

    def refresh_project_proxies(self) -> None:
        self.project_proxies_list.delete(0, "end")
        self.project_proxy_ids = []
        sel = self.project_listbox.curselection()
        if not sel:
            return
        project = self.project_listbox.get(sel[0])
        proxies = database.get_proxies_for_project(project)
        for proxy in proxies:
            self.project_proxies_list.insert("end", f"{proxy['ip_address']}:{proxy.get('port','')}")
            self.project_proxy_ids.append(proxy["id"])

    def assign_account_to_project_from_projects_tab(self) -> None:
        sel = self.project_listbox.curselection()
        if not sel:
            return
        project = self.project_listbox.get(sel[0])
        accounts = database.get_all_accounts()
        if not accounts:
            messagebox.showinfo("Accounts", "No accounts available.")
            return
        dialog = tk.Toplevel(self)
        dialog.title("Assign Account")
        ttk.Label(dialog, text="Account:").pack(anchor="w", padx=10, pady=10)
        values = [f"{a['id']}: {a['username']}" for a in accounts]
        acc_var = tk.StringVar(value=values[0])
        acc_box = ttk.Combobox(dialog, values=values, textvariable=acc_var, state="readonly")
        acc_box.pack(padx=10, pady=5)

        def save() -> None:
            acc_id = int(acc_var.get().split(":", 1)[0])
            database.assign_account_to_project(acc_id, project)
            dialog.destroy()
            self.refresh_project_accounts()
            self.refresh_accounts()

        ttk.Button(dialog, text="Assign", command=save).pack(pady=10)

    def unassign_account_from_project_from_projects_tab(self) -> None:
        sel_proj = self.project_listbox.curselection()
        sel_acc = self.project_accounts_list.curselection()
        if not sel_proj or not sel_acc:
            return
        project = self.project_listbox.get(sel_proj[0])
        acc_id = self.project_account_ids[sel_acc[0]]
        database.remove_account_from_project(acc_id, project)
        self.refresh_project_accounts()
        self.refresh_accounts()

    def assign_proxy_to_project_from_projects_tab(self) -> None:
        sel = self.project_listbox.curselection()
        if not sel:
            return
        project = self.project_listbox.get(sel[0])
        proxies = database.get_all_proxies()
        if not proxies:
            messagebox.showinfo("Proxies", "No proxies available.")
            return
        dialog = tk.Toplevel(self)
        dialog.title("Assign Proxy")
        ttk.Label(dialog, text="Proxy:").pack(anchor="w", padx=10, pady=10)
        values = [f"{p['id']}: {p['ip_address']}:{p.get('port','')}" for p in proxies]
        proxy_var = tk.StringVar(value=values[0])
        ttk.Combobox(dialog, values=values, textvariable=proxy_var, state="readonly").pack(
            padx=10, pady=5
        )

        def save() -> None:
            proxy_id = int(proxy_var.get().split(":", 1)[0])
            database.assign_proxy_to_project(proxy_id, project)
            dialog.destroy()
            self.refresh_project_proxies()
            self.refresh_proxies()

        ttk.Button(dialog, text="Assign", command=save).pack(pady=10)

    def unassign_proxy_from_project_from_projects_tab(self) -> None:
        sel_proj = self.project_listbox.curselection()
        sel_proxy = self.project_proxies_list.curselection()
        if not sel_proj or not sel_proxy:
            return
        project = self.project_listbox.get(sel_proj[0])
        proxy_id = self.project_proxy_ids[sel_proxy[0]]
        database.remove_proxy_from_project(proxy_id, project)
        self.refresh_project_proxies()
        self.refresh_proxies()

    def refresh_project_templates(self) -> None:
        self.project_templates_list.delete(0, "end")
        sel = self.project_listbox.curselection()
        if not sel:
            return
        project = self.project_listbox.get(sel[0])
        templates = project_hub.list_templates(project)
        for tmpl in templates:
            self.project_templates_list.insert("end", tmpl)

    def refresh_project_sites(self) -> None:
        self.project_sites_list.delete(0, "end")
        sel = self.project_listbox.curselection()
        if not sel:
            return
        project = self.project_listbox.get(sel[0])
        sites = project_hub.list_sites(project)
        for site in sites:
            self.project_sites_list.insert("end", site)

    def refresh_project_schedule(self) -> None:
        self.project_schedule_var.set("")
        sel = self.project_listbox.curselection()
        if not sel:
            return
        project = self.project_listbox.get(sel[0])
        sched = project_hub.get_schedule(project)
        if sched:
            self.project_schedule_var.set(str(sched))

    def assign_template_to_project_from_projects_tab(self) -> None:
        sel = self.project_listbox.curselection()
        if not sel:
            return
        project = self.project_listbox.get(sel[0])
        templates = [t["name"] for t in self.load_templates_list()]
        if not templates:
            messagebox.showinfo("Templates", "No templates available.")
            return
        dialog = tk.Toplevel(self)
        dialog.title("Assign Template")
        ttk.Label(dialog, text="Template:").pack(anchor="w", padx=10, pady=10)
        tmpl_var = tk.StringVar(value=templates[0])
        ttk.Combobox(dialog, values=templates, textvariable=tmpl_var, state="readonly").pack(
            padx=10, pady=5
        )

        def save() -> None:
            project_hub.add_template(project, tmpl_var.get())
            dialog.destroy()
            self.refresh_project_templates()

        ttk.Button(dialog, text="Assign", command=save).pack(pady=10)

    def unassign_template_from_project_from_projects_tab(self) -> None:
        sel_proj = self.project_listbox.curselection()
        sel_tmpl = self.project_templates_list.curselection()
        if not sel_proj or not sel_tmpl:
            return
        project = self.project_listbox.get(sel_proj[0])
        template = self.project_templates_list.get(sel_tmpl[0])
        project_hub.remove_template(project, template)
        self.refresh_project_templates()

    def assign_site_to_project_from_projects_tab(self) -> None:
        sel = self.project_listbox.curselection()
        if not sel:
            return
        project = self.project_listbox.get(sel[0])
        loader = SiteConfigLoader(TEMPLATES_DIR)
        sites = list(loader.load_templates().keys())
        if not sites:
            messagebox.showinfo("Sites", "No sites available.")
            return
        dialog = tk.Toplevel(self)
        dialog.title("Assign Site")
        ttk.Label(dialog, text="Site:").pack(anchor="w", padx=10, pady=10)
        site_var = tk.StringVar(value=sites[0])
        ttk.Combobox(dialog, values=sites, textvariable=site_var, state="readonly").pack(
            padx=10, pady=5
        )

        def save() -> None:
            project_hub.add_site(project, site_var.get())
            dialog.destroy()
            self.refresh_project_sites()

        ttk.Button(dialog, text="Assign", command=save).pack(pady=10)

    def unassign_site_from_project_from_projects_tab(self) -> None:
        sel_proj = self.project_listbox.curselection()
        sel_site = self.project_sites_list.curselection()
        if not sel_proj or not sel_site:
            return
        project = self.project_listbox.get(sel_proj[0])
        site = self.project_sites_list.get(sel_site[0])
        project_hub.remove_site(project, site)
        self.refresh_project_sites()

    def assign_schedule_to_project_from_projects_tab(self) -> None:
        sel = self.project_listbox.curselection()
        if not sel:
            return
        project = self.project_listbox.get(sel[0])
        path = filedialog.askopenfilename(
            title="Select Schedule Config", filetypes=[("JSON Files", "*.json"), ("All Files", "*")]
        )
        if path:
            project_hub.set_schedule(project, path)
            self.refresh_project_schedule()

    def clear_schedule_from_project_from_projects_tab(self) -> None:
        sel = self.project_listbox.curselection()
        if not sel:
            return
        project = self.project_listbox.get(sel[0])
        project_hub.clear_schedule(project)
        self.refresh_project_schedule()

    # --- REVIEW QUEUE ------------------------------------------------
    def create_queue_tab(self, frame: ttk.Frame) -> None:
        controls = ttk.Frame(frame)
        controls.pack(fill="x", padx=10, pady=5)
        ttk.Label(controls, text="Project:").pack(side="left")
        self.queue_project_var = tk.StringVar()
        self.queue_project_box = ttk.Combobox(
            controls, textvariable=self.queue_project_var, state="readonly", width=20
        )
        self.queue_project_box.pack(side="left", padx=5)
        self.queue_project_box.bind("<<ComboboxSelected>>", self.refresh_queue_view)
        ttk.Button(controls, text="Edit Selected", command=self.edit_selected_queue_item).pack(
            side="left", padx=5
        )
        ttk.Button(controls, text="Delete Selected", command=self.delete_selected_queue_item).pack(
            side="left", padx=5
        )
        ttk.Button(controls, text="Refresh", command=self.refresh_queue_projects).pack(side="right")

        columns = ("rating", "text")
        self.queue_tree = ttk.Treeview(frame, columns=columns, show="headings")
        self.queue_tree.heading("rating", text="Rating")
        self.queue_tree.heading("text", text="Review")
        self.queue_tree.column("rating", width=60, anchor="center")
        self.queue_tree.column("text", anchor="w")
        self.queue_tree.pack(fill="both", expand=True, padx=10, pady=5)

        self.current_queue_data = []
        self.refresh_queue_projects()

    def refresh_queue_projects(self) -> None:
        projects = [p.stem for p in QUEUED_DIR.glob("*.json")] if QUEUED_DIR.exists() else []
        self.queue_project_box["values"] = projects
        if projects:
            if self.queue_project_var.get() not in projects:
                self.queue_project_var.set(projects[0])
            self.refresh_queue_view()
        else:
            self.queue_project_var.set("")
            self.refresh_queue_view()

    def load_queue_file(self, project: str) -> list[dict]:
        path = QUEUED_DIR / f"{project}.json"
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return []

    def save_queue_file(self, project: str, data: list[dict]) -> None:
        QUEUED_DIR.mkdir(parents=True, exist_ok=True)
        path = QUEUED_DIR / f"{project}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def refresh_queue_view(self, event=None) -> None:
        for item in self.queue_tree.get_children():
            self.queue_tree.delete(item)
        project = self.queue_project_var.get()
        if not project:
            self.current_queue_data = []
            return
        data = self.load_queue_file(project)
        self.current_queue_data = data
        for idx, item in enumerate(data):
            self.queue_tree.insert(
                "",
                "end",
                iid=str(idx),
                values=(item.get("rating", ""), item.get("text", "")),
            )

    def edit_selected_queue_item(self) -> None:
        sel = self.queue_tree.selection()
        if not sel:
            messagebox.showinfo("Edit", "No review selected.")
            return
        idx = int(sel[0])
        item = self.current_queue_data[idx]
        dialog = tk.Toplevel(self)
        dialog.title("Edit Review")
        ttk.Label(dialog, text="Text:").pack(anchor="w", padx=10, pady=(10, 0))
        text_box = ScrolledText(dialog, height=6, width=60)
        text_box.pack(padx=10, pady=5)
        text_box.insert("1.0", item.get("text", ""))
        ttk.Label(dialog, text="Rating:").pack(anchor="w", padx=10)
        rating_var = tk.IntVar(value=item.get("rating", 1))
        ttk.Spinbox(dialog, from_=1, to=5, textvariable=rating_var, width=5).pack(
            anchor="w", padx=10, pady=(0, 10)
        )

        def save() -> None:
            item["text"] = text_box.get("1.0", "end").strip()
            item["rating"] = rating_var.get()
            self.save_queue_file(self.queue_project_var.get(), self.current_queue_data)
            dialog.destroy()
            self.refresh_queue_view()

        ttk.Button(dialog, text="Save", command=save).pack(pady=5)

    def delete_selected_queue_item(self) -> None:
        sel = self.queue_tree.selection()
        if not sel:
            messagebox.showinfo("Delete", "No review selected.")
            return
        for item_id in sorted(sel, key=int, reverse=True):
            idx = int(item_id)
            del self.current_queue_data[idx]
        self.save_queue_file(self.queue_project_var.get(), self.current_queue_data)
        self.refresh_queue_view()

    # --- TEMPLATES ----------------------------------------------------
    def create_templates_tab(self, frame: ttk.Frame) -> None:
        manager = TemplateManagerFrame(frame, on_update=self.refresh_template_dropdown)
        manager.pack(fill="both", expand=True)

    # --- ACCOUNTS -----------------------------------------------------
    def create_accounts_tab(self, frame: ttk.Frame) -> None:
        columns = ("username", "category", "projects", "status", "last_used")
        self.accounts_tree = ttk.Treeview(frame, columns=columns, show="headings")
        for col in columns:
            self.accounts_tree.heading(col, text=col.replace("_", " ").title())
        self.accounts_tree.column("status", width=100, anchor="center")
        self.accounts_tree.column("projects", width=150)
        self.accounts_tree.pack(fill="both", expand=True, padx=10, pady=5)
        self.accounts_tree.tag_configure("healthy", foreground="green")
        self.accounts_tree.tag_configure("warning", foreground="orange")
        self.accounts_tree.tag_configure("failed", foreground="red")

        btns = ttk.Frame(frame)
        btns.pack(pady=5)
        ttk.Button(btns, text="Add Account", command=self.add_account_dialog).pack(side="left", padx=5)
        ttk.Button(btns, text="Delete Selected", command=self.delete_selected_account).pack(side="left", padx=5)
        ttk.Button(btns, text="Mark as Failed", command=self.mark_account_failed).pack(side="left", padx=5)
        ttk.Button(btns, text="Assign to Project", command=self.assign_account_to_project_dialog).pack(side="left", padx=5)
        ttk.Button(btns, text="Unassign from Project", command=self.unassign_account_from_project_dialog).pack(side="left", padx=5)
        ttk.Button(btns, text="Import From File", command=self.import_accounts_from_file).pack(side="left", padx=5)

        self.refresh_accounts()

    def refresh_accounts(self) -> None:
        for item in self.accounts_tree.get_children():
            self.accounts_tree.delete(item)
        for acc in database.get_all_accounts():
            status = acc.get("health_status") or "warning"
            tag = status if status in ("healthy", "failed") else "warning"
            projects = ", ".join(database.get_account_projects(acc["id"]))
            self.accounts_tree.insert(
                "",
                "end",
                iid=acc["id"],
                values=(
                    acc.get("username"),
                    acc.get("category"),
                    projects,
                    status,
                    acc.get("last_used", ""),
                ),
                tags=(tag,),
            )

    def add_account_dialog(self) -> None:
        dialog = tk.Toplevel(self)
        dialog.title("Add Account")

        fields = ttk.Frame(dialog)
        fields.pack(padx=10, pady=10)

        ttk.Label(fields, text="Username:").grid(row=0, column=0, sticky="w")
        user_var = tk.StringVar()
        ttk.Entry(fields, textvariable=user_var).grid(row=0, column=1)

        ttk.Label(fields, text="Password:").grid(row=1, column=0, sticky="w")
        pass_var = tk.StringVar()
        ttk.Entry(fields, textvariable=pass_var, show="*").grid(row=1, column=1)

        ttk.Label(fields, text="Category:").grid(row=2, column=0, sticky="w")
        cat_var = tk.StringVar(value="general")
        ttk.Entry(fields, textvariable=cat_var).grid(row=2, column=1)

        ttk.Label(fields, text="Site URL:").grid(row=3, column=0, sticky="w")
        site_var = tk.StringVar()
        ttk.Entry(fields, textvariable=site_var).grid(row=3, column=1)

        ttk.Label(fields, text="Login URL:").grid(row=4, column=0, sticky="w")
        login_var = tk.StringVar()
        ttk.Entry(fields, textvariable=login_var).grid(row=4, column=1)

        captcha_var = tk.BooleanVar()
        ttk.Checkbutton(fields, text="Requires Captcha", variable=captcha_var).grid(row=5, column=1, sticky="w")

        ttk.Label(fields, text="Phone (optional):").grid(row=6, column=0, sticky="w")
        phone_var = tk.StringVar()
        ttk.Entry(fields, textvariable=phone_var).grid(row=6, column=1)

        ttk.Label(fields, text="Project:").grid(row=7, column=0, sticky="w")
        projects = self.load_projects_list()
        proj_var = tk.StringVar()
        proj_box = ttk.Combobox(fields, values=projects, textvariable=proj_var, state="readonly")
        proj_box.grid(row=7, column=1)

        ttk.Label(fields, text="Social Login:").grid(row=8, column=0, sticky="w")
        social_var = tk.StringVar()
        social_box = ttk.Combobox(
            fields,
            values=["", "google", "facebook", "twitter", "linkedin"],
            textvariable=social_var,
            state="readonly",
        )
        social_box.grid(row=8, column=1)

        sms_var = tk.BooleanVar()
        voice_var = tk.BooleanVar()
        ttk.Checkbutton(fields, text="SMS Verification", variable=sms_var).grid(row=9, column=1, sticky="w")
        ttk.Checkbutton(fields, text="Voice Verification", variable=voice_var).grid(row=10, column=1, sticky="w")

        btns = ttk.Frame(dialog)
        btns.pack(pady=10)

        def save() -> None:
            username = user_var.get().strip()
            password = pass_var.get().strip()
            if not username or not password:
                messagebox.showwarning("Add Account", "Username and password required.")
                return
            category = cat_var.get().strip() or "general"
            metadata = {
                "site_url": site_var.get().strip() or None,
                "login_url": login_var.get().strip() or None,
                "captcha_required": captcha_var.get(),
                "phone": phone_var.get().strip() or None,
                "social_login": social_var.get().strip() or None,
                "sms_verification": sms_var.get(),
                "voice_verification": voice_var.get(),
            }
            account_id = database.add_account(username, password, category, metadata=metadata)
            project = proj_var.get().strip()
            if project:
                database.assign_account_to_project(account_id, project)
            if sms_var.get() and metadata["phone"]:
                self.trigger_sms_verification(metadata["phone"])
            if voice_var.get() and metadata["phone"]:
                self.trigger_voice_verification(metadata["phone"])
            dialog.destroy()
            self.refresh_accounts()

        ttk.Button(btns, text="Save", command=save).pack(side="left", padx=5)
        ttk.Button(btns, text="Cancel", command=dialog.destroy).pack(side="left", padx=5)

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

    def import_accounts_from_file(self) -> None:
        path = filedialog.askopenfilename()
        if not path:
            return
        count = 0
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split(":")
                username = parts[0]
                password = parts[1] if len(parts) > 1 else ""
                site_url = parts[2] if len(parts) > 2 else ""
                login_url = parts[3] if len(parts) > 3 else ""
                captcha_flag = parts[4].lower() in ("1", "true", "yes") if len(parts) > 4 else False
                phone = parts[5] if len(parts) > 5 and parts[5] else None
                project = parts[6] if len(parts) > 6 and parts[6] else None
                social = parts[7] if len(parts) > 7 and parts[7] else None
                sms_flag = parts[8].lower() in ("1", "true", "yes") if len(parts) > 8 else False
                voice_flag = parts[9].lower() in ("1", "true", "yes") if len(parts) > 9 else False
                metadata = {
                    "site_url": site_url or None,
                    "login_url": login_url or None,
                    "captcha_required": captcha_flag,
                    "phone": phone,
                    "social_login": social or None,
                    "sms_verification": sms_flag,
                    "voice_verification": voice_flag,
                }
                account_id = database.add_account(username, password, "general", metadata=metadata)
                if project:
                    database.assign_account_to_project(account_id, project)
                if sms_flag and phone:
                    self.trigger_sms_verification(phone)
                if voice_flag and phone:
                    self.trigger_voice_verification(phone)
                count += 1
        messagebox.showinfo("Import", f"Imported {count} accounts.")
        self.refresh_accounts()

    def trigger_sms_verification(self, phone: str) -> None:
        """Hook for integrating SMS verification."""
        logger.info("SMS verification hook for %s", phone)

    def trigger_voice_verification(self, phone: str) -> None:
        """Hook for integrating voice call verification."""
        logger.info("Voice verification hook for %s", phone)

    def assign_account_to_project_dialog(self) -> None:
        sel = self.accounts_tree.selection()
        if not sel:
            return
        account_id = int(sel[0])
        projects = self.load_projects_list()
        if not projects:
            messagebox.showinfo("Projects", "No projects available.")
            return
        dialog = tk.Toplevel(self)
        dialog.title("Assign to Project")
        ttk.Label(dialog, text="Project:").pack(anchor="w", padx=10, pady=10)
        proj_var = tk.StringVar(value=projects[0])
        proj_box = ttk.Combobox(dialog, values=projects, textvariable=proj_var, state="readonly")
        proj_box.pack(padx=10, pady=5)

        def save() -> None:
            database.assign_account_to_project(account_id, proj_var.get())
            dialog.destroy()
            self.refresh_accounts()
            self.refresh_project_accounts()

        ttk.Button(dialog, text="Assign", command=save).pack(pady=10)

    def unassign_account_from_project_dialog(self) -> None:
        sel = self.accounts_tree.selection()
        if not sel:
            return
        account_id = int(sel[0])
        projects = database.get_account_projects(account_id)
        if not projects:
            messagebox.showinfo("Unassign", "Account not assigned to any project.")
            return
        dialog = tk.Toplevel(self)
        dialog.title("Unassign from Project")
        ttk.Label(dialog, text="Project:").pack(anchor="w", padx=10, pady=10)
        proj_var = tk.StringVar(value=projects[0])
        proj_box = ttk.Combobox(dialog, values=projects, textvariable=proj_var, state="readonly")
        proj_box.pack(padx=10, pady=5)

        def remove() -> None:
            database.remove_account_from_project(account_id, proj_var.get())
            dialog.destroy()
            self.refresh_accounts()
            self.refresh_project_accounts()

        ttk.Button(dialog, text="Remove", command=remove).pack(pady=10)

    # --- PROXIES ------------------------------------------------------
    def create_proxy_tab(self, frame: ttk.Frame) -> None:
        columns = ("ip", "port", "region", "status", "projects", "sites", "accounts")
        self.proxy_tree = ttk.Treeview(frame, columns=columns, show="headings")
        for col in columns:
            self.proxy_tree.heading(col, text=col.title())
        self.proxy_tree.column("status", width=100, anchor="center")
        self.proxy_tree.column("projects", width=150)
        self.proxy_tree.column("sites", width=150)
        self.proxy_tree.column("accounts", width=150)
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
        ttk.Button(entry, text="Assign to Project", command=self.assign_proxy_to_project_dialog).pack(
            side="left", padx=5
        )
        ttk.Button(entry, text="Unassign from Project", command=self.unassign_proxy_from_project_dialog).pack(
            side="left", padx=5
        )
        ttk.Button(entry, text="Assign to Site", command=self.assign_proxy_to_site_dialog).pack(
            side="left", padx=5
        )
        ttk.Button(entry, text="Unassign from Site", command=self.unassign_proxy_from_site_dialog).pack(
            side="left", padx=5
        )
        ttk.Button(entry, text="Assign to Account", command=self.assign_proxy_to_account_dialog).pack(
            side="left", padx=5
        )
        ttk.Button(entry, text="Unassign from Account", command=self.unassign_proxy_from_account_dialog).pack(
            side="left", padx=5
        )
        ttk.Button(entry, text="Import From File", command=self.import_proxies_from_file).pack(side="left", padx=5)
        ttk.Button(entry, text="Import VPN Configs", command=self.import_vpn_configs).pack(side="left", padx=5)

        self.refresh_proxies()

    def refresh_proxies(self) -> None:
        for item in self.proxy_tree.get_children():
            self.proxy_tree.delete(item)
        for proxy in database.get_all_proxies():
            tag = proxy.get("status") or "Unknown"
            projects = proxy.get("projects") or ""
            sites = proxy.get("sites") or ""
            accounts = proxy.get("accounts") or ""
            self.proxy_tree.insert(
                "",
                "end",
                iid=proxy["id"],
                values=(
                    proxy.get("ip_address"),
                    proxy.get("port"),
                    proxy.get("region", ""),
                    proxy.get("status", "Unknown"),
                    projects,
                    sites,
                    accounts,
                ),
                tags=(tag,),
            )

    def add_proxy(self) -> None:
        entry = self.proxy_entry.get().strip()
        if not entry:
            return
        parts = entry.split(":")
        ip = parts[0]
        port = parts[1] if len(parts) > 1 else None
        user = parts[2] if len(parts) > 2 else None
        pwd = parts[3] if len(parts) > 3 else None
        region = self.lookup_region(ip) if port else None
        database.add_proxy(ip, port, region, "Unknown", user, pwd)
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

    def assign_proxy_to_project_dialog(self) -> None:
        sel = self.proxy_tree.selection()
        if not sel:
            return
        proxy_id = int(sel[0])
        projects = self.load_projects_list()
        if not projects:
            messagebox.showinfo("Projects", "No projects available.")
            return
        dialog = tk.Toplevel(self)
        dialog.title("Assign to Project")
        ttk.Label(dialog, text="Project:").pack(anchor="w", padx=10, pady=10)
        proj_var = tk.StringVar(value=projects[0])
        ttk.Combobox(dialog, values=projects, textvariable=proj_var, state="readonly").pack(
            padx=10, pady=5
        )

        def save() -> None:
            database.assign_proxy_to_project(proxy_id, proj_var.get())
            dialog.destroy()
            self.refresh_proxies()
            self.refresh_project_proxies()

        ttk.Button(dialog, text="Assign", command=save).pack(pady=10)

    def unassign_proxy_from_project_dialog(self) -> None:
        sel = self.proxy_tree.selection()
        if not sel:
            return
        proxy_id = int(sel[0])
        projects = database.get_proxy_projects(proxy_id)
        if not projects:
            messagebox.showinfo("Unassign", "Proxy not assigned to any project.")
            return
        dialog = tk.Toplevel(self)
        dialog.title("Unassign from Project")
        ttk.Label(dialog, text="Project:").pack(anchor="w", padx=10, pady=10)
        proj_var = tk.StringVar(value=projects[0])
        ttk.Combobox(dialog, values=projects, textvariable=proj_var, state="readonly").pack(
            padx=10, pady=5
        )

        def remove() -> None:
            database.remove_proxy_from_project(proxy_id, proj_var.get())
            dialog.destroy()
            self.refresh_proxies()
            self.refresh_project_proxies()

        ttk.Button(dialog, text="Remove", command=remove).pack(pady=10)

    def import_proxies_from_file(self) -> None:
        path = filedialog.askopenfilename()
        if not path:
            return
        count = 0
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split(":")
                ip = parts[0]
                port = parts[1] if len(parts) > 1 else None
                user = parts[2] if len(parts) > 2 else None
                pwd = parts[3] if len(parts) > 3 else None
                region = self.lookup_region(ip) if port else None
                database.add_proxy(ip, port, region, "Unknown", user, pwd)
                count += 1
        messagebox.showinfo("Import", f"Imported {count} proxies.")
        self.refresh_proxies()

    def import_vpn_configs(self) -> None:
        paths = filedialog.askopenfilenames(
            filetypes=[("VPN configs", "*.ovpn *.conf *.nordvpn"), ("All files", "*.*")]
        )
        if not paths:
            return
        count = 0
        for path in paths:
            server = None
            port = None
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("remote"):
                            parts = line.split()
                            if len(parts) >= 2:
                                server = parts[1]
                            if len(parts) >= 3:
                                port = parts[2]
                            break
            except Exception:
                continue
            if server:
                try:
                    ip_lookup = socket.gethostbyname(server)
                except Exception:
                    ip_lookup = server
                region = self.lookup_region(ip_lookup)
                database.add_proxy(server, port, region, "Unknown")
                count += 1
        messagebox.showinfo("Import", f"Imported {count} VPN profiles.")
        self.refresh_proxies()

    def assign_proxy_to_site_dialog(self) -> None:
        sel = self.proxy_tree.selection()
        if not sel:
            return
        proxy_id = int(sel[0])
        sites = database.get_all_sites()
        if not sites:
            messagebox.showinfo("Sites", "No sites available.")
            return
        dialog = tk.Toplevel(self)
        dialog.title("Assign to Site")
        ttk.Label(dialog, text="Site:").pack(anchor="w", padx=10, pady=10)
        site_var = tk.StringVar(value=sites[0])
        ttk.Combobox(dialog, values=sites, textvariable=site_var, state="readonly").pack(
            padx=10, pady=5
        )

        def save() -> None:
            database.assign_proxy_to_site(proxy_id, site_var.get())
            dialog.destroy()
            self.refresh_proxies()

        ttk.Button(dialog, text="Assign", command=save).pack(pady=10)

    def unassign_proxy_from_site_dialog(self) -> None:
        sel = self.proxy_tree.selection()
        if not sel:
            return
        proxy_id = int(sel[0])
        sites = database.get_proxy_sites(proxy_id)
        if not sites:
            messagebox.showinfo("Unassign", "Proxy not assigned to any site.")
            return
        dialog = tk.Toplevel(self)
        dialog.title("Unassign from Site")
        ttk.Label(dialog, text="Site:").pack(anchor="w", padx=10, pady=10)
        site_var = tk.StringVar(value=sites[0])
        ttk.Combobox(dialog, values=sites, textvariable=site_var, state="readonly").pack(
            padx=10, pady=5
        )

        def remove() -> None:
            database.remove_proxy_from_site(proxy_id, site_var.get())
            dialog.destroy()
            self.refresh_proxies()

        ttk.Button(dialog, text="Remove", command=remove).pack(pady=10)

    def assign_proxy_to_account_dialog(self) -> None:
        sel = self.proxy_tree.selection()
        if not sel:
            return
        proxy_id = int(sel[0])
        accounts = database.get_all_accounts()
        if not accounts:
            messagebox.showinfo("Accounts", "No accounts available.")
            return
        dialog = tk.Toplevel(self)
        dialog.title("Assign to Account")
        ttk.Label(dialog, text="Account:").pack(anchor="w", padx=10, pady=10)
        values = [f"{a['id']}: {a['username']}" for a in accounts]
        acc_var = tk.StringVar(value=values[0])
        ttk.Combobox(dialog, values=values, textvariable=acc_var, state="readonly").pack(
            padx=10, pady=5
        )

        def save() -> None:
            acc_id = int(acc_var.get().split(":", 1)[0])
            database.assign_proxy_to_account(proxy_id, acc_id)
            dialog.destroy()
            self.refresh_proxies()

        ttk.Button(dialog, text="Assign", command=save).pack(pady=10)

    def unassign_proxy_from_account_dialog(self) -> None:
        sel = self.proxy_tree.selection()
        if not sel:
            return
        proxy_id = int(sel[0])
        accounts = database.get_proxy_accounts(proxy_id)
        if not accounts:
            messagebox.showinfo("Unassign", "Proxy not assigned to any account.")
            return
        dialog = tk.Toplevel(self)
        dialog.title("Unassign from Account")
        ttk.Label(dialog, text="Account:").pack(anchor="w", padx=10, pady=10)
        values = [f"{a['id']}: {a['username']}" for a in accounts]
        acc_var = tk.StringVar(value=values[0])
        ttk.Combobox(dialog, values=values, textvariable=acc_var, state="readonly").pack(
            padx=10, pady=5
        )

        def remove() -> None:
            acc_id = int(acc_var.get().split(":", 1)[0])
            database.remove_proxy_from_account(proxy_id, acc_id)
            dialog.destroy()
            self.refresh_proxies()

        ttk.Button(dialog, text="Remove", command=remove).pack(pady=10)

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
        manager = SiteManagerFrame(frame, on_update=self.refresh_projects_tab)
        manager.pack(fill="both", expand=True)
        self.site_manager = manager

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
        controls = ttk.Frame(frame)
        controls.pack(fill="x", padx=10, pady=5)
        ttk.Label(controls, text="Project:").pack(side="left")
        self.log_project_var = tk.StringVar(value="All")
        self.log_project_box = ttk.Combobox(
            controls, textvariable=self.log_project_var, state="readonly", width=25
        )
        self.log_project_box.pack(side="left", padx=5)
        self.log_project_box.bind("<<ComboboxSelected>>", lambda _: self.load_logs())
        self.refresh_log_projects()
        self.log_output = ScrolledText(frame, height=20)
        self.log_output.pack(fill="both", expand=True, padx=10, pady=5)
        ttk.Button(frame, text="Refresh", command=self.load_logs).pack(pady=5)
        self.load_logs()

    def load_logs(self) -> None:
        self.log_output.delete("1.0", "end")
        self.log_manager._enforce_limits()
        project = getattr(self, "log_project_var", None)
        project_name = project.get() if project else "All"
        if project_name == "All":
            logs = self.log_manager.get_logs()
            if logs:
                for name, lines in logs.items():
                    self.log_output.insert("end", f"=== {name} ===\n")
                    self.log_output.insert("end", "\n".join(lines[-100:]) + "\n\n")
            else:
                self.log_output.insert("end", "No logs found.")
        else:
            lines = self.log_manager.get_logs(project_name)
            if lines:
                self.log_output.insert("end", "\n".join(lines[-100:]))
            else:
                self.log_output.insert("end", "Log file not found.")

    # --- TOOLS --------------------------------------------------------
    def create_tools_tab(self, frame: ttk.Frame) -> None:
        ttk.Button(frame, text="Solve CAPTCHA", command=self.solve_captcha_dialog).pack(
            anchor="w", padx=10, pady=5
        )
        ttk.Button(frame, text="Spoof Location", command=self.spoof_location_demo).pack(
            anchor="w", padx=10, pady=5
        )
        serp_frame = ttk.LabelFrame(frame, text="SERP Scanner")
        serp_frame.pack(fill="x", padx=10, pady=10)
        self.serp_query_var = tk.StringVar()
        ttk.Entry(serp_frame, textvariable=self.serp_query_var, width=40).pack(side="left", padx=5, pady=5)
        ttk.Button(serp_frame, text="Scan", command=self.run_serp_scan).pack(side="left", padx=5)
        self.serp_results = ScrolledText(frame, height=10)
        self.serp_results.pack(fill="both", expand=True, padx=10, pady=5)

    def solve_captcha_dialog(self) -> None:
        path = filedialog.askopenfilename(title="Select CAPTCHA Image")
        if not path:
            return
        username = simpledialog.askstring("CAPTCHA", "DeathByCaptcha Username:")
        password = simpledialog.askstring("CAPTCHA", "Password:", show="*")
        if not username or not password:
            messagebox.showwarning("CAPTCHA", "Credentials required")
            return
        with open(path, "rb") as f:
            result = solve_captcha(f.read(), username, password)
        messagebox.showinfo("CAPTCHA", result or "Failed to solve")

    def spoof_location_demo(self) -> None:
        loc = get_random_location()
        messagebox.showinfo(
            "Geospoofer", f"Random location: {loc['city']} ({loc['lat']}, {loc['lon']})"
        )

    def run_serp_scan(self) -> None:
        query = self.serp_query_var.get().strip()
        if not query:
            messagebox.showwarning("SERP Scanner", "Please enter a query")
            return
        try:
            results = check_review_visibility(query)
            self.serp_results.delete("1.0", "end")
            self.serp_results.insert("end", "\n".join(results) or "No results")
        except Exception as e:
            logger.error(f"SERP scan failed: {e}")
            messagebox.showerror("SERP Scanner", str(e))

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
