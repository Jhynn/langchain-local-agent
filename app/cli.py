import typer
import asyncio

from typing import Annotated
from app.core.database import db, init_database
from app.agents.adk_agent import adk_assistant_agent
from app.agents.assistant_agent import assistant_agent


cli_app: typer.Typer = typer.Typer(
    name="agent-cli",
    help="CLI interface for the local LangGraph Corporate Agent with persistent SQLite memory.",
    add_completion=False,
)


def _cleanup_resources() -> None:
    if not db.is_closed():
        db.close()
    assistant_agent.close()


@cli_app.command("chat")
def interactive_chat(
    session_id: Annotated[
        str,
        typer.Option(
            "--session-id",
            "-s",
            help="Conversation thread ID persisted in SQLite.",
        ),
    ] = "cli-default-session",
    show_tools: Annotated[
        bool,
        typer.Option(
            "--show-tools/--no-show-tools",
            help="Display which tools the agent invoked on each turn.",
        ),
    ] = True,
) -> None:
    """Starts an interactive multi-turn chat session with persistent memory."""
    init_database()
    typer.secho(
        f"\nLangGraph Agent CLI ready | Session: '{session_id}' | Type 'exit' or 'quit' to stop.\n",
        fg=typer.colors.CYAN,
        bold=True,
    )

    try:
        while True:
            user_input: str = typer.prompt("You").strip()
            if not user_input:
                continue
            if user_input.lower() in {"exit", "quit"}:
                typer.secho("Session saved to SQLite. Goodbye!", fg=typer.colors.YELLOW)
                break

            answer, tools_used = assistant_agent.run(user_input, session_id=session_id)
            if show_tools and tools_used:
                typer.secho(f"[Tools used: {', '.join(tools_used)}]", fg=typer.colors.MAGENTA)

            typer.secho("\nAgent: ", fg=typer.colors.GREEN, bold=True, nl=False)
            typer.echo(f"{answer}\n")
    except (KeyboardInterrupt, typer.Abort):
        typer.secho("\nSession interrupted and saved.", fg=typer.colors.YELLOW)
    finally:
        _cleanup_resources()


@cli_app.command("ask")
def single_question(
    question: Annotated[
        str,
        typer.Argument(help="The question or instruction to send to the agent."),
    ],
    session_id: Annotated[
        str,
        typer.Option(
            "--session-id",
            "-s",
            help="Conversation thread ID persisted in SQLite.",
        ),
    ] = "cli-default-session",
) -> None:
    """Sends a single prompt to the agent and prints the response."""
    init_database()
    try:
        answer, tools_used = assistant_agent.run(question, session_id=session_id)
        if tools_used:
            typer.secho(f"[Tools used: {', '.join(tools_used)}]", fg=typer.colors.MAGENTA)
        typer.echo(answer)
    finally:
        _cleanup_resources()


@cli_app.command("history")
def show_history(
    session_id: Annotated[
        str,
        typer.Option(
            "--session-id",
            "-s",
            help="Conversation thread ID to inspect.",
        ),
    ] = "cli-default-session",
) -> None:
    """Displays persisted conversation messages for a given session ID."""
    try:
        messages: list[dict[str, str]] = assistant_agent.get_history(session_id)
        if not messages:
            typer.secho(f"No persisted history found for session '{session_id}'.", fg=typer.colors.YELLOW)
            raise typer.Exit(code=0)

        typer.secho(f"\n--- Persisted History ({session_id}) ---\n", fg=typer.colors.CYAN, bold=True)
        for msg in messages:
            role_label: str = "You" if msg["role"] == "user" else "Agent"
            color: str = typer.colors.WHITE if msg["role"] == "user" else typer.colors.GREEN
            typer.secho(f"{role_label}: ", fg=color, bold=True, nl=False)
            typer.echo(f"{msg['content']}\n")
    finally:
        _cleanup_resources()


@cli_app.command("adk-chat")
def interactive_adk_chat(
    session_id: Annotated[
        str,
        typer.Option(
            "--session-id",
            "-s",
            help="ADK session identifier.",
        ),
    ] = "adk-default-session",
) -> None:
    """Starts an interactive multi-turn chat session using Google ADK."""
    init_database()
    typer.secho(
        f"\nGoogle ADK Agent CLI ready | Session: '{session_id}' | Type 'exit' or 'quit' to stop.\n",
        fg=typer.colors.CYAN,
        bold=True,
    )

    try:
        while True:
            user_input: str = typer.prompt("You").strip()

            if not user_input:
                continue

            if user_input.lower() in {"exit", "quit"}:
                typer.secho("ADK session ended. Goodbye!", fg=typer.colors.YELLOW)
                break

            answer, tools_used = asyncio.run(
                adk_assistant_agent.run(user_input, session_id=session_id)
            )

            if tools_used:
                typer.secho(f"[ADK Tools used: {', '.join(tools_used)}]", fg=typer.colors.MAGENTA)

            typer.secho("\nADK Agent: ", fg=typer.colors.GREEN, bold=True, nl=False)
            typer.echo(f"{answer}\n")

    except (KeyboardInterrupt, typer.Abort):
        typer.secho("\nSession interrupted.", fg=typer.colors.YELLOW)

    finally:
        _cleanup_resources()


if __name__ == "__main__":
    cli_app()
