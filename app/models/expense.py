import datetime

from peewee import CharField, DateField, DecimalField, Model
from app.core.database import db


class Expense(Model):
    id: int
    employee_name: CharField = CharField(max_length=120)
    department: CharField = CharField(max_length=80)
    category: CharField = CharField(max_length=80)
    amount: DecimalField = DecimalField(max_digits=10, decimal_places=2)
    status: CharField = CharField(max_length=20)  # 'approved', 'pending', 'rejected'
    expense_date: DateField = DateField(default=datetime.date.today)

    class Meta:
        database = db
        table_name = "expenses"
