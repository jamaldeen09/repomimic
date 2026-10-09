import typer

app = typer.Typer(
    name="repomimic",
    help="CLI tool that indexes source code from Git repos into a database so AI can mirror their implementation patterns.",
)

def main() -> None:
    app()

@app.command()
def hello(name: str):
    print(f"Hello {name}")

@app.command()
def goodbye(name: str, formal: bool = False):
    if formal:
        print(f"Goodbye Ms. {name}. Have a good day.")
    else:
        print(f"Bye {name}!")

if __name__ == "__main__":
    main()