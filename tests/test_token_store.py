import json
import pytest
from token_store import JSONTokenStore


def _write(tmp_path, data):
    p = tmp_path / "tokens.json"
    p.write_text(json.dumps(data))
    return p


def test_load_file_not_found(tmp_path):
    store = JSONTokenStore(tmp_path / "missing.json")
    with pytest.raises(FileNotFoundError, match="missing.json"):
        store._load()


def test_load_file_exists(tmp_path):
    data = {"chase": {"access_token": "tok", "name": "Chase", "accounts": {}}}
    p = _write(tmp_path, data)
    assert JSONTokenStore(p)._load() == data


def test_list_institutions_with_accounts(tmp_path):
    data = {"chase": {"access_token": "tok", "name": "Chase", "accounts": {"id1": "My Checking"}}}
    store = JSONTokenStore(_write(tmp_path, data))
    result = store.list_institutions()
    assert len(result) == 1
    assert result[0].access_token == "tok"
    assert result[0].name == "Chase"
    assert result[0].accounts == {"id1": "My Checking"}


def test_list_institutions_without_accounts_key(tmp_path):
    data = {"chase": {"access_token": "tok", "name": "Chase"}}
    store = JSONTokenStore(_write(tmp_path, data))
    assert store.list_institutions()[0].accounts == {}


def test_list_institutions_multiple(tmp_path):
    data = {
        "chase": {"access_token": "tok1", "name": "Chase"},
        "bofa": {"access_token": "tok2", "name": "Bank of America"},
    }
    store = JSONTokenStore(_write(tmp_path, data))
    result = store.list_institutions()
    assert len(result) == 2
    assert {r.name for r in result} == {"Chase", "Bank of America"}


def test_list_institutions_empty_file(tmp_path):
    assert JSONTokenStore(_write(tmp_path, {})).list_institutions() == []


def test_load_raw(tmp_path):
    data = {"chase": {"access_token": "tok", "name": "Chase"}}
    assert JSONTokenStore(_write(tmp_path, data)).load_raw() == data


def test_save_raw_roundtrip(tmp_path):
    p = tmp_path / "tokens.json"
    data = {"chase": {"access_token": "tok", "name": "Chase", "accounts": {}}}
    JSONTokenStore(p).save_raw(data)
    assert json.loads(p.read_text()) == data


def test_save_raw_trailing_newline(tmp_path):
    p = tmp_path / "tokens.json"
    JSONTokenStore(p).save_raw({})
    assert p.read_text().endswith("\n")
