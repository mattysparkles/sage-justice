"""Main Tkinter GUI for Sage Justice dashboard."""

import json
import tkinter as tk
from datetime import datetime, timedelta
from pathlib import Path
from tkinter import messagebox, simpledialog
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

from core.account_manager import load_accounts
from core.config_loader import load_json_config
from core.review_generator import generate_reviews
from core.review_spinner import generate_variants
from core.site_config_loader import SiteConfigLoader
from scheduler.schedule_engine import ReviewScheduler
from proxy.manager import ProxyManager
from gui.proxy_manager_gui import ProxyManagerFrame

SETTINGS_PATH = Path("config/settings.local.json")
DEFAULT_SETTINGS_PATH = Path("config/settings.json")
LOG_PATH = Path("logs/app.log")
POST_LOG_PATH = Path("logs/post_log.csv")
ACCOUNTS_PATH = Path("accounts/accounts.json")
TEMPLATES_DIR = Path("templates")
PROJECTS_PATH = Path("config/project.json")
QUEUED_DIR = Path("output/queued_reviews")


class GuardianDeck(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Guardian Deck")
        self.geometry("900x700")
        self.scheduler = ReviewScheduler()
        self.create_widgets()

    # --- UI SETUP -----------------------------------------------------
    def create_widgets(self) -> None:
        ttk.Label(self, text="SAGE JUSTICE - Guardian Deck", font=("Helvetica", 16)).pack(pady=10)

        notebook = ttk.Notebook(self)
        notebook.pack(expand=True, fill="both")

        tabs = {
            "Review Generator": self.create_review_tab,
            "Templates": self.create_templates_tab,
            "Accounts": self.create_accounts_tab,
            "Proxies": self.create_proxy_tab,
            "Sites": self.create_sites_tab,
            "Schedule": self.create_scheduler_tab,
            "Logs": self.create_logs_tab,
            "Settings": self.create_settings_tab,
        }

        for name, creator in tabs.items():
            frame = ttk.Frame(notebook)
            notebook.add(frame, text=name)
            creator(frame)

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
        self.review_container = ttk.Frame(self.review_canvas)
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
        prompt = self.prompt_text.get("1.0", "end").strip()
        if not prompt:
            messagebox.showwarning("Input", "Please provide a prompt.")
            return
        count = self.count_var.get()
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
        self.template_listbox = tk.Listbox(frame)
        self.template_listbox.pack(side="left", fill="y", padx=5, pady=5)
        self.template_editor = ScrolledText(frame)
        self.template_editor.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        btns = ttk.Frame(frame)
        btns.pack(fill="x")
        ttk.Button(btns, text="Load", command=self.load_template).pack(side="left", padx=5)
        ttk.Button(btns, text="Save", command=self.save_template).pack(side="left")
        self.refresh_templates()

    def refresh_templates(self) -> None:
        self.template_listbox.delete(0, tk.END)
        for file in TEMPLATES_DIR.glob("*.json"):
            self.template_listbox.insert(tk.END, file.name)

    def load_template(self) -> None:
        sel = self.template_listbox.curselection()
        if not sel:
            return
        path = TEMPLATES_DIR / self.template_listbox.get(sel[0])
        data = json.dumps(json.load(open(path, "r", encoding="utf-8")), indent=2)
        self.template_editor.delete("1.0", "end")
        self.template_editor.insert("1.0", data)
        self.current_template_path = path

    def save_template(self) -> None:
        if not hasattr(self, "current_template_path"):
            messagebox.showinfo("Template", "No template loaded.")
            return
        try:
            data = json.loads(self.template_editor.get("1.0", "end"))
            with open(self.current_template_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            messagebox.showinfo("Template", "Template saved.")
        except json.JSONDecodeError:
            messagebox.showerror("Template", "Invalid JSON")

    # --- ACCOUNTS -----------------------------------------------------
    def create_accounts_tab(self, frame: ttk.Frame) -> None:
        self.accounts_editor = ScrolledText(frame)
        self.accounts_editor.pack(fill="both", expand=True, padx=10, pady=5)
        ttk.Button(frame, text="Save", command=self.save_accounts).pack(pady=5)
        try:
            data = json.dumps(load_accounts(ACCOUNTS_PATH), indent=2)
            self.accounts_editor.insert("1.0", data)
        except FileNotFoundError:
            self.accounts_editor.insert("1.0", "[]")

    def save_accounts(self) -> None:
        try:
            data = json.loads(self.accounts_editor.get("1.0", "end"))
            with open(ACCOUNTS_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            messagebox.showinfo("Accounts", "Accounts saved.")
        except json.JSONDecodeError:
            messagebox.showerror("Accounts", "Invalid JSON")

    # --- PROXIES ------------------------------------------------------
    def create_proxy_tab(self, frame: ttk.Frame) -> None:
        manager = ProxyManager(path="proxy/proxy_list.txt")
        proxy_frame = ProxyManagerFrame(frame, manager)
        proxy_frame.pack(fill="both", expand=True, padx=10, pady=5)

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
        self.schedule_listbox = tk.Listbox(frame)
        self.schedule_listbox.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        controls = ttk.Frame(frame)
        controls.pack(side="left", fill="y", padx=5, pady=5)

        form = ttk.Frame(controls)
        form.pack(fill="x")
        ttk.Label(form, text="Site:").grid(row=0, column=0, sticky="w")
        self.site_entry = ttk.Entry(form)
        self.site_entry.grid(row=0, column=1, sticky="ew")
        ttk.Label(form, text="Prompt:").grid(row=1, column=0, sticky="nw")
        self.prompt_entry = ScrolledText(form, width=20, height=4)
        self.prompt_entry.grid(row=1, column=1, sticky="ew")
        ttk.Label(form, text="Interval (min):").grid(row=2, column=0, sticky="w")
        self.interval_var = tk.IntVar(value=60)
        ttk.Spinbox(form, from_=1, to=1440, textvariable=self.interval_var, width=5).grid(row=2, column=1, sticky="w")
        form.columnconfigure(1, weight=1)

        btns = ttk.Frame(controls)
        btns.pack(pady=5)
        ttk.Button(btns, text="Add", command=self.add_schedule).pack(side="left", padx=5)
        ttk.Button(btns, text="Remove", command=self.remove_schedule).pack(side="left", padx=5)
        ttk.Button(btns, text="Start", command=self.start_scheduler).pack(side="left", padx=5)
        ttk.Button(btns, text="Stop", command=self.stop_scheduler).pack(side="left", padx=5)

        self.scheduler_status = ttk.Label(controls, text="Inactive", foreground="red")
        self.scheduler_status.pack(anchor="w", pady=5)
        self.refresh_schedule()

    def refresh_schedule(self) -> None:
        self.schedule_listbox.delete(0, tk.END)
        for task in self.scheduler.schedule:
            self.schedule_listbox.insert(
                tk.END, f"{task['site']} every {task['interval_minutes']} min"
            )

    def add_schedule(self) -> None:
        site = self.site_entry.get().strip()
        prompt = self.prompt_entry.get("1.0", "end").strip()
        interval = self.interval_var.get()
        if not site or not prompt:
            messagebox.showwarning("Schedule", "Site and prompt required.")
            return
        task = {
            "site": site,
            "prompt": prompt,
            "interval_minutes": interval,
            "next_run": (datetime.now() + timedelta(minutes=interval)).isoformat(),
        }
        self.scheduler.schedule.append(task)
        self.scheduler.save_schedule()
        self.refresh_schedule()
        messagebox.showinfo("Schedule", "Task added.")

    def remove_schedule(self) -> None:
        sel = self.schedule_listbox.curselection()
        if not sel:
            return
        self.scheduler.schedule.pop(sel[0])
        self.scheduler.save_schedule()
        self.refresh_schedule()

    def start_scheduler(self) -> None:
        if not getattr(self.scheduler, "thread", None):
            self.scheduler.start()
        self.scheduler_status.config(text="Active", foreground="green")

    def stop_scheduler(self) -> None:
        # ReviewScheduler has no hard stop; flag is informational only
        self.scheduler_status.config(text="Inactive", foreground="red")

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
