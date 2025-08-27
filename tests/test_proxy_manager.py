import importlib
import os
import sys

sys.path.append(os.path.abspath("."))


def setup_db(tmp_path):
    os.environ["REVIEWBOT_DB"] = str(tmp_path / "test.db")
    import core.database as database
    importlib.reload(database)
    import proxy.manager as pm
    importlib.reload(pm)
    return database, pm.ProxyManager


def test_fetch_proxy(tmp_path):
    database, ProxyManager = setup_db(tmp_path)
    with database.get_connection() as conn:
        conn.execute(
            "INSERT INTO proxies (ip_address, port, region, status) VALUES ('1.2.3.4', '8080', 'us', 'alive')"
        )
        conn.commit()
    manager = ProxyManager()
    proxy = manager.get_proxy()
    assert proxy == "1.2.3.4:8080"
