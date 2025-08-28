import importlib
import os
import sys

sys.path.append(os.path.abspath('.'))


def setup_db(tmp_path):
    os.environ['REVIEWBOT_DB'] = str(tmp_path / 'test.db')
    import core.database as database
    importlib.reload(database)
    return database


def test_proxy_assignment_scopes(tmp_path):
    database = setup_db(tmp_path)
    # add proxy
    database.add_proxy('1.2.3.4', '8080')
    # add account
    database.add_account('user', 'pass', 'cat')
    acc = database.get_all_accounts()[0]
    acc_id = acc['id']
    # add site
    with database.get_connection() as conn:
        conn.execute("INSERT INTO sites (name) VALUES ('example')")
        conn.commit()
    # assign to account
    database.assign_proxy_to_account(1, acc_id)
    assert any(a['id'] == acc_id for a in database.get_proxy_accounts(1))
    # assign to site
    database.assign_proxy_to_site(1, 'example')
    assert 'example' in database.get_proxy_sites(1)
    # assign to project
    database.assign_proxy_to_project(1, 'proj')
    assert 'proj' in database.get_proxy_projects(1)
