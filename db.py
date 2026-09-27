import os
import psycopg2
from psycopg2.extras import RealDictCursor


def get_db_connection():
    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is not configured. "
            "Add your Render PostgreSQL connection string."
        )

    connection = psycopg2.connect(database_url)
    return connection


def init_database():
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS volunteers (
            volunteer_id SERIAL PRIMARY KEY,
            name TEXT,
            email TEXT,
            skills TEXT,
            interests TEXT,
            location TEXT,
            availability TEXT,
            experience TEXT,
            preferred_mode TEXT,
            hours_per_week INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ngos (
            ngo_id SERIAL PRIMARY KEY,
            name TEXT,
            email TEXT,
            cause TEXT,
            location TEXT,
            description TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS opportunities (
            opportunity_id SERIAL PRIMARY KEY,
            ngo_id INTEGER,
            title TEXT NOT NULL,
            description TEXT,
            cause TEXT,
            required_skills TEXT,
            location TEXT,
            availability TEXT,
            hours_required INTEGER,
            mode TEXT,
            experience_required TEXT,
            FOREIGN KEY (ngo_id) REFERENCES ngos(ngo_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS volunteer_profiles (
            profile_id SERIAL PRIMARY KEY,
            user_id INTEGER UNIQUE NOT NULL,
            skills TEXT,
            interests TEXT,
            location TEXT,
            availability TEXT,
            experience TEXT,
            preferred_mode TEXT,
            hours_per_week INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            application_id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            opportunity_id INTEGER NOT NULL,
            status TEXT DEFAULT 'Pending',
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, opportunity_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (opportunity_id) REFERENCES opportunities(opportunity_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            feedback_id SERIAL PRIMARY KEY,
            user_id INTEGER,
            opportunity_id INTEGER,
            rating INTEGER,
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.commit()
    cursor.close()
    connection.close()