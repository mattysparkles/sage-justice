
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
