
from database import get_db_connection


def test_database_connection():
    connection = None

    try:
        connection = get_db_connection()

        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()

        assert result is not None
        print("Database connection successful!")
        print("Query result:", result)

    finally:
        if connection:
            connection.close()


if __name__ == "__main__":
    test_database_connection()
