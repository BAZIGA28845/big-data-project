import logging
import os

import psycopg2
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def get_connection():
    """
    Opens a connection to PostgreSQL using credentials from .env.
    Raises a clear RuntimeError if the connection fails (e.g. wrong
    password, Postgres service not running, database doesn't exist)
    instead of letting a raw psycopg2 traceback bubble up.
    """
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            connect_timeout=10,
        )
        logger.info("Connected to PostgreSQL successfully")
        return conn
    except psycopg2.OperationalError as e:
        logger.error(f"Could not connect to PostgreSQL: {e}")
        raise RuntimeError(
            "Database connection failed - check that PostgreSQL is running "
            "and your .env credentials are correct"
        ) from e