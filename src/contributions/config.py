"""Application configuration via environment variables."""

import logging
import subprocess

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


def _gh_auth_token() -> str | None:
    """Try to get a token from the gh CLI."""
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    github_token: str | None = None
    gitea_url: str | None = None
    gitea_token: str | None = None
    anthropic_api_key: str | None = None

    @model_validator(mode="after")
    def _resolve_github_token(self):
        if not self.github_token:
            token = _gh_auth_token()
            if token:
                logger.debug("Using GitHub token from gh CLI")
                self.github_token = token
        return self
