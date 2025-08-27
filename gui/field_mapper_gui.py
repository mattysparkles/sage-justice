import tkinter as tk
from tkinter import simpledialog, messagebox
from tools.field_mapper import FieldMapper

class FieldMapperGUI:
    def __init__(self, driver):
        self.driver = driver
        self.mapper = FieldMapper(driver)
        self.root = tk.Tk()
        self.root.title("Field Mapper")
        self.root.geometry("300x200")
        self.build_ui()

    def build_ui(self):
        tk.Button(self.root, text="Map New Field", command=self.prompt_field).pack(pady=10)
        tk.Button(self.root, text="Save Mapping", command=self.mapper.save_map).pack(pady=5)
        tk.Button(self.root, text="Exit", command=self.root.quit).pack(pady=5)

    def prompt_field(self):
        field_name = simpledialog.askstring("Field", "Enter field name:")
        strategy = simpledialog.askstring("Strategy", "Enter By strategy (ID, NAME, XPATH):")
        value = simpledialog.askstring("Value", "Enter selector value:")
        self.mapper.map_field(field_name, strategy.upper(), value)
        messagebox.showinfo("Mapped", f"Mapped {field_name} via {strategy.upper()}")

    def run(self):
        self.root.mainloop()