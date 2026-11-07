import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from decimal import Decimal
from typing import Literal

import psycopg
from fastapi import FastAPI, HTTPException
from fastapi.openapi.docs import get_swagger_ui_html
from pydantic import BaseModel, Field, field_validator
from psycopg.rows import dict_row

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aegisshield.payment-api")


def database_connection():
    return psycopg.connect(
        host=os.getenv("DB_HOST", "postgres.aegis-data.svc.cluster.local"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "aegis"),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        connect_timeout=3,
        row_factory=dict_row,
    )


def initialize_database():
    with database_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    payment_id UUID PRIMARY KEY,
                    amount NUMERIC(12, 2) NOT NULL
                        CHECK (amount > 0),
                    currency VARCHAR(3) NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL
                        DEFAULT CURRENT_TIMESTAMP
                )
            """)
        conn.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AegisShield Payment API")

    # Database initialization is retried through the readiness
    # endpoint if PostgreSQL is initially unavailable.
    try:
        initialize_database()
    except Exception:
        logger.exception("Database initialization deferred")

    yield

    logger.info("Stopping AegisShield Payment API")


app = FastAPI(
    servers=[{"url": "/pay"}],
    title="AegisShield Payment API",
    version="1.0.0",
    description="Development-only simulated payment processing",
    lifespan=lifespan,
    docs_url=None,
)


@app.get("/docs", include_in_schema=False)
def custom_swagger_ui():
    return get_swagger_ui_html(
        openapi_url="/pay/openapi.json",
        title="AegisShield Payment API - Swagger UI",
    )


class PaymentRequest(BaseModel):
    amount: Decimal = Field(
        gt=Decimal("0"),
        le=Decimal("9999999999.99"),
        max_digits=12,
        decimal_places=2,
    )
    currency: Literal["EUR", "USD", "GBP"] = "EUR"

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value):
        if not value.is_finite():
            raise ValueError("Amount must be finite")
        return value


class PaymentResponse(BaseModel):
    payment_id: uuid.UUID
    amount: Decimal
    currency: str
    status: str
    created_at: datetime


@app.get("/")
def root():
    return {
        "application": "AegisShield Payment API",
        "version": "1.0.0",
        "environment": "development",
        "message": "Simulated payments only",
    }


@app.get("/health/live")
def liveness():
    return {"status": "alive"}


@app.get("/health/startup")
def startup():
    return {"status": "started"}


@app.get("/health/ready")
def readiness():
    try:
        initialize_database()
        return {"status": "ready", "database": "connected"}
    except Exception:
        logger.exception("Database readiness check failed")
        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
        )


@app.post(
    "/pay",
    response_model=PaymentResponse,
    status_code=201,
)
def create_payment(payment: PaymentRequest):
    payment_id = uuid.uuid4()

    try:
        with database_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO payments (
                        payment_id,
                        amount,
                        currency,
                        status
                    )
                    VALUES (%s, %s, %s, %s)
                    RETURNING
                        payment_id,
                        amount,
                        currency,
                        status,
                        created_at
                """, (
                    payment_id,
                    payment.amount,
                    payment.currency,
                    "simulated_success",
                ))

                result = cursor.fetchone()

            conn.commit()

        return result

    except psycopg.Error:
        logger.exception("Payment database operation failed")
        raise HTTPException(
            status_code=503,
            detail="Payment service temporarily unavailable",
        )


@app.get(
    "/payments/{payment_id}",
    response_model=PaymentResponse,
)
def get_payment(payment_id: uuid.UUID):
    try:
        with database_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        payment_id,
                        amount,
                        currency,
                        status,
                        created_at
                    FROM payments
                    WHERE payment_id = %s
                """, (payment_id,))

                result = cursor.fetchone()

        if result is None:
            raise HTTPException(
                status_code=404,
                detail="Payment not found",
            )

        return result

    except psycopg.Error:
        logger.exception("Payment lookup failed")
        raise HTTPException(
            status_code=503,
            detail="Database temporarily unavailable",
        )
