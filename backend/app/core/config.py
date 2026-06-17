from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "SmartRoute"
    API_V1_STR: str = "/api/v1"

    # Amap Web Service API (后端路线规划)
    AMAP_API_KEY: str = ""

    # DeepSeek LLM — AI 助手
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_MODEL: str = "deepseek-v4-flash"

    # MaxKB — 知识库法规查询
    # MAXKB_BASE_URL 自动从 MAXKB_PORT 推导: http://localhost:{MAXKB_PORT}
    # Docker 内部使用 cargo-maxkb:8080，由 docker-compose 注入 MAXKB_BASE_URL
    MAXKB_PORT: int = 18090
    MAXKB_BASE_URL: str = ""
    MAXKB_API_KEY: str = ""
    MAXKB_CHAT_API_URL: str = ""
    MAXKB_DATASET_ID: str = ""
    MAXKB_SESSION_TOKEN: str = ""

    # Cost Estimation (均有合理默认值)
    FUEL_PRICE_PER_L: float = 7.5
    ESCORT_VEHICLE_COST_PER_DAY: float = 800.0
    POLICE_ESCORT_COST: float = 2000.0
    DEFAULT_INSURANCE_COST: float = 1500.0

    def model_post_init(self, __context):
        """自动推导未显式设置的 URL"""
        if not self.MAXKB_BASE_URL:
            self.MAXKB_BASE_URL = f"http://localhost:{self.MAXKB_PORT}"

    class Config:
        env_file = "../.env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
