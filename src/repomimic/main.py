import typer

from src.repomimic.cli.commands.repositories import repository_app

app = typer.Typer(
    name="repomimic",
    help="CLI tool that indexes source code from Git repos into a database so AI can mirror their implementation patterns.",
)


app.add_typer(repository_app, name="repo")


def main():
    app()

if __name__ == "__main__":
    main()