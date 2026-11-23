from app.agents.assistant_agent import assistant_agent
from app.core.database import db, init_database
from app.core.logger import logger


def main() -> None:
    init_database()
    session_id: str = "cli-default-session"
    print(f"\nLangGraph Local Agent ready (session='{session_id}'). Type 'exit' or 'quit' to stop.\n")

    while True:
        try:
            user_input: str = input("You: ").strip()
            if not user_input:
                continue
            if user_input.lower() in {"exit", "quit"}:
                break

            answer, tools_used = assistant_agent.run(user_input, session_id=session_id)
            if tools_used:
                print(f"[Tools used: {', '.join(tools_used)}]")
            print(f"\nAgent: {answer}\n")
        except KeyboardInterrupt:
            break
        finally:
            if not db.is_closed():
                db.close()


if __name__ == "__main__":
    main()
