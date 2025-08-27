import tkinter as tk
from tkinter import ttk, scrolledtext
import datetime
from core.style_generator import generate_styled_reviews
from core.drip_scheduler import schedule_reviews

class SchedulerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Sage Justice – Dripfeed Scheduler")

        # Prompt input
        tk.Label(root, text="Base Review Prompt").pack()
        self.prompt_entry = scrolledtext.ScrolledText(root, height=5)
        self.prompt_entry.pack(fill="both", expand=True)

        # Tone dropdown
        tk.Label(root, text="Tone").pack()
        self.tone_var = tk.StringVar(value="professional")
        tone_options = ["professional", "emotional", "rhetorical", "legalese", "outraged"]
        self.tone_menu = ttk.Combobox(root, textvariable=self.tone_var, values=tone_options, state="readonly")
        self.tone_menu.pack()

        # Site template input
        tk.Label(root, text="Template Path").pack()
        self.template_entry = tk.Entry(root)
        self.template_entry.insert(0, "templates/google_review.json")
        self.template_entry.pack(fill="x")

        # Generate & Schedule
        tk.Button(root, text="Preview Reviews", command=self.preview_reviews).pack(pady=5)
        self.review_output = scrolledtext.ScrolledText(root, height=10)
        self.review_output.pack(fill="both", expand=True)

        tk.Label(root, text="Delay between reviews (sec)").pack()
        self.delay_spin = tk.Spinbox(root, from_=60, to=86400, increment=60)
        self.delay_spin.pack()

        tk.Button(root, text="Schedule Dripfeed", command=self.schedule_reviews).pack(pady=10)

    def preview_reviews(self):
        prompt = self.prompt_entry.get("1.0", "end").strip()
        tone = self.tone_var.get()
        reviews = generate_styled_reviews(prompt, count=3, tone=tone)
        self.review_output.delete("1.0", "end")
        for r in reviews:
            self.review_output.insert("end", r + "\n\n")
        self.reviews = reviews

    def schedule_reviews(self):
        try:
            delay = int(self.delay_spin.get())
        except ValueError:
            delay = 3600
        pairs = [(r, self.template_entry.get()) for r in getattr(self, "reviews", [])]
        schedule_reviews(pairs, delay_seconds=delay)
        self.review_output.insert("end", "\n[Scheduled reviews for dripfeed...]\n")

if __name__ == "__main__":
    root = tk.Tk()
    app = SchedulerGUI(root)
    root.mainloop()
