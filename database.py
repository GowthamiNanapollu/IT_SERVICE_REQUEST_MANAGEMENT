import os
import ssl
import pymysql

from config import Config


def get_db_connection(select_database=True):
    certificate_path = os.path.join(
        os.path.dirname(__file__),
        "certs",
        "globalsignrootca.pem"
    )

    ssl_context = ssl.create_default_context(
        cafile=certificate_path
    )

    connection_args = {
        "host": Config.DB_HOST,
        "port": Config.DB_PORT,
        "user": Config.DB_USER,
        "password": Config.DB_PASSWORD,
        "connect_timeout": 15,
        "ssl": ssl_context,
        "autocommit": False
    }

    if select_database:
        if not Config.MYSQL_DATABASE:
            raise ValueError("MYSQL_DATABASE is missing in .env")

        connection_args["database"] = Config.MYSQL_DATABASE

    return pymysql.connect(**connection_args)

