"""MySQL connection helpers."""

from __future__ import annotations

from contextlib import contextmanager

import mysql.connector
from mysql.connector import Error

from config import MYSQL_CONFIG


def get_connection():
    """Return an open MySQL connection."""
    candidate_configs = [
        MYSQL_CONFIG,
    ]

    last_error = None
    for config in candidate_configs:
        try:
            try:
                return mysql.connector.connect(**config)
            except Error as exc:
                if getattr(exc, "errno", None) != 1049:
                    raise

                server_config = dict(config)
                server_config.pop("database", None)
                server_connection = mysql.connector.connect(**server_config)
                try:
                    cursor = server_connection.cursor()
                    cursor.execute(
                        f"CREATE DATABASE IF NOT EXISTS `{config['database']}` CHARACTER SET utf8mb4"
                    )
                    server_connection.commit()
                    cursor.close()
                finally:
                    server_connection.close()

                return mysql.connector.connect(**config)
        except Error as exc:
            last_error = exc

    raise last_error


def close_connection(connection):
    """Close a MySQL connection safely."""
    if connection is None:
        return

    try:
        if connection.is_connected():
            connection.close()
    except Error:
        print("Error closing MySQL connection")


def _is_read_query(query):
    normalized_query = query.lstrip().lower()
    return normalized_query.startswith(("select", "with", "show", "describe", "desc", "explain"))


def run_query(connection, query, parameters=None):
    """Run a parameterised SQL query and return results or affected rows."""
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(query, parameters or ())

        if _is_read_query(query):
            results = cursor.fetchall()
            return results

        connection.commit()
        return cursor.rowcount
    except Error:
        connection.rollback()
        print("SQL query failed and transaction was rolled back")
        raise
    finally:
        cursor.close()


@contextmanager
def mysql_session():
    """Provide a connection context manager for short database operations."""
    connection = get_connection()
    try:
        yield connection
    finally:
        close_connection(connection)
