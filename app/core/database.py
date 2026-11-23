import datetime

from decimal import Decimal
from peewee import MySQLDatabase
from app.core.config import settings
from app.core.logger import logger


db: MySQLDatabase = MySQLDatabase(
    settings.DB_NAME,
    user=settings.DB_USER,
    password=settings.DB_PASSWORD,
    host=settings.DB_HOST,
    port=settings.DB_PORT,
)


def init_database() -> None:
    from app.models.expense import Expense

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
