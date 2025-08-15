from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    database_url: str
    rabbitmq_url: str
    openai_api_key: str
    daily_budget_usd: float
    max_tokens_per_request: int
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
