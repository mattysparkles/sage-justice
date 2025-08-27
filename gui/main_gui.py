import tkinter as tk
from tkinter import scrolledtext, filedialog
from core.review_generator import generate_reviews

class ReviewGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Sage Justice – Review Generator")
        self.setup_ui()

    def setup_ui(self):
        tk.Label(self.root, text="Base Review Prompt").pack()
        self.prompt_entry = scrolledtext.ScrolledText(self.root, height=10)
        self.prompt_entry.pack(fill="both", expand=True)

        tk.Button(self.root, text="Generate Reviews", command=self.generate).pack(pady=10)
        self.output_area = scrolledtext.ScrolledText(self.root, height=15)
        self.output_area.pack(fill="both", expand=True)

    def generate(self):
        prompt = self.prompt_entry.get("1.0", "end").strip()
        reviews = generate_reviews(prompt, count=5)
        self.output_area.delete("1.0", "end")
        for review in reviews:
            self.output_area.insert("end", review + "\n\n")

if __name__ == "__main__":
    root = tk.Tk()
    app = ReviewGUI(root)
    root.mainloop()
