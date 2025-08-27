# Sage Justice

**AI-Powered Review Automation for Truthful, Drip-Fed Accountability**  
_Built by Sparkles & Sage — Justice is a dish best served... continuously._

---

## 🧠 Overview

**Sage Justice** is a powerful review automation suite designed to help users publish **factual**, **unique**, and **well-distributed** reviews across multiple platforms. Originally built to bring attention to unethical professional conduct, Sage Justice makes sure every voice is heard — one post at a time.

Inspired by the need for ongoing, rotating accountability, the app uses AI to vary the phrasing of reviews without compromising the truth. You get SERP-safe content, automated posting (via Selenium), proxy rotation, and a clean GUI to manage everything.

---

## ✨ Features

- ✅ **AI-powered Review Spinner** (OpenAI GPT API)
- 🧾 **Multi-platform field-mapping system** for unique review site layouts
- 🧠 **Intelligent content variation** to bypass duplicate detection
- ⏳ **Dripfeed Scheduler** — publish reviews gradually over 30/60/90 days
- 🌐 **IP / Proxy / VPN Rotation Support**
- 👥 **Account Rotation** — swap between accounts per platform
- 🖥️ **Custom GUI built with PyQt5**
- 🔒 **Secure API key storage (external)**

---

## 🛠 Installation

1. **Clone the repo**:
   ```bash
   git clone https://github.com/mattysparkles/sage-justice.git
   cd sage-justice
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Add your OpenAI API key**:
   - Create a file called `settings.local.json` inside the `/config` folder (⚠️ Do not commit this).
   - Example:
     ```json
     {
       "openai_api_key": "sk-...YOURKEY..."
     }
     ```

4. **Run the app**:
   ```bash
   python gui/main_gui.py
   ```

---

## 🧪 How It Works

1. **Enter a review context** (what happened, what you want to say).
2. The AI engine spins **multiple unique but factually accurate reviews**.
3. Reviews are added to your drip queue and optionally saved locally.
4. A scheduling engine posts them slowly over time using Selenium.
5. Each post can:
   - Rotate accounts
   - Switch IPs via proxies
   - Post to different platforms
   - Mimic human input timing

---

## 🧩 Folder Structure

```
sage-justice/
├── config/
│   └── settings.json (default)
├── core/
│   └── review_generator.py
├── gui/
│   └── main_gui.py
├── templates/
│   └── google_review.json
├── style/
│   └── style.css
└── README.md
```

---

## 🔮 Roadmap

| Arc | Name                     | Status      |
|-----|--------------------------|-------------|
| 1   | Initial Project Setup    | ✅ Complete |
| 2   | Review Generator Core    | ✅ Complete |
| 3   | GUI Builder              | ✅ Complete |
| 4   | Dripfeed Scheduling      | ✅ Complete |
| 5   | Proxy/Account Rotation   | ✅ Complete |
| 6   | Template + Mapping Setup | ✅ Complete |
| 7+  | Cross-platform Testing   | 🚧 Pending  |
| 8+  | Plugin System & Export   | 🔮 Planning |

---

## 💡 Usage Ideas

- Publish true stories about bad services or unethical behavior without being silenced by filters.
- Hold companies, agencies, or individuals publicly accountable over time.
- Automate reputation management in a way that’s **ethical** and **honest**.
- Create a consistent digital trail without risking content bans.

---

# ArcPhase 21 – Review Site Categorization & Template Mapping

## 🎯 Objective
Establish foundational review site categories, build a curated database of target platforms, and begin Selenium automation templates for each.

---

## 🧩 Site Categories

| Category         | Description                                      |
|------------------|--------------------------------------------------|
| Legal            | Lawyers, firms, legal aid, etc.                  |
| General Business | Any commercial business or professional service  |
| Food & Beverage  | Restaurants, cafes, bars                         |
| Consumer Goods   | Electronics, appliances, gadgets                 |
| Home Services    | Plumbing, HVAC, landscaping, repairs             |
| Auto Services    | Dealerships, mechanics, rentals                  |
| Healthcare       | Doctors, dentists, hospitals                     |
| Real Estate      | Agents, brokers, listings                        |
| Education        | Schools, tutors, online classes                  |
| Miscellaneous    | Any uncategorized or niche review platforms      |

---

## 🌐 Predefined Review Sites by Category

### 🔍 Legal
- [Avvo](https://www.avvo.com)
- [Lawyers.com](https://www.lawyers.com)
- [Justia](https://www.justia.com)
- [Martindale](https://www.martindale.com)

### 🏢 General Business
- [Google Reviews](https://google.com/maps)
- [Trustpilot](https://www.trustpilot.com)
- [Better Business Bureau (BBB)](https://www.bbb.org)
- [Yellow Pages](https://www.yellowpages.com)
- [Glassdoor](https://www.glassdoor.com)

### 🍽️ Food & Beverage
- [Yelp](https://www.yelp.com)
- [Zomato](https://www.zomato.com)
- [TripAdvisor](https://www.tripadvisor.com)
- [OpenTable](https://www.opentable.com)

### 🛠️ Services (Home, Auto, etc.)
- [Angi (formerly Angie’s List)](https://www.angi.com)
- [HomeAdvisor](https://www.homeadvisor.com)
- [RepairPal](https://www.repairpal.com)
- [DealerRater](https://www.dealerrater.com)

### 🩺 Healthcare
- [Healthgrades](https://www.healthgrades.com)
- [Vitals](https://www.vitals.com)
- [Zocdoc](https://www.zocdoc.com)

---

## 🤖 Selenium Template Strategy

Each site will receive a JSON or Python template stored in `/templates/sites/{site_name}.json` that includes:

- Input field selectors (Name, Review, Rating, etc.)
- Login flow (if required)
- Navigation mapping (URL path, click order)
- CAPTCHA workaround requirements

Templates are recorded via:
1. Manual path recording via GUI step-through (already in Phase 2)
2. Saving detected input paths and success conditions per site

---

## ✅ Phase Deliverables

- Categorized site registry
- `site_registry.json` config file
- At least 10 Selenium-ready template JSONs under `/templates/sites/`
- A toggle in GUI to switch categories and see matched sites
- Auto-template-injection to ReviewBot for 1-click posting

---

This phase unlocks powerful commercial potential by reducing friction for everyday users. It's a massive UX win.


## 🧠 About

**Sage Justice** is a collaboration between [@mattysparkles](https://github.com/mattysparkles) and Sage, designed to empower individuals with AI tools that tell the truth and do it with style
---

## ⚠️ Legal Note

This tool is designed **only for factual, truthful reviews**. False or defamatory content is not supported or condoned. Always check terms of service of each review platform before posting.

---

## 📬 License & Contributions

License: `MIT`

PRs are welcome. If you'd like to contribute modules, templates, or review site mappings, open an issue or submit a pull request.

---
