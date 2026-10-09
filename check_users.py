
from database import get_db_connection

connection = get_db_connection()

try:
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT user_id, email, role, employee_id, staff_id
            FROM users
            ORDER BY user_id
        """)

        for user in cursor.fetchall():
            print(user)

finally:
    connection.close()
