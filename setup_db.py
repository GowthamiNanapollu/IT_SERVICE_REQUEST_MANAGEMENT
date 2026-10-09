from database import get_db_connection


def setup_database():
    connection = None

    try:
        connection = get_db_connection()

        with open("schema.sql", "r", encoding="utf-8") as file:
            sql_script = file.read()

        # Remove blank lines and SQL comment lines.
        lines = [
            line for line in sql_script.splitlines()
            if line.strip() and not line.strip().startswith("--")
        ]
        sql_script = "\n".join(lines)

        statements = [
            statement.strip()
            for statement in sql_script.split(";")
            if statement.strip()
        ]

        with connection.cursor() as cursor:
            for index, statement in enumerate(statements, start=1):
                try:
                    cursor.execute(statement)
                    print(f"Statement {index}: OK")
                except Exception as error:
                    print(f"Statement {index} failed: {error}")
                    raise

        connection.commit()
        print("\nDatabase setup completed successfully!")

    except Exception as error:
        if connection:
            connection.rollback()
        print("\nDatabase setup failed:", error)

    finally:
        if connection:
            connection.close()


if __name__ == "__main__":
    setup_database()