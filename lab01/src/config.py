from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    github_tokens_raw: str = Field(
        ..., 
        alias="GITHUB_TOKENS", 
        description="List of GitHub tokens separated by comma"
    )
    github_graphql_url: str = Field(default="https://api.github.com/graphql")
    sample_size: int = Field(default=10)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def github_tokens(self) -> List[str]:
        return [t.strip() for t in self.github_tokens_raw.split(",") if t.strip()]

settings = Settings()
