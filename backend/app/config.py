from decimal import Decimal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://localhost:5432/firewall_db"
    TEST_DATABASE_URL: str = "postgresql://localhost:5432/firewall_test_db"
    TRANSACTION_EXPIRY_SECONDS: int = 300
    PRICE_MISMATCH_TOLERANCE: Decimal = Decimal("0.01")
    RAZORPAY_TEST_KEY_ID: str = ""
    RAZORPAY_TEST_KEY_SECRET: str = ""
    RAZORPAY_MOCK_FALLBACK: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
