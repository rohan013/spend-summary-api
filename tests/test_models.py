from models import InstitutionConfig


def test_all_fields():
    cfg = InstitutionConfig(access_token="tok", name="Chase", accounts={"id1": "Checking"})
    assert cfg.access_token == "tok"
    assert cfg.name == "Chase"
    assert cfg.accounts == {"id1": "Checking"}


def test_default_accounts_is_empty_dict():
    cfg = InstitutionConfig(access_token="tok", name="Chase")
    assert cfg.accounts == {}


def test_default_accounts_not_shared():
    a = InstitutionConfig(access_token="tok", name="A")
    b = InstitutionConfig(access_token="tok", name="B")
    a.accounts["x"] = "y"
    assert "x" not in b.accounts


def test_equality():
    a = InstitutionConfig(access_token="tok", name="Chase")
    b = InstitutionConfig(access_token="tok", name="Chase")
    assert a == b


def test_inequality():
    a = InstitutionConfig(access_token="tok1", name="Chase")
    b = InstitutionConfig(access_token="tok2", name="Chase")
    assert a != b
