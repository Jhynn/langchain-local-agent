from typing import Any
from langchain_core.tools import tool
from peewee import fn

from app.core.database import db
from app.core.logger import logger
from app.models.expense import Expense

FORBIDDEN_SQL_KEYWORDS: set[str] = {
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "TRUNCATE",
    "CREATE",
    "REPLACE",
    "GRANT",
    "REVOKE",
}


@tool
def get_expenses_by_status(status: str) -> str:
    """Retrieves corporate expenses filtered by status ('approved', 'pending', or 'rejected')."""
    normalized_status: str = status.strip().lower()
    logger.info(f"Executing tool: get_expenses_by_status(status='{normalized_status}')")

    db.connect(reuse_if_open=True)
    records: list[Expense] = list(
        Expense.select().where(Expense.status == normalized_status)
    )

    if not records:
        return f"No expenses found with status '{normalized_status}'."

    lines: list[str] = [
        f"ID={r.id} | Employee={r.employee_name} | Dept={r.department} | "
        f"Category={r.category} | Amount=BRL {r.amount:.2f} | Date={r.expense_date}"
        for r in records
    ]

    return "\n".join(lines)


@tool
def get_department_spending_summary() -> str:
    """Returns the total expense amount and record count grouped by department."""
    logger.info("Executing tool: get_department_spending_summary()")

    db.connect(reuse_if_open=True)
    query = (
        Expense.select(
            Expense.department,
            fn.COUNT(Expense.id).alias("total_count"),
            fn.SUM(Expense.amount).alias("total_amount"),
        )
        .group_by(Expense.department)
        .order_by(fn.SUM(Expense.amount).desc())
    )

    rows: list[Expense] = list(query)

    if not rows:
        return "No expense records available in the database."

    summary: list[str] = [
        f"Department={row.department} | Count={row.total_count} | Total=BRL {float(row.total_amount):.2f}" # type: ignore
        for row in rows
    ]

    return "\n".join(summary)


@tool
def execute_readonly_sql(sql_query: str) -> str:
    """
    Executes a read-only SELECT SQL query on the 'expenses' table in MariaDB.
    Table schema: expenses(id, employee_name, department, category, amount, status, expense_date).
    """
    cleaned_query: str = sql_query.strip().rstrip(";")
    logger.info(f"Executing tool: execute_readonly_sql(sql_query='{cleaned_query}')")

    upper_tokens: set[str] = set(cleaned_query.upper().split())

    if not cleaned_query.upper().startswith("SELECT") or (upper_tokens & FORBIDDEN_SQL_KEYWORDS):
        logger.warning(f"Blocked unsafe SQL attempt: {cleaned_query}")
        return "Security Error: Only read-only SELECT queries are permitted."

    try:
        db.connect(reuse_if_open=True)
        cursor = db.execute_sql(cleaned_query)
        columns: list[str] = [desc[0] for desc in cursor.description] if cursor.description else []
        rows: list[tuple[Any, ...]] = cursor.fetchall()

        if not rows:
            return "Query executed successfully, but returned 0 rows."

        formatted_rows: list[str] = [
            str(dict(zip(columns, row))) for row in rows[:25]
        ]

        return "\n".join(formatted_rows)

    except Exception as exc:
        logger.error(f"SQL execution error: {exc}")

        return f"Database error executing query: {exc}"
