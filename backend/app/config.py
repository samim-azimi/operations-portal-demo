from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Mission Operations Portal API"
    environment: str = "development"
    database_url: str = "sqlite:///./helpdesk.db"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    jwt_secret_key: str = "development-only-secret"
    jwt_issuer: str = "helixdesk-api"
    jwt_audience: str = "helixdesk-web"
    access_token_expire_minutes: int = 60
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    trusted_hosts: str = "localhost,127.0.0.1,testserver"
    chroma_path: str = "./chroma_data"
    upload_path: str = "./uploads"
    max_upload_bytes: int = 5_242_880
    max_files_per_ticket: int = 5
    rate_limit_per_minute: int = 120
    login_attempts_per_minute: int = 8
    public_app_url: str = "http://localhost:5173"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "helpdesk@example.com"
    smtp_from_name: str = "Operations Portal"
    smtp_use_tls: bool = True
    notification_admin_emails: str = ""
    signing_link_base_url: str = "http://localhost:5173/sign/review"
    lan_messenger_internal_base_url: str = ""
    lan_messenger_public_base_url: str = ""
    lan_messenger_lan_cidrs: str = "192.168.0.0/16,10.0.0.0/8,172.16.0.0/12"
    webrtc_stun_urls: str = ""
    webrtc_turn_urls: str = ""
    webrtc_turn_username: str = ""
    webrtc_turn_password: str = ""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self):
        if self.environment.lower() == "development":
            return ["*"]
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

    @property
    def trusted_host_list(self):
        if self.environment.lower() == "development":
            return ["*"]
        return [x.strip() for x in self.trusted_hosts.split(",") if x.strip()]

    @property
    def upload_directory(self) -> Path:
        return Path(self.upload_path).resolve()

    @property
    def notification_admin_email_list(self) -> list[str]:
        return [
            email.strip().lower()
            for email in self.notification_admin_emails.split(",")
            if email.strip()
        ]

    @property
    def lan_messenger_lan_cidr_list(self) -> list[str]:
        return [value.strip() for value in self.lan_messenger_lan_cidrs.split(",") if value.strip()]

    @model_validator(mode="after")
    def validate_production_secrets(self):
        weak = {"", "development-only-secret", "change-me-in-production"}
        if self.environment.lower() == "production" and self.jwt_secret_key in weak:
            raise ValueError("JWT_SECRET_KEY must be a strong secret in production")
        if self.environment.lower() == "production" and len(self.jwt_secret_key) < 32:
            raise ValueError("JWT_SECRET_KEY must contain at least 32 characters")
        return self

@lru_cache
def get_settings():
    return Settings()
settings = get_settings()
