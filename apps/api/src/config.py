from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="../../.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    skyfi_api_key: str = ""
    skyfi_api_base_url: str = "https://app.skyfi.com/platform-api"
    skyfi_webhook_secret: str = ""
    anthropic_api_key: str = ""
    database_url: str = "postgresql://sentinel:sentinel@localhost:5432/sentinel"
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    secret_key: str = "dev-secret-change-in-production"
    demo_key: str = "SKYFI_DEMO"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 720  # 30 days

    @property
    def use_mock_skyfi(self) -> bool:
        return not self.skyfi_api_key


settings = Settings()
