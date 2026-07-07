import os
from dataclasses import dataclass

@dataclass
class Settings:
    """Application settings from environment."""
    api_key: str = ""
    anthropic_api_key: str = ""
    claude_proxy_base_url: str = ""
    redis_url: str = ""
    cors_origins: str = ""
    debug: bool = False
    
    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            api_key=os.getenv("API_KEY", ""),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            claude_proxy_base_url=os.getenv("CLAUDE_PROXY_BASE_URL", ""),
            redis_url=os.getenv("REDIS_URL", ""),
            cors_origins=os.getenv("CORS_ORIGINS", ""),
            debug=os.getenv("DEBUG", "").lower() == "true",
        )
