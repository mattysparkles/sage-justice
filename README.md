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
8. [How the Automation Works](#how-the-automation-works)
9. [Troubleshooting & FAQ](#troubleshooting--faq)
10. [Folder Structure](#folder-structure)
11. [Roadmap](#roadmap)
12. [Legal & Contributions](#legal--contributions)

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
Still in the terminal, type:
```bash
pip install -r requirements.txt
```
This installs all libraries that Sage Justice needs.

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

---

## Running the Program
In the terminal, make sure you are inside the `sage-justice` folder. Then type:
```bash
python dashboard/main_gui.py
```
A window will appear. This is the main control panel.

**First-time tip:** If nothing happens or you see an error, read the troubleshooting section below.

---

## Understanding the Interface
The dashboard uses tabs along the top to organize features. You can click a tab to switch sections.

| Tab | What It Does |
| --- | --- |
| **Review Generator** | Write or rewrite reviews with AI. |
| **Templates** | Configure how different websites accept reviews. |
| **Accounts** | Store usernames and passwords for each site. |
| **Proxies** | List IP addresses to hide your location. |
| **Sites** | View all supported review platforms. |
| **Schedule** | Plan when reviews should be posted. |
| **Logs** | Read records of what has been posted. |
| **Settings** | Save your OpenAI key and choose the AI model. |

Each tab has buttons and text fields. Move your mouse over a field, click it, and type.

---

## Feature Walkthrough
### 1. Review Generator
1. Click the **Review Generator** tab.
2. In the **Prompt** box, type the situation or message you want to express.
3. Click **Generate**. The AI creates one or more reviews.
4. To rewrite a review, select it and click **Rewrite**.
5. Click **Save** to keep the reviews on your computer.

### 2. Templates
Templates tell the program where to click and what to fill out on each review website.
1. Click **Templates**.
2. Load an existing template or create a new one.
3. For new templates, follow the on-screen prompts to map fields (name, rating, review text, etc.).
4. Save templates as JSON files in the `templates/` folder.

### 3. Accounts
1. Click **Accounts**.
2. Add a new entry with the website name, username, and password.
3. The data is saved in `accounts/accounts.json`. Keep this file private.

### 4. Proxies
1. Click **Proxies**.
2. Enter one proxy per line in the format `http://USER:PASS@HOST:PORT`.
3. The list is saved to `proxy/proxy_list.txt`.

### 5. Sites
This tab shows which sites are available based on your templates. Select a site to view details.

### 6. Schedule
1. Click **Schedule**.
2. Choose a review, site, account, and date.
3. Click **Add Job** to queue it.
4. Press **Start Scheduler** to begin automated posting.

### 7. Logs
Use this tab to view the last 100 lines of:
- `logs/post_log.csv` – record of postings.
- `logs/app.log` – general application logs.

### 8. Settings
1. Enter your OpenAI API key (again) and choose the model (e.g., `gpt-4`).
2. Click **Save Settings**.

---

## How the Automation Works
1. **Review Creation:** You supply a prompt; the AI produces variations.
2. **Queueing:** Reviews are scheduled with dates and times.
3. **Posting:** The scheduler opens Chrome using Selenium, logs into accounts, and submits reviews.
4. **Rotation:** Each post can use a different account and proxy to avoid detection.
5. **Logging:** Results are stored in log files for later review.

---

## Troubleshooting & FAQ
### Nothing happens when I run `python dashboard/main_gui.py`
- Ensure Python is installed: `python --version`.
- On some systems the command is `python3` instead of `python`.

### The program cannot find my OpenAI key
- Confirm `config/settings.local.json` exists and contains your key.
- The file must be valid JSON. Use double quotes around the key.

### Chrome does not open or automation fails
- Confirm Google Chrome is installed.
- Make sure `chromedriver` is compatible with your Chrome version. Some Selenium setups handle this automatically; otherwise, install `webdriver-manager`.

### How do I stop the scheduler?
- Close the scheduler window or press `Ctrl` + `C` in the terminal running the program.

### Where are my reviews stored?
- Generated text is stored in the `output/` folder.
- Logs are under `logs/`.

---

## Folder Structure
```
sage-justice/
├── accounts/
├── config/
├── core/
├── dashboard/
├── logs/
├── output/
├── proxy/
├── templates/
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
