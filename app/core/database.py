from peewee import MySQLDatabase
from app.core.config import settings

db: MySQLDatabase = MySQLDatabase(
    settings.DB_NAME,
    user=settings.DB_USER,
    password=settings.DB_PASSWORD,
    host=settings.DB_HOST,
    port=settings.DB_PORT,
)
