# ArcPhase 21: Review Site Categories and Template Mapping

## Overview
This phase introduces structured categorization of review sites and outlines a templating approach for automated review submission using Selenium. The goal is to maximize automation, minimize user setup, and support as many high-impact platforms as possible out of the box.

---

## Categories of Review Sites

### 1. **Legal & Attorney Review Sites**
- Avvo (https://www.avvo.com)
- Lawyers.com (https://www.lawyers.com)
- Justia (https://www.justia.com/lawyers)
- Martindale-Hubbell (https://www.martindale.com)
- Super Lawyers (https://www.superlawyers.com)
- LegalMatch (https://www.legalmatch.com)

### 2. **General Business Review Sites**
- Google Business (https://business.google.com)
- Yelp (https://www.yelp.com)
- Better Business Bureau (https://www.bbb.org)
- Trustpilot (https://www.trustpilot.com)
- SiteJabber (https://www.sitejabber.com)
- YellowPages (https://www.yellowpages.com)

### 3. **Social Media Platforms**
- Facebook Pages (https://www.facebook.com)
- LinkedIn Business (https://www.linkedin.com)
- Reddit (subreddits like r/legaladvice, r/lawyers)

### 4. **Local / Niche / Regional Review Platforms**
- Angi (formerly Angie’s List) (https://www.angi.com)
- Nextdoor (https://nextdoor.com)
- Thumbtack (https://www.thumbtack.com)
- Alignable (https://www.alignable.com)

### 5. **Service & Consumer Complaint Boards**
- Ripoff Report (https://www.ripoffreport.com)
- ComplaintsBoard (https://www.complaintsboard.com)
- PissedConsumer (https://www.pissedconsumer.com)

---

## Template Format for Selenium Automation

Each review site will require the following configuration:

```json
{
  "site_name": "Avvo",
  "category": "Legal & Attorney Review Sites",
  "url": "https://www.avvo.com",
  "review_path": [
    {"type": "click", "selector": "button.write-review"},
    {"type": "input", "selector": "#title", "content": "{title}"},
    {"type": "input", "selector": "#review", "content": "{body}"},
    {"type": "select", "selector": "#rating", "value": "5"},
    {"type": "click", "selector": "button.submit"}
  ],
  "requires_account": true,
  "captcha_handling": "deathbycaptcha"
}
```

---

## Next Steps

- Prioritize legal and business platforms (high trust/SEO value).
- Auto-detect category and pull template config from local JSON.
- Build GUI interface for mapping new sites.
- Test each flow with proxy/VPN rotation enabled.