import importlib
import sys
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

import psycopg
import pytest
from fastapi.testclient import TestClient


# The application directory is named payment-api, so it cannot
# be imported as a conventional Python package.
API_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_DIR))

payment_api = importlib.import_module("main")

PAYMENT_ID = uuid.UUID("30f027a1-df95-4b12-a0aa-21ff7ac07d8d")
CREATED_AT = datetime(2026, 11, 7, 12, 44, 47, tzinfo=timezone.utc)


def payment_record(amount="10.00", currency="EUR"):
    return {
        "payment_id": PAYMENT_ID,
        "amount": Decimal(amount),
        "currency": currency,
        "status": "simulated_success",
        "created_at": CREATED_AT,
    }


@pytest.fixture
def db_mock(monkeypatch):
    """Mock the database connection and cursor context managers."""
    connection = MagicMock()
    cursor = MagicMock()

    connection.__enter__.return_value = connection
    connection.cursor.return_value = cursor
    cursor.__enter__.return_value = cursor

    monkeypatch.setattr(
        payment_api,
        "database_connection",
        lambda: connection,
    )

    return connection, cursor


@pytest.fixture
def client(monkeypatch):
    """Disable real database initialization during application startup."""
    monkeypatch.setattr(
        payment_api,
        "initialize_database",
        lambda: None,
    )

    with TestClient(payment_api.app) as test_client:
        yield test_client


# ----------------------------------------------------------
# Application and health checks
# ----------------------------------------------------------

def test_root_returns_application_information(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["application"] == "AegisShield Payment API"
    assert response.json()["environment"] == "development"


def test_liveness(client):
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_startup_health(client):
    response = client.get("/health/startup")

    assert response.status_code == 200
    assert response.json() == {"status": "started"}


def test_readiness_when_database_connected(client):
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "database": "connected",
    }


def test_readiness_when_database_unavailable(client, monkeypatch):
    def unavailable():
        raise psycopg.OperationalError("Database unavailable")

    monkeypatch.setattr(payment_api, "initialize_database", unavailable)

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["detail"] == "Database unavailable"


# ----------------------------------------------------------
# Payment creation
# ----------------------------------------------------------

def test_create_payment_success(client, db_mock):
    connection, cursor = db_mock
    cursor.fetchone.return_value = payment_record()

    response = client.post(
        "/pay",
        json={"amount": "10.00", "currency": "EUR"},
    )

    assert response.status_code == 201

    data = response.json()

    assert data["payment_id"] == str(PAYMENT_ID)
    assert Decimal(data["amount"]) == Decimal("10.00")
    assert data["currency"] == "EUR"
    assert data["status"] == "simulated_success"

    cursor.execute.assert_called_once()
    connection.commit.assert_called_once()


@pytest.mark.parametrize(
    "amount",
    ["0", "-1", "-10.50", "10000000000.00", "1.234", "NaN", "Infinity"],
)
def test_reject_invalid_amounts(client, db_mock, amount):
    connection, cursor = db_mock

    response = client.post(
        "/pay",
        json={"amount": amount, "currency": "EUR"},
    )

    assert response.status_code == 422
    cursor.execute.assert_not_called()
    connection.commit.assert_not_called()


@pytest.mark.parametrize(
    "currency",
    ["PKR", "JPY", "eur", "", "EURO"],
)
def test_reject_unsupported_currency(client, db_mock, currency):
    _, cursor = db_mock

    response = client.post(
        "/pay",
        json={"amount": "10.00", "currency": currency},
    )

    assert response.status_code == 422
    cursor.execute.assert_not_called()


def test_reject_missing_amount(client, db_mock):
    _, cursor = db_mock

    response = client.post("/pay", json={"currency": "EUR"})

    assert response.status_code == 422
    cursor.execute.assert_not_called()


def test_default_currency_is_eur(client, db_mock):
    _, cursor = db_mock
    cursor.fetchone.return_value = payment_record()

    response = client.post("/pay", json={"amount": "10.00"})

    assert response.status_code == 201
    assert response.json()["currency"] == "EUR"

    parameters = cursor.execute.call_args.args[1]
    assert parameters[2] == "EUR"


def test_payment_database_failure(client, monkeypatch):
    def failing_connection():
        raise psycopg.OperationalError("Connection refused")

    monkeypatch.setattr(
        payment_api,
        "database_connection",
        failing_connection,
    )

    response = client.post(
        "/pay",
        json={"amount": "10.00", "currency": "EUR"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Payment service temporarily unavailable"
    )

    # Internal database details must not leak to clients.
    assert "Connection refused" not in response.text


# ----------------------------------------------------------
# Payment retrieval
# ----------------------------------------------------------

def test_get_existing_payment(client, db_mock):
    _, cursor = db_mock
    cursor.fetchone.return_value = payment_record()

    response = client.get(f"/payments/{PAYMENT_ID}")

    assert response.status_code == 200
    assert response.json()["payment_id"] == str(PAYMENT_ID)
    assert response.json()["status"] == "simulated_success"

    cursor.execute.assert_called_once()
    assert cursor.execute.call_args.args[1] == (PAYMENT_ID,)


def test_get_missing_payment(client, db_mock):
    _, cursor = db_mock
    cursor.fetchone.return_value = None

    response = client.get(f"/payments/{PAYMENT_ID}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Payment not found"


@pytest.mark.parametrize(
    "invalid_id",
    ["invalid-uuid", "12345", "not-a-payment"],
)
def test_reject_invalid_payment_id(client, db_mock, invalid_id):
    _, cursor = db_mock

    response = client.get(f"/payments/{invalid_id}")

    assert response.status_code == 422
    cursor.execute.assert_not_called()


def test_get_payment_database_failure(client, monkeypatch):
    def failing_connection():
        raise psycopg.OperationalError("Connection refused")

    monkeypatch.setattr(
        payment_api,
        "database_connection",
        failing_connection,
    )

    response = client.get(f"/payments/{PAYMENT_ID}")

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Database temporarily unavailable"
    )
    assert "Connection refused" not in response.text


# ----------------------------------------------------------
# API schema
# ----------------------------------------------------------

def test_openapi_schema_available(client):
    response = client.get("/openapi.json")

    assert response.status_code == 200

    paths = response.json()["paths"]

    assert "/pay" in paths
    assert "/payments/{payment_id}" in paths
    assert "/health/ready" in paths
