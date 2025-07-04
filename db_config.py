# db_connector.py
import mysql.connector

def get_connection():
    return mysql.connector.connect(
        host='127.0.0.1',
        user='root',
        password='raima1105',
        database='hotel_mgmt'
    )
