import typer

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import ValidationError

class Settings(BaseSettings):
    DATABASE_URL: str
    GITHUB_TOKEN: str
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

SETTING_DESCRIPTIONS = {
    "DATABASE_URL": "Database connection string (e.g., postgresql+asyncpg://user:pass@localhost/db)",
    "GITHUB_TOKEN": "GitHub Personal Access Token for querying the GitHub API on your behalf"
}

def get_settings() -> Settings:
    """Loads and validates environment variables with a polished, context-aware CLI error report."""
    try:
        return Settings()
    except ValidationError as e:
        typer.secho("\nConfiguration Error: Missing required environment variables.", fg=typer.colors.RED, bold=True)
        typer.echo("\nRepomimic needs the following configuration to run properly:\n")
        
        for error in e.errors():
            field = str(error["loc"][0]) if error["loc"] else "unknown"
            desc = SETTING_DESCRIPTIONS.get(field, "Required configuration setting")
            
            typer.secho(f"  • {field}", fg=typer.colors.YELLOW, bold=True, nl=False)
            typer.echo(f": {desc}")
            
        typer.echo("\nTip: Make sure your .env file is present in the project root and includes these keys.")
        raise typer.Exit(code=1)