import tkinter as tk
from tkinter import messagebox
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

def run_guided_mapper(parent, url, field_prompts=None):
    """Launch a simple guided wizard to capture form field selectors.

    Args:
        parent: tk widget to attach dialogs to.
        url: Page URL to open in the browser.
        field_prompts: mapping of field keys to human-readable descriptions.
    Returns:
        dict mapping field keys to CSS selectors.
    """
    if field_prompts is None:
        field_prompts = {
            "review_text": "review text area",
            "submit_button": "submit button",
        }
    try:
        driver = webdriver.Chrome()
    except WebDriverException as exc:
        messagebox.showerror("Guided Mapper", f"Unable to launch browser: {exc}")
        return {}
    driver.get(url)
    driver.execute_script(CLICK_LISTENER + CSS_PATH_FUNC)
    mapping = {}

    for key, label in field_prompts.items():
        top = tk.Toplevel(parent)
        top.title("Map Field")
        tk.Label(top, text=f"Click the {label} in the browser, then click Capture.").pack(padx=10, pady=10)
        result: dict[str, str] = {}

        def capture() -> None:
            selector = driver.execute_script("return cssPath(window._sj_last);")
            result["selector"] = selector
            top.destroy()

        tk.Button(top, text="Capture", command=capture).pack(pady=5)
        top.wait_window()
        selector = result.get("selector")
        if selector:
            mapping[key] = selector
    driver.quit()
    return mapping
