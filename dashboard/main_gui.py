import json
import tkinter as tk
from pathlib import Path
from tkinter import messagebox
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

SETTINGS_PATH = Path("config/settings.json")
LOG_PATH = Path("logs/app.log")
ACCOUNTS_PATH = Path("accounts/accounts.json")
TEMPLATES_DIR = Path("templates")


class GuardianDeck(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Guardian Deck")
        self.geometry("900x700")
        self.scheduler: ReviewScheduler | None = None
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

        self.review_output = ScrolledText(frame, height=15)
        self.review_output.pack(fill="both", expand=True, padx=10, pady=5)

    def run_generation(self) -> None:
        prompt = self.prompt_text.get("1.0", "end").strip()
        if not prompt:
            messagebox.showwarning("Input", "Please provide a prompt.")
            return
        count = self.count_var.get()
        reviews = generate_reviews(prompt, count=count)
        if self.rewrite_var.get():
            spun = []
            for review in reviews:
                variants = generate_variants(review, n=1)
                spun.append(variants[0] if variants else review)
            reviews = spun
        self.review_output.delete("1.0", "end")
        for r in reviews:
            self.review_output.insert("end", r + "\n\n")

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
        self.scheduler_status = ttk.Label(frame, text="Inactive", foreground="red")
        self.scheduler_status.pack(anchor="w", padx=10, pady=5)
        ttk.Button(frame, text="Start", command=self.start_scheduler).pack(side="left", padx=5)
        ttk.Button(frame, text="Stop", command=self.stop_scheduler).pack(side="left", padx=5)

    def start_scheduler(self) -> None:
        if not self.scheduler:
            self.scheduler = ReviewScheduler()
            self.scheduler.start()
        self.scheduler_status.config(text="Active", foreground="green")

    def stop_scheduler(self) -> None:
        if self.scheduler and hasattr(self.scheduler, "schedule"):
            # No direct stop, but we can drop reference; thread will exit when program closes
            self.scheduler = None
        self.scheduler_status.config(text="Inactive", foreground="red")

    # --- LOGS ---------------------------------------------------------
    def create_logs_tab(self, frame: ttk.Frame) -> None:
        self.log_output = ScrolledText(frame, height=20)
        self.log_output.pack(fill="both", expand=True, padx=10, pady=5)
        ttk.Button(frame, text="Refresh", command=self.load_logs).pack(pady=5)
        self.load_logs()

    def load_logs(self) -> None:
        self.log_output.delete("1.0", "end")
        if LOG_PATH.exists():
            lines = LOG_PATH.read_text(encoding="utf-8").splitlines()[-100:]
            self.log_output.insert("end", "\n".join(lines))
        else:
            self.log_output.insert("end", "Log file not found.")

    # --- SETTINGS -----------------------------------------------------
    def create_settings_tab(self, frame: ttk.Frame) -> None:
        ttk.Label(frame, text="OpenAI API Key:").pack(anchor="w", padx=10, pady=5)
        self.api_key_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.api_key_var, width=60).pack(padx=10, pady=5)
        ttk.Button(frame, text="Save", command=self.save_settings).pack(pady=5)
        self.load_settings()

    def load_settings(self) -> None:
        try:
            data = load_json_config(SETTINGS_PATH)
            self.api_key_var.set(data.get("openai_api_key", ""))
        except FileNotFoundError:
            self.api_key_var.set("")

    def save_settings(self) -> None:
        data = {"openai_api_key": self.api_key_var.get()}
        SETTINGS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
        messagebox.showinfo("Settings", "Settings saved.")


if __name__ == "__main__":
    app = GuardianDeck()
    app.mainloop()
