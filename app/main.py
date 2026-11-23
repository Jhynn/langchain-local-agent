import datetime

from decimal import Decimal
from app.agents.assistant_agent import AssistantAgent
from app.core.database import db
from app.core.logger import logger
from app.models.expense import Expense


def init_database() -> None:
    db.connect(reuse_if_open=True)
    db.create_tables([Expense], safe=True)

    if Expense.select().count() == 0:
        sample_expenses: list[dict[str, object]] = [
            {
                "employee_name": "Ana Souza",
                "department": "Engineering",
                "category": "Cloud Infrastructure",
                "amount": Decimal("1450.00"),
                "status": "approved",
                "expense_date": datetime.date(2026, 11, 10),
            },
            {
                "employee_name": "Carlos Lima",
                "department": "Sales",
                "category": "Flight Ticket",
                "amount": Decimal("2180.50"),
                "status": "pending",
                "expense_date": datetime.date(2026, 11, 15),
            },
            {
                "employee_name": "Beatriz Mendes",
                "department": "Engineering",
                "category": "Conference Pass",
                "amount": Decimal("950.00"),
                "status": "approved",
                "expense_date": datetime.date(2026, 11, 18),
            },
            {
                "employee_name": "Rafael Costa",
                "department": "Marketing",
                "category": "Client Dinner",
                "amount": Decimal("420.75"),
                "status": "rejected",
                "expense_date": datetime.date(2026, 11, 19),
            },
            {
                "employee_name": "Juliana Alves",
                "department": "Sales",
                "category": "Hotel Accommodation",
                "amount": Decimal("1120.00"),
                "status": "pending",
                "expense_date": datetime.date(2026, 11, 20),
            },
        ]
        Expense.insert_many(sample_expenses).execute()
        logger.info("Seeded initial sample records into 'expenses' table.")


def main() -> None:
    init_database()
    agent: AssistantAgent = AssistantAgent()
    print("\nLangGraph Local Agent ready. Type 'exit' or 'quit' to stop.\n")

    while True:
        try:
            user_input: str = input("You: ").strip()
            if not user_input:
                continue
            if user_input.lower() in {"exit", "quit"}:
                logger.info("Shutting down agent session.")
                break

            answer: str = agent.run(user_input)
            print(f"\nAgent: {answer}\n")

        except KeyboardInterrupt:
            logger.info("Session interrupted by user.")
            break
        except Exception as exc:
            logger.error(f"Unexpected error during execution: {exc}")
        finally:
            if not db.is_closed():
                db.close()


if __name__ == "__main__":
    main()
