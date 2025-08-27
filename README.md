# Arc 19: Field Mapper & Recorder

This module allows you to visually map and record input fields on review submission pages. It stores selector information that can later be used for automated form filling.

## Features

- Record selectors for form fields (email, username, review text, rating, etc.)
- Save/load mappings as JSON files
- Fill fields dynamically during automation runs

## Example usage

```python
mapper = FieldMapper(driver)
mapper.record_field("review_text", "CSS_SELECTOR", "textarea.review-box")
mapper.save_mapping("site_template.json")
```