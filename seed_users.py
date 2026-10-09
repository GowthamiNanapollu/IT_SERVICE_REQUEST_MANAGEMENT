
from werkzeug.security import generate_password_hash
from database import get_db_connection

DEMO_ACCOUNTS = [
    {
        "email": "santhosh@gmail.com",
        "password": "Santhosh@123",
        "role": "employee",
        "reference_column": "employee_id",
        "reference_id": 2,
    },
    {
        "email": "sara@gmail.com",
        "password": "sara@123",
        "role": "it_staff",
        "reference_column": "staff_id",
        "reference_id": 2,
    },
]


def create_demo_accounts():
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            for account in DEMO_ACCOUNTS:
                cursor.execute(
                    "SELECT user_id FROM users WHERE email = %s",
                    (account["email"],),
                )

                if cursor.fetchone():
                    print(f"Account already exists: {account['email']}")
                    continue

                reference_column = account["reference_column"]

                query = f"""
                    INSERT INTO users
                    (email, password_hash, role, {reference_column})
                    VALUES (%s, %s, %s, %s)
                """

                password_hash = generate_password_hash(
                    account["password"]
                )

                cursor.execute(
                    query,
                    (
                        account["email"],
                        password_hash,
                        account["role"],
                        account["reference_id"],
                    ),
                )

                print(f"Created {account['role']} account: {account['email']}")

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    create_demo_accounts()
