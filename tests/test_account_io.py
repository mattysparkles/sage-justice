import logging
import os
from importlib import reload


def test_account_import_export(tmp_path, caplog):
    os.environ["REVIEWBOT_DB"] = str(tmp_path / "test.db")
    from core import database, account_manager

    # Reload modules so they pick up the new database path
    reload(database)
    reload(account_manager)

    text = "u1,p1,SiteA,https://a.com,recaptcha,123\n" "badline\n" "u2,p2,,,,\n"
    with caplog.at_level(logging.ERROR):
        accounts = account_manager.import_accounts_from_text(text)
    # One invalid line should be logged and skipped
    assert len(accounts) == 2
    assert "missing username or password" in caplog.text

    account_manager.save_accounts(accounts, category="test")

    all_accounts = database.get_all_accounts()
    exported = account_manager.export_accounts_to_text(all_accounts)
    assert "u1,p1,SiteA,https://a.com,recaptcha,123" in exported
    assert "u2,p2" in exported

