
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

from proxy.manager import ProxyManager
from gui.proxy_manager_gui import ProxyManagerFrame

class GuardianDeck(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Guardian Deck")
        self.geometry("800x600")
        self.create_widgets()

    def create_widgets(self):
        ttk.Label(self, text="SAGE JUSTICE - Guardian Deck", font=("Helvetica", 16)).pack(pady=10)
        
        notebook = ttk.Notebook(self)
        notebook.pack(expand=True, fill='both')

        tabs = {
            "Review Queue": self.create_review_tab,
            "Templates": self.create_templates_tab,
            "Proxy / Account": self.create_proxy_tab,
            "Scheduler": self.create_scheduler_tab,
            "Logs": self.create_logs_tab,
        }

        for tab_name, creator in tabs.items():
            frame = ttk.Frame(notebook)
            notebook.add(frame, text=tab_name)
            creator(frame)

    def create_review_tab(self, frame):
        ttk.Label(frame, text="Queued Reviews:").pack(anchor='w')
        self.review_list = ScrolledText(frame, height=10)
        self.review_list.pack(fill='both', expand=True, padx=10, pady=5)

    def create_templates_tab(self, frame):
        ttk.Label(frame, text="Available Templates:").pack(anchor='w')
        self.template_list = ScrolledText(frame, height=10)
        self.template_list.pack(fill='both', expand=True, padx=10, pady=5)

    def create_proxy_tab(self, frame):
        manager = ProxyManager(path="proxy/proxy_list.txt")
        proxy_frame = ProxyManagerFrame(frame, manager)
        proxy_frame.pack(fill='both', expand=True, padx=10, pady=5)

    def create_scheduler_tab(self, frame):
        ttk.Label(frame, text="Scheduler Status:").pack(anchor='w')
        self.scheduler_status = ttk.Label(frame, text="Inactive", foreground="red")
        self.scheduler_status.pack(anchor='w', padx=10)
        ttk.Button(frame, text="Start Scheduler", command=lambda: self.scheduler_status.config(text="Active", foreground="green")).pack(pady=5)
        ttk.Button(frame, text="Stop Scheduler", command=lambda: self.scheduler_status.config(text="Inactive", foreground="red")).pack(pady=5)

    def create_logs_tab(self, frame):
        ttk.Label(frame, text="System Logs:").pack(anchor='w')
        self.log_output = ScrolledText(frame, height=10)
        self.log_output.pack(fill='both', expand=True, padx=10, pady=5)


if __name__ == "__main__":
    app = GuardianDeck()
    app.mainloop()
