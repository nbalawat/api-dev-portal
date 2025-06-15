"""
Configuration settings for the Developer Portal API.
"""
import os
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application settings
    app_name: str = Field(default="Developer Portal API", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    app_env: str = Field(default="development", env="APP_ENV")
    debug: bool = Field(default=True, env="DEBUG")
    
    # Security settings
    secret_key: str = Field(..., env="SECRET_KEY")
    jwt_secret_key: str = Field(..., env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=30, env="JWT_EXPIRE_MINUTES")
    jwt_refresh_expire_days: int = Field(default=7, env="JWT_REFRESH_EXPIRE_DAYS")
    
    # Password settings
    password_min_length: int = Field(default=8, env="PASSWORD_MIN_LENGTH")
    password_require_uppercase: bool = Field(default=True, env="PASSWORD_REQUIRE_UPPERCASE")
    password_require_lowercase: bool = Field(default=True, env="PASSWORD_REQUIRE_LOWERCASE")
    password_require_numbers: bool = Field(default=True, env="PASSWORD_REQUIRE_NUMBERS")
    password_require_special: bool = Field(default=False, env="PASSWORD_REQUIRE_SPECIAL")
    
    # Database settings
    database_url: str = Field(..., env="DATABASE_URL")
    database_echo: bool = Field(default=False, env="DATABASE_ECHO")
    
    # Redis settings
    redis_url: str = Field(..., env="REDIS_URL")
    
    # CORS settings
    allowed_origins: str = Field(default="", env="ALLOWED_ORIGINS")
    allowed_methods: str = Field(default="GET,POST,PUT,DELETE,OPTIONS,PATCH", env="ALLOWED_METHODS")
    allowed_headers: str = Field(default="*", env="ALLOWED_HEADERS")
    
    # Rate limiting settings
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_period: int = Field(default=60, env="RATE_LIMIT_PERIOD")
    
    # Admin settings
    admin_email: str = Field(default="admin@devportal.local", env="ADMIN_EMAIL")
    admin_username: str = Field(default="admin", env="ADMIN_USERNAME")
    admin_password: str = Field(default="admin123", env="ADMIN_PASSWORD")
    
    # Logging settings
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    
    # Email settings (optional)
    smtp_host: Optional[str] = Field(default=None, env="SMTP_HOST")
    smtp_port: int = Field(default=587, env="SMTP_PORT")
    smtp_user: Optional[str] = Field(default=None, env="SMTP_USER")
    smtp_password: Optional[str] = Field(default=None, env="SMTP_PASSWORD")
    smtp_tls: bool = Field(default=True, env="SMTP_TLS")
    from_email: str = Field(default="noreply@devportal.local", env="FROM_EMAIL")
    
    @property
    def cors_origins(self) -> List[str]:
        """Get CORS origins as a list."""
        if self.allowed_origins:
            return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]
        return []
    
    @property
    def cors_methods(self) -> List[str]:
        """Get CORS methods as a list."""
        if self.allowed_methods:
            return [method.strip() for method in self.allowed_methods.split(",") if method.strip()]
        return ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
    
    @property
    def cors_headers(self) -> List[str]:
        """Get CORS headers as a list."""
        if self.allowed_headers:
            return [header.strip() for header in self.allowed_headers.split(",") if header.strip()]
        return ["*"]
    
    @validator("debug", pre=True)
    def parse_debug(cls, v):
        """Parse debug flag from string."""
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "on")
        return v
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.app_env.lower() == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.app_env.lower() == "production"
    
    @property
    def docs_url(self) -> Optional[str]:
        """Get docs URL based on environment."""
        return "/docs" if self.debug else None
    
    @property
    def redoc_url(self) -> Optional[str]:
        """Get ReDoc URL based on environment."""
        return "/redoc" if self.debug else None
    
    @property
    def openapi_url(self) -> Optional[str]:
        """Get OpenAPI URL based on environment."""
        return "/openapi.json" if self.debug else None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()