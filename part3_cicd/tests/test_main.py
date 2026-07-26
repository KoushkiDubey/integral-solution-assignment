import pytest

from app.main import app, calculate_refund_eta


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_refund_eta_card():
    assert calculate_refund_eta(2, "card") == 5


def test_refund_eta_store_credit():
    assert calculate_refund_eta(1, "store_credit") == 2


def test_refund_eta_never_negative():
    assert calculate_refund_eta(100, "card") == 0


def test_refund_eta_invalid_method():
    with pytest.raises(ValueError):
        calculate_refund_eta(1, "bitcoin")


def test_refund_eta_route(client):
    resp = client.get("/refund-eta/2/card")
    assert resp.status_code == 200
    assert resp.get_json() == {"days_remaining": 5}


def test_refund_eta_route_invalid_method(client):
    resp = client.get("/refund-eta/2/bitcoin")
    assert resp.status_code == 400
