
from database import get_db_connection

connection = None

try:
    connection = get_db_connection()

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT
                request_id,
                subject,
                priority,
                status,
                created_at,
                sla_due_at
            FROM service_requests
            ORDER BY request_id DESC
        """)

        rows = cursor.fetchall()

        for row in rows:
            print(f"ID: {row[0]}")
            print(f"Subject: {row[1]}")
            print(f"Priority: {row[2]}")
            print(f"Status: {row[3]}")
            print(f"Created at: {row[4]}")
            print(f"SLA deadline: {row[5]}")
            print("-" * 40)

except Exception as error:
    print("Error:", error)

finally:
    if connection:
        connection.close()
