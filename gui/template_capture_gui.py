"""Interactive template capture utility using Selenium."""

from __future__ import annotations

import json
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
from tkinter.scrolledtext import ScrolledText

from selenium import webdriver
from selenium.common.exceptions import WebDriverException


CSS_PATH_FUNC = """
function cssPath(el){
  if(!(el instanceof Element)) return '';
  var path = [];
  while(el.nodeType === Node.ELEMENT_NODE){
    var selector = el.nodeName.toLowerCase();
    if(el.id){
      selector += '#' + el.id;
      path.unshift(selector);
      break;
    }else{
      var sib = el, nth = 1;
      while(sib = sib.previousElementSibling) nth++;
      selector += ':nth-of-type(' + nth + ')';
    }
    path.unshift(selector);
    el = el.parentNode;
  }
  return path.join(' > ');
}
"""

CLICK_LISTENER = """
window._sj_last = null;
document.addEventListener('click', function(e){
  e.preventDefault();
  e.stopPropagation();
  window._sj_last = e.target;
}, true);
"""


class TemplateCapture(tk.Toplevel):
    """Window for capturing click-based template steps."""

    def __init__(self, master: tk.Widget):
        super().__init__(master)
        self.title("Template Capture")
        self.geometry("500x500")
        self.driver: webdriver.Chrome | None = None
        self.steps: list[dict[str, str]] = []
        self.url_var = tk.StringVar()

        top = tk.Frame(self)
        top.pack(fill="x", pady=5)
        tk.Label(top, text="Start URL:").pack(side="left")
        tk.Entry(top, textvariable=self.url_var).pack(side="left", fill="x", expand=True)
        tk.Button(top, text="Start", command=self.start_capture).pack(side="left", padx=4)

        self.text = ScrolledText(self, state="disabled")
        self.text.pack(fill="both", expand=True, padx=5, pady=5)

        tk.Label(
            self,
            text="When you reach the submit button stage click 'Mark Submit'",
            font=("Helvetica", 10, "bold"),
        ).pack(pady=(0, 2))
        btns = tk.Frame(self)
        btns.pack(fill="x")
        tk.Button(btns, text="Mark Submit", command=self.mark_submit).pack(side="left", padx=2)
        tk.Button(btns, text="Save", command=self.save).pack(side="right", padx=2)

        self.protocol("WM_DELETE_WINDOW", self.close)

    # ------------------------------------------------------------------
    def start_capture(self) -> None:
        url = self.url_var.get().strip()
        try:
            self.driver = webdriver.Chrome()
        except WebDriverException as exc:
            messagebox.showerror("Template Capture", str(exc), parent=self)
            return
        self.driver.get(url)
        self.driver.execute_script(CLICK_LISTENER + CSS_PATH_FUNC)
        self.after(500, self.poll_browser)

    def poll_browser(self) -> None:
        if not self.driver:
            return
        selector = self.driver.execute_script(
            "var el = window._sj_last; if(!el) return ''; window._sj_last=null; return cssPath(el);"
        )
        if selector:
            name = simpledialog.askstring("Step", "Name this step:", parent=self)
            if name:
                self.steps.append({"name": name, "selector": selector})
                self.refresh_text()
        self.after(500, self.poll_browser)

    def refresh_text(self) -> None:
        self.text.config(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("end", json.dumps(self.steps, indent=2))
        self.text.config(state="disabled")

    def mark_submit(self) -> None:
        if self.steps:
            self.steps[-1]["submit"] = True
            self.refresh_text()

    def save(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".json")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.steps, f, indent=2)

    def close(self) -> None:
        if self.driver:
            self.driver.quit()
        self.destroy()
