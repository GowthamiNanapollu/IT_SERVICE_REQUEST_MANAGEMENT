
from database import get_db_connection

connection = None

try:
    connection = get_db_connection(select_database=False)

    with connection.cursor() as cursor:
        cursor.execute("CREATE DATABASE it_service_db")

    connection.commit()
    print("Database created successfully!")

except Exception as error:
    print("Database creation failed:", error)

finally:
    if connection is not None:
        connection.close()
