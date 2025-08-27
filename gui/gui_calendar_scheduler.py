import tkinter as tk
from tkinter import messagebox, scrolledtext
import calendar
from datetime import datetime, timedelta
from core.style_generator import generate_styled_reviews
from core.drip_scheduler import schedule_reviews

class CalendarScheduler:
    def __init__(self, root):
        self.root = root
        self.root.title("Sage Justice – Visual Calendar Scheduler")
        self.today = datetime.today()
        self.scheduled = {}

        self.build_ui()

    def build_ui(self):
        self.cal_frame = tk.Frame(self.root)
        self.cal_frame.pack()

        self.build_calendar(self.today.year, self.today.month)

        # Review and prompt section
        self.prompt = scrolledtext.ScrolledText(self.root, height=4)
        self.prompt.pack(fill="x", padx=10, pady=5)
        self.prompt.insert("end", "Enter your base review prompt here.")

        self.tone_var = tk.StringVar(value="professional")
        tones = ["professional", "emotional", "rhetorical", "legalese", "outraged"]
        tk.OptionMenu(self.root, self.tone_var, *tones).pack()

        self.template_entry = tk.Entry(self.root)
        self.template_entry.insert(0, "templates/google_review.json")
        self.template_entry.pack(fill="x", padx=10, pady=5)

        tk.Button(self.root, text="Schedule Selected Date", command=self.schedule_selected).pack(pady=5)

        self.output = scrolledtext.ScrolledText(self.root, height=6)
        self.output.pack(fill="x", padx=10, pady=5)

    def build_calendar(self, year, month):
        tk.Label(self.cal_frame, text=f"{calendar.month_name[month]} {year}", font=("Helvetica", 14)).grid(row=0, column=0, columnspan=7)

        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for i, day in enumerate(days):
            tk.Label(self.cal_frame, text=day).grid(row=1, column=i)

        month_days = calendar.monthcalendar(year, month)
        self.date_buttons = {}

        for week_num, week in enumerate(month_days):
            for day_num, day in enumerate(week):
                if day != 0:
                    btn = tk.Button(self.cal_frame, text=str(day), width=4,
                                    command=lambda d=day: self.select_day(d))
                    btn.grid(row=week_num+2, column=day_num)
                    self.date_buttons[day] = btn

        self.selected_day = self.today.day
        self.highlight_selected_day()

    def highlight_selected_day(self):
        for day, btn in self.date_buttons.items():
            btn.config(relief="raised")
        if self.selected_day in self.date_buttons:
            self.date_buttons[self.selected_day].config(relief="sunken")

    def select_day(self, day):
        self.selected_day = day
        self.highlight_selected_day()

    def schedule_selected(self):
        prompt = self.prompt.get("1.0", "end").strip()
        tone = self.tone_var.get()
        reviews = generate_styled_reviews(prompt, count=1, tone=tone)
        date_str = f"{self.today.year}-{self.today.month:02d}-{self.selected_day:02d}"
        template = self.template_entry.get()
        self.scheduled[date_str] = (reviews[0], template)
        self.output.insert("end", f"[Scheduled for {date_str}]: {reviews[0][:100]}...
")
        # Optional: tie this into a true delay-timed queue later

if __name__ == "__main__":
    root = tk.Tk()
    app = CalendarScheduler(root)
    root.mainloop()
