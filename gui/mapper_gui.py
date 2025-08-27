import tkinter as tk
from tkinter import messagebox, filedialog
from selenium import webdriver
from selenium.webdriver.common.by import By
import json

class MapperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Review Site Mapper")
        self.fields = {}

        tk.Label(root, text="Site Name:").grid(row=0, column=0)
        self.site_name_entry = tk.Entry(root)
        self.site_name_entry.grid(row=0, column=1)

        tk.Label(root, text="Review URL:").grid(row=1, column=0)
        self.url_entry = tk.Entry(root)
        self.url_entry.grid(row=1, column=1)

        tk.Button(root, text="Add Field", command=self.add_field).grid(row=2, column=0, pady=10)
        tk.Button(root, text="Save Template", command=self.save_template).grid(row=2, column=1, pady=10)

        self.field_frame = tk.Frame(root)
        self.field_frame.grid(row=3, column=0, columnspan=2)

    def add_field(self):
        field_row = len(self.fields)
        field_name = tk.Entry(self.field_frame)
        field_selector = tk.Entry(self.field_frame)
        field_type = tk.Entry(self.field_frame)

        field_name.grid(row=field_row, column=0)
        field_selector.grid(row=field_row, column=1)
        field_type.grid(row=field_row, column=2)

        self.fields[field_row] = {
            "name": field_name,
            "selector": field_selector,
            "type": field_type
        }

    def save_template(self):
        site_name = self.site_name_entry.get()
        url = self.url_entry.get()
        field_data = {}

        for field in self.fields.values():
            name = field["name"].get()
            selector = field["selector"].get()
            ftype = field["type"].get()
            if name and selector and ftype:
                field_data[name] = {"selector": selector, "type": ftype}

        template = {
            "site_name": site_name,
            "url": url,
            "fields": field_data
        }

        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if path:
            with open(path, "w") as f:
                json.dump(template, f, indent=4)
            messagebox.showinfo("Saved", "Template saved successfully!")

if __name__ == "__main__":
    root = tk.Tk()
    app = MapperGUI(root)
    root.mainloop()