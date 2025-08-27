from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import time

def highlight_element(driver, element):
    driver.execute_script("arguments[0].style.border='3px solid red'", element)

def auto_detect_fields(driver):
    print("Detecting textareas and buttons...")
    textareas = driver.find_elements(By.TAG_NAME, "textarea")
    buttons = driver.find_elements(By.TAG_NAME, "button")

    print(f"Found {len(textareas)} textareas and {len(buttons)} buttons.")
    for idx, el in enumerate(textareas + buttons):
        try:
            highlight_element(driver, el)
            print(f"[{idx}] - {el.tag_name}: {el.get_attribute('outerHTML')[:120]}")
        except Exception:
            continue
    print("Use this to find likely XPaths.")
