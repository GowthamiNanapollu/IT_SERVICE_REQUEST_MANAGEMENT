
from database import get_db_connection

connection = None

try:
    connection = get_db_connection()

    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES")

        tables = cursor.fetchall()

        print("Tables in it_service_db:")

        if not tables:
            print("No tables found.")

        for table in tables:
            print("-", table[0])

except Exception as error:
    print("Verification failed:", error)

finally:
    if connection is not None:
        connection.close()
