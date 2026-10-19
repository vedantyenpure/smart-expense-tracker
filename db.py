
import os
import mysql.connector
import streamlit as st
from dotenv import load_dotenv

load_dotenv()


def get_config(key, default=None):
    try:
        return st.secrets[key]
    except (KeyError, FileNotFoundError):
        return os.getenv(key, default)
    except Exception:
        return os.getenv(key, default)


def get_connection():
    return mysql.connector.connect(
        host=get_config("DB_HOST"),
        port=int(get_config("DB_PORT", "3306")),
        user=get_config("DB_USER"),
        password=get_config("DB_PASSWORD"),
        database=get_config("DB_NAME"),
        ssl_disabled=False,
    )


if __name__ == "__main__":
    try:
        connection = get_connection()
        print("Database connected successfully! ✅")
        connection.close()
    except Exception as error:
        print(f"Database connection failed: {error}")
