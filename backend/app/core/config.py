from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "SmartRoute"
    API_V1_STR: str = "/api/v1"

    # Amap
    AMAP_API_KEY: str = ""

    # DeepSeek LLM
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_MODEL: str = "deepseek-v4-flash"

    # MaxKB
    MAXKB_BASE_URL: str = "http://localhost:18090"
    MAXKB_API_KEY: str = ""
    MAXKB_CHAT_API_URL: str = ""
    MAXKB_DATASET_ID: str = ""

    # Cost Estimation
    FUEL_PRICE_PER_L: float = 7.5
    ESCORT_VEHICLE_COST_PER_DAY: float = 800.0
    POLICE_ESCORT_COST: float = 2000.0
    DEFAULT_INSURANCE_COST: float = 1500.0

    class Config:
        env_file = "../.env"  # Relative to backend/ working directory
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
