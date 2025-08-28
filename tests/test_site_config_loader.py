from core.site_config_loader import SiteConfigLoader

def test_loader_parses_review_site_templates():
    loader = SiteConfigLoader('templates')
    templates = loader.load_templates()
    assert 'google_reviews' in templates
    assert 'bbb_scam_tracker' in templates
    assert isinstance(templates['google_reviews'].get('review_fields'), list)

