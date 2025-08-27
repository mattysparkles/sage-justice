from selenium import webdriver
import pickle
import os

def save_cookies(driver, path="accounts/session_cookies.pkl"):
    with open(path, "wb") as file:
        pickle.dump(driver.get_cookies(), file)

def load_cookies(driver, path="accounts/session_cookies.pkl"):
    if os.path.exists(path):
        with open(path, "rb") as file:
            cookies = pickle.load(file)
            for cookie in cookies:
                driver.add_cookie(cookie)
