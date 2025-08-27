"""Tkinter dashboard wiring multiple Sage Justice modules."""

from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox

from core.style_generator import generate_styled_reviews, tones
from core.async_queue import AsyncReviewQueue
from core.proxy_manager import get_random_proxy
from core.account_manager import get_random_account

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

        self._build_schedule_tab()
        self._build_logs_tab()
        self._build_template_tab()
        self._build_settings_tab()

        self.status_var = tk.StringVar(value="Ready")
        tk.Label(root, textvariable=self.status_var, relief="sunken", anchor="w").pack(
            fill="x", side="bottom"
        )

        self._refresh_queue_view()
        self._refresh_logs()

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

