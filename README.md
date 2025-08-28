# Sage Justice

**AI-Powered Review Automation for Truthful, Drip-Fed Accountability**  
*Built by Sparkles & Sage — Justice is a dish best served... continuously.*

---

## 📘 Table of Contents
1. [What Is Sage Justice?](#what-is-sage-justice)
2. [Who Is This Guide For?](#who-is-this-guide-for)
3. [Before You Begin](#before-you-begin)
4. [Step-by-Step Installation](#step-by-step-installation)
5. [Running the Program](#running-the-program)
6. [Understanding the Interface](#understanding-the-interface)
7. [Feature Walkthrough](#feature-walkthrough)
8. [Advanced Tools](#advanced-tools)
9. [How the Automation Works](#how-the-automation-works)
10. [Troubleshooting & FAQ](#troubleshooting--faq)
11. [Folder Structure](#folder-structure)
12. [Roadmap](#roadmap)
13. [Legal & Contributions](#legal--contributions)

---

## What Is Sage Justice?
Sage Justice is a software suite that automatically publishes **factual**, **unique**, and **slowly drip-fed** reviews to multiple websites. It was originally created to highlight unethical professional conduct, making sure honest experiences reach the public over time.

The system uses artificial intelligence (AI) to rewrite reviews without changing their meaning. It rotates user accounts and network addresses, and it schedules posts gradually so they appear natural.

---

## Who Is This Guide For?
This guide assumes **no prior computer knowledge**. Every step is written for people who have never used a terminal, installed software, or edited a file. If you already know how to use a computer, feel free to skim the basics.

---

## Before You Begin
### 1. Hardware and Internet
- A computer running Windows 10+, macOS 11+, or a modern Linux distribution.
- A stable internet connection.

### 2. Software to Install
We will install these together during the setup:
- **Git** – a tool to download the project.
- **Python 3.11+** – the language the program is written in.
- **Google Chrome** – required for automated web browsing.

---

## Step-by-Step Installation
### Step 1 – Open a Terminal
A *terminal* is a text-based window for giving commands to the computer.
- **Windows**: Press `Start`, type `cmd`, and press `Enter`.
- **macOS**: Open `Finder` → `Applications` → `Utilities` → `Terminal`.
- **Linux**: Press `Ctrl` + `Alt` + `T`.

### Step 2 – Install Git
- **Windows**: Visit [git-scm.com](https://git-scm.com/download/win), download the installer, and run it with default options.
- **macOS**: In the terminal, type `xcode-select --install` and follow the prompts.
- **Linux**: In the terminal, type `sudo apt install git` and press `Enter`.

### Step 3 – Install Python
- Go to [python.org/downloads](https://www.python.org/downloads/) and download the latest version for your operating system.
- Run the installer. **On Windows, make sure to check the box that says “Add Python to PATH.”**

### Step 4 – Install Google Chrome
- Download from [google.com/chrome](https://www.google.com/chrome/).
- Run the installer with default options.

### Step 5 – Download Sage Justice
In your terminal, type:
```bash
git clone https://github.com/mattysparkles/sage-justice.git
cd sage-justice
```
This downloads the project folder and moves you into it.

### Step 6 – Install Python Dependencies
Stay in the terminal and run:
```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```
If `pip` is not recognized, replace `python` with `python3`.
These commands download and install all libraries that Sage Justice needs.

### Step 7 – Add Your OpenAI API Key
The program uses OpenAI’s GPT models. You need an API key.
1. Create an account at [platform.openai.com](https://platform.openai.com/).
2. Generate a new API key and copy it.
3. In your terminal, type:
   ```bash
   mkdir -p config
   nano config/settings.local.json
   ```
4. Paste the following, replacing `YOURKEY` with your key:
   ```json
   {
     "openai_api_key": "sk-YOURKEY"
   }
   ```
5. Press `Ctrl` + `O` then `Enter` to save, and `Ctrl` + `X` to exit.
6. To double‑check, run `cat config/settings.local.json` and make sure your key is visible.

---

## Running the Program
1. Open your terminal and confirm you are in the project folder by typing `ls` (macOS/Linux) or `dir` (Windows). You should see files like `README.md` and folders named `core` and `dashboard`.
2. Start the program:
   ```bash
   python dashboard/main_gui.py
   ```
   If this fails, try `python3` instead of `python`.
3. After a few seconds a window titled **Guardian Deck** appears. Keep the terminal open; it shows additional messages.

**First-time tip:** If nothing happens or you see an error, read the troubleshooting section below.

---

## Understanding the Interface
When you launch the program a window opens with a small **overview panel** at the top. It shows how many reviews were posted today and the health of your accounts and proxies in simple pie charts. Below the panel is a row of tabs that group every feature. Click a tab to switch sections.

| Tab | What It Does |
| --- | --- |
| **Review Generator** | Write or rewrite reviews with AI. |
| **Templates** | Configure how different websites accept reviews. |
| **Accounts** | Store usernames and passwords for each site. |
| **Proxies** | List IP addresses to hide your location. |
| **Sites** | View all supported review platforms. |
| **Schedule** | Plan when reviews should be posted. |
| **Jobs** | Monitor queued tasks and retry failures. |
| **Logs** | Read records of what has been posted. |
| **Settings** | Save your OpenAI key and choose the AI model. |

Each tab has buttons and text fields. Move your mouse over a field, click it, and type. Buttons perform actions when clicked.

---

## Feature Walkthrough
### 1. Review Generator
The Review Generator creates fresh text or rewrites existing reviews.
1. Click the **Review Generator** tab.
2. Type the situation or story you want to tell into the **Prompt** box.
3. Use the **Count** spinner to choose how many unique reviews you want (1–10).
4. Adjust the **Formality** and **Emotion** sliders to set tone on a scale from 0 (none) to 10 (high).
5. Optional: Check **Rewrite** to spin the text using the AI's variant engine.
6. Click **Generate**. New reviews appear in the list below.
7. Click individual reviews to select or deselect them. Selected reviews turn blue.
8. Use **Assign & Queue** to save selected reviews into a project for later scheduling. They are stored under `output/queued_reviews/`.
9. To keep a copy on your computer immediately, click **Save** (or use your operating system's copy‑paste).

### 2. Templates
Templates tell the program where to click and what to fill out on each review website.
1. Click **Templates**.
2. The Template Manager shows existing templates on the left and details on the right.
3. To make a new template, choose **New**, enter the website URL, and follow the prompts to map each form field. The field auto‑detector attempts to guess inputs for you.
4. Test the mapping inside the manager to ensure the cursor jumps to the correct fields.
5. Save templates as JSON files in the `templates/` folder. You can edit these files later with any text editor if needed.

### 3. Accounts
The program rotates through many login credentials to keep posting natural.
1. Click **Accounts**.
2. Press **Add Account** and enter username, password, and an optional category like “healthcare” or “finance.”
3. Accounts are listed with a health status (green = healthy, orange = warning, red = failed).
4. Select a row and use **Delete Selected** to remove it or **Mark as Failed** if the login stopped working.
5. Account data is stored inside the internal SQLite database `core/reviewbot.db`; keep a backup if you reinstall.

### 4. Proxies
Proxies disguise your network location.
1. Click **Proxies**.
2. Type a proxy in the form `IP:PORT` or `USER:PASS@IP:PORT` and press **Add**.
3. The table shows each proxy's status and region. Use **Test Proxy** to ping it and update the status.
4. Use **Delete Selected** to remove entries. Proxy details are stored in the same `core/reviewbot.db` database.

### 5. Sites
This tab lists all site templates found in the `templates/` directory. Selecting a site shows the fields defined for that website. Use it as a quick reference to verify that your template contains the necessary mappings.

### 6. Schedule
The scheduler plans when each review will be posted.
1. Click **Schedule**.
2. Press **Add Scheduled Job** and choose the review, template/site, account, date, and time. You can also set repeat intervals for recurring posts.
3. Scheduled jobs appear in the table. Select one and choose **Remove Selected** to cancel it.
4. Press **Toggle Scheduler** to start or stop the background posting engine. The banner turns green when running.

### 7. Jobs
The Jobs tab shows every queued task.
1. Click **Jobs**.
2. Use the **Show only failed** checkbox to filter for errors.
3. Select a job and click **Retry Selected** to attempt posting again.
4. Click **Refresh** to reload the list at any time. Jobs update automatically every few seconds.

### 8. Logs
Use this tab to view the last 100 lines of activity.
1. Click **Logs**.
2. Press **Refresh** to reload the display.
3. By default it shows `logs/post_log.csv` if available; otherwise it falls back to `logs/app.log`.
4. Scroll through the text box to see success messages, errors, and timestamps.

### 9. Settings
1. Click **Settings**.
2. Enter your OpenAI API key and pick a model (for example `gpt-4`).
3. Click **Save**. Settings are written to `config/settings.local.json`. You can edit this file manually if the GUI is unavailable.

---

## Advanced Tools
These tools live under the `core/` folder and are run from the terminal. They provide power features beyond the GUI.

### SERP Scanner
Check if reviews are visible on Google.
```bash
python -c "from core.serp_scanner import check_review_visibility;print(check_review_visibility('your search terms'))"
```
It prints the top snippets it finds.
=======


### Report Generator
Summarize what has been posted.
```bash
python -c "from core.report_generator import generate_report;print(generate_report())"
```
Add `start` and `end` dates in ISO format to limit the range.

### Exporter
Create CSV, JSON, or PDF reports from the post log.
```bash
python -c "from core.exporter import export_reviews;from datetime import datetime;export_reviews(None,None,['csv','json','pdf'])"
```
Files are saved in the `reports/` folder.

### Geo Spoofer
Some sites show content based on location. The geo spoofer feeds Chrome fake coordinates.
```bash
python -c "from core.geospoofer import get_random_location,spoof_location;from selenium import webdriver;d=webdriver.Chrome();spoof_location(d,get_random_location())"
```
Run this before interacting with a site if you need a different region.

### CAPTCHA Solver
Sage Justice integrates with DeathByCaptcha to solve image challenges.
```bash
python -c "from core.captcha_solver import solve_captcha;print(solve_captcha(open('captcha.jpg','rb').read(),'USERNAME','PASSWORD'))"
```
Replace with your account details; the function returns the text solution.

### Test Mode
Preview postings without using real accounts.
```bash
python -c "from core.test_mode import dry_run_post;dry_run_post('templates/site.json','This is a test review')"
```
The browser opens, fills in fields, and stops before submission.

### Orchestrator
For high-volume work, the `orchestrator.py` script launches multiple agents to process the job queue simultaneously.
```bash
python orchestrator.py
```
Agents pull jobs from the database, post reviews, and retry on failure.

---

## How the Automation Works
1. **Review Creation:** You craft prompts; the AI generates multiple styled variations.
2. **Template Mapping:** Templates define where each piece of data goes on a website.
3. **Queueing:** Reviews assigned to projects are added to the job queue with chosen accounts, proxies, and times.
4. **Scheduling:** The scheduler or orchestrator wakes up when a job is due and spawns a browser.
5. **Posting:** Selenium opens the site, optionally spoofs location, logs in, solves CAPTCHAs, and submits the review.
6. **Rotation:** Each job can use different accounts, proxies, and tones to appear organic.
7. **Logging & Reports:** Every attempt is written to `logs/post_log.csv`, which powers the Logs tab, report generator, and expo

### 2. Templates
Templates tell the program where to click and what to fill out on each review website.
1. Click **Templates**.
2. Load an existing template or create a new one.
3. For new templates, follow the on-screen prompts to map fields (name, rating, review text, etc.).
4. Save templates as JSON files in the `templates/` folder.

## Troubleshooting & FAQ
### Nothing happens when I run `python dashboard/main_gui.py`
- Ensure Python is installed: `python --version`.
- On some systems the command is `python3` instead of `python`.
- If the command prints `No module named tkinter`, install Tkinter (`sudo apt install python3-tk` on Linux).

### `git` or `pip` is not recognized
- On Windows, close and reopen the terminal after installation so PATH updates.
- On macOS/Linux, ensure you typed the commands exactly (`git --version`, `pip --version`).

### The program cannot find my OpenAI key
- Confirm `config/settings.local.json` exists and contains your key.
- The file must be valid JSON. Use double quotes around the key.
- If you rotated your key, update the file and restart the program.

### Chrome does not open or automation fails
- Confirm Google Chrome is installed.
- Make sure `chromedriver` matches your Chrome version. Installing `webdriver-manager` often resolves this.
- Disable antivirus software temporarily if it blocks the browser from launching.

### Proxy or account keeps failing
- Use the **Proxies** and **Accounts** tabs to check status colors.
- Remove entries that show repeated failures and replace them with fresh ones.

### API calls return errors or time out
- Check your internet connection.
- Ensure your OpenAI account has quota remaining.
- Large prompts may take longer; try again with fewer simultaneous generations.

### How do I stop the scheduler?
- Close the scheduler window or press `Ctrl` + `C` in the terminal running the program.

### Where are my reviews stored?
- Generated text is saved in the `output/` folder under project names.
- Logs and post results are under `logs/`.

---

## Folder Structure
```
sage-justice/
├── accounts/   # (optional) legacy JSON credentials; new data stored in core/reviewbot.db
├── config/     # Settings, project lists, template registry
├── core/       # All automation engines and utility modules
├── dashboard/  # Tkinter GUI application (Guardian Deck)
├── gui/        # Reusable GUI components like the Template Manager
├── scheduler/  # Background scheduler and job queue logic
├── logs/       # `app.log` and `post_log.csv`
├── output/     # Generated reviews and queued project files
├── proxy/      # (optional) legacy proxy lists; new data stored in core/reviewbot.db
├── templates/  # Site templates created with the manager
├── tests/      # Automated test suite
└── README.md
```

---

## Roadmap
| Arc | Name | Status |
| --- | --- | --- |
| 1 | Initial Project Setup | ✅ Complete |
| 2 | Review Generator Core | ✅ Complete |
| 3 | GUI Builder | ✅ Complete |
| 4 | Dripfeed Scheduling | ✅ Complete |
| 5 | Proxy/Account Rotation | ✅ Complete |
| 6 | Template + Mapping Setup | ✅ Complete |
| 7+ | Cross-platform Testing | 🚧 Pending |
| 8+ | Plugin System & Export | 🔮 Planning |

---
## Legal & Contributions
- **Truthfulness:** This tool is meant for honest, factual reviews only.
- **Terms of Service:** Always respect the rules of each review platform.
- **License:** MIT – see `LICENSE` file.
- **Contributing:** Pull requests are welcome. Please open an issue to discuss major changes first.

---

Happy reviewing! If you get stuck, read the troubleshooting section again or ask a tech-savvy friend for help.
