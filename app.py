from flask import Flask, render_template, request, redirect, url_for, session
import os
import sqlite3
import pandas as pd

from matching import rank_opportunities


# ============================================================
# APP CONFIGURATION
# ============================================================

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "sevaconnect-local-secret-key"
)

# IMPORTANT:
# DATABASE_URL must be the NAME of the Render environment variable.
#
# Render:
#   DATABASE_URL = your PostgreSQL Internal Database URL
#
# Local:
#   DATABASE_URL can be absent and SQLite will be used.
DATABASE_URL = os.environ.get("DATABASE_URL")

# Render normally provides RENDER=true.
IS_RENDER = os.environ.get("RENDER", "").lower() == "true"

SQLITE_DATABASE = "database.db"


# ============================================================
# DATABASE CONNECTION WRAPPER
# ============================================================

class DatabaseConnection:

    def __init__(self):

        # Use PostgreSQL whenever DATABASE_URL is available.
        # Otherwise use local SQLite.
        self.is_postgres = bool(DATABASE_URL)

        if self.is_postgres:

            import psycopg2
            from psycopg2.extras import RealDictCursor

            database_url = DATABASE_URL

            # Support old postgres:// URLs.
            if database_url.startswith("postgres://"):
                database_url = database_url.replace(
                    "postgres://",
                    "postgresql://",
                    1
                )

            self.connection = psycopg2.connect(
                database_url,
                cursor_factory=RealDictCursor
            )

        else:

            self.connection = sqlite3.connect(
                SQLITE_DATABASE
            )

            self.connection.row_factory = sqlite3.Row

    def execute(self, query, params=()):

        if self.is_postgres:
            query = query.replace("?", "%s")

        return self.connection.cursor().execute(
            query,
            params
        )

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    def close(self):
        self.connection.close()


def get_db_connection():
    return DatabaseConnection()


# ============================================================
# CREATE DATABASE TABLES
# ============================================================

def init_database():

    connection = get_db_connection()

    # --------------------------------------------------------
    # USERS
    # --------------------------------------------------------

    if connection.is_postgres:

        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL
            )
        """)

    else:

        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL
            )
        """)

    # --------------------------------------------------------
    # VOLUNTEERS
    # --------------------------------------------------------

    if connection.is_postgres:

        connection.execute("""
            CREATE TABLE IF NOT EXISTS volunteers (
                volunteer_id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                skills TEXT,
                interests TEXT,
                location TEXT,
                availability TEXT,
                experience TEXT,
                preferred_mode TEXT,
                hours_per_week INTEGER
            )
        """)

    else:

        connection.execute("""
            CREATE TABLE IF NOT EXISTS volunteers (
                volunteer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                skills TEXT,
                interests TEXT,
                location TEXT,
                availability TEXT,
                experience TEXT,
                preferred_mode TEXT,
                hours_per_week INTEGER
            )
        """)

    # --------------------------------------------------------
    # NGOs
    # --------------------------------------------------------

    if connection.is_postgres:

        connection.execute("""
            CREATE TABLE IF NOT EXISTS ngos (
                ngo_id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                cause TEXT,
                location TEXT,
                description TEXT,
                user_id INTEGER
            )
        """)

    else:

        connection.execute("""
            CREATE TABLE IF NOT EXISTS ngos (
                ngo_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                cause TEXT,
                location TEXT,
                description TEXT,
                user_id INTEGER
            )
        """)

    # --------------------------------------------------------
    # VOLUNTEER PROFILES
    # --------------------------------------------------------

    if connection.is_postgres:

        connection.execute("""
            CREATE TABLE IF NOT EXISTS volunteer_profiles (
                profile_id SERIAL PRIMARY KEY,
                user_id INTEGER UNIQUE NOT NULL,
                skills TEXT,
                interests TEXT,
                location TEXT,
                availability TEXT,
                experience TEXT,
                preferred_mode TEXT,
                hours_per_week INTEGER
            )
        """)

    else:

        connection.execute("""
            CREATE TABLE IF NOT EXISTS volunteer_profiles (
                profile_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                skills TEXT,
                interests TEXT,
                location TEXT,
                availability TEXT,
                experience TEXT,
                preferred_mode TEXT,
                hours_per_week INTEGER
            )
        """)

    # --------------------------------------------------------
    # OPPORTUNITIES
    # --------------------------------------------------------

    if connection.is_postgres:

        connection.execute("""
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
                experience_required TEXT
            )
        """)

    else:

        connection.execute("""
            CREATE TABLE IF NOT EXISTS opportunities (
                opportunity_id INTEGER PRIMARY KEY AUTOINCREMENT,
                ngo_id INTEGER,
                title TEXT NOT NULL,
                description TEXT,
                cause TEXT,
                required_skills TEXT,
                location TEXT,
                availability TEXT,
                hours_required INTEGER,
                mode TEXT,
                experience_required TEXT
            )
        """)

    # --------------------------------------------------------
    # APPLICATIONS
    # --------------------------------------------------------

    if connection.is_postgres:

        connection.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                application_id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                opportunity_id INTEGER NOT NULL,
                status TEXT DEFAULT 'Pending',
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, opportunity_id)
            )
        """)

    else:

        connection.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                application_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                opportunity_id INTEGER NOT NULL,
                status TEXT DEFAULT 'Pending',
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, opportunity_id)
            )
        """)

    # --------------------------------------------------------
    # FEEDBACK
    # --------------------------------------------------------

    if connection.is_postgres:

        connection.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                feedback_id SERIAL PRIMARY KEY,
                volunteer_id INTEGER,
                opportunity_id INTEGER,
                rating INTEGER,
                comments TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    else:

        connection.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
                volunteer_id INTEGER,
                opportunity_id INTEGER,
                rating INTEGER,
                comments TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    connection.commit()
    connection.close()

    print("Database tables initialized successfully.")


# ============================================================
# LOAD CSV DATA
# ============================================================

def load_csv_data():

    connection = get_db_connection()

    try:

        volunteers = pd.read_csv(
            "volunteers_100.csv"
        )

        ngos = pd.read_csv(
            "ngos_30.csv"
        )

        opportunities = pd.read_csv(
            "opportunities_100.csv"
        )

    except FileNotFoundError:

        print(
            "CSV files not found. "
            "Skipping synthetic data loading."
        )

        connection.close()

        return

    # --------------------------------------------------------
    # INSERT NGOs
    # --------------------------------------------------------

    for _, row in ngos.iterrows():

        email = (
            f"{row['ngo_id']}@synthetic.sevaconnect"
        )

        existing = connection.execute(
            """
            SELECT ngo_id
            FROM ngos
            WHERE email = ?
            """,
            (email,)
        ).fetchone()

        if existing is None:

            connection.execute(
                """
                INSERT INTO ngos
                (
                    name,
                    email,
                    cause,
                    location,
                    description
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    row["ngo_name"],
                    email,
                    row["cause"],
                    row["location"],
                    "Synthetic NGO record for SevaConnect prototype."
                )
            )

    # --------------------------------------------------------
    # INSERT VOLUNTEERS
    # --------------------------------------------------------

    for _, row in volunteers.iterrows():

        email = (
            f"{row['volunteer_id']}@synthetic.sevaconnect"
        )

        existing = connection.execute(
            """
            SELECT volunteer_id
            FROM volunteers
            WHERE email = ?
            """,
            (email,)
        ).fetchone()

        if existing is None:

            connection.execute(
                """
                INSERT INTO volunteers
                (
                    name,
                    email,
                    skills,
                    interests,
                    location,
                    availability,
                    experience,
                    preferred_mode,
                    hours_per_week
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["volunteer_id"],
                    email,
                    row["skills"],
                    row["interests"],
                    row["location"],
                    row["availability"],
                    row["experience"],
                    row["preferred_mode"],
                    int(row["hours_per_week"])
                )
            )

    # --------------------------------------------------------
    # INSERT OPPORTUNITIES
    # --------------------------------------------------------

    for _, row in opportunities.iterrows():

        ngo = connection.execute(
            """
            SELECT ngo_id
            FROM ngos
            WHERE name = ?
            """,
            (row["ngo_name"],)
        ).fetchone()

        if ngo is None:
            continue

        existing = connection.execute(
            """
            SELECT opportunity_id
            FROM opportunities
            WHERE title = ?
            AND ngo_id = ?
            """,
            (
                row["opportunity_title"],
                ngo["ngo_id"]
            )
        ).fetchone()

        if existing is None:

            connection.execute(
                """
                INSERT INTO opportunities
                (
                    ngo_id,
                    title,
                    description,
                    cause,
                    required_skills,
                    location,
                    availability,
                    hours_required,
                    mode,
                    experience_required
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ngo["ngo_id"],
                    row["opportunity_title"],
                    (
                        f"{row['opportunity_title']} "
                        f"offered by {row['ngo_name']}."
                    ),
                    row["cause"],
                    row["required_skills"],
                    row["location"],
                    row["availability"],
                    int(row["hours_required"]),
                    row["mode"],
                    row["experience_required"]
                )
            )

    connection.commit()
    connection.close()

    print("CSV data loaded successfully.")


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# ============================================================
# REGISTER
# ============================================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        role = request.form["role"]

        connection = get_db_connection()

        try:

            connection.execute(
                """
                INSERT INTO users
                (
                    name,
                    email,
                    password,
                    role
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    name,
                    email,
                    password,
                    role
                )
            )

            connection.commit()

        except Exception:

            connection.rollback()
            connection.close()

            return """
                <h2>Email already registered.</h2>
                <a href="/register">
                    Try again
                </a>
            """

        connection.close()

        return redirect(
            url_for("login")
        )

    return render_template(
        "register.html"
    )


# ============================================================
# LOGIN
# ============================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        connection = get_db_connection()

        user = connection.execute(
            """
            SELECT *
            FROM users
            WHERE email = ?
            AND password = ?
            """,
            (
                email,
                password
            )
        ).fetchone()

        connection.close()

        if user is None:

            return """
                <h2>Invalid email or password.</h2>
                <a href="/login">
                    Try again
                </a>
            """

        session["user_id"] = user["user_id"]
        session["name"] = user["name"]
        session["role"] = user["role"]

        if user["role"] == "volunteer":

            return redirect(
                url_for("volunteer_dashboard")
            )

        if user["role"] == "ngo":

            return redirect(
                url_for("ngo_dashboard")
            )

    return render_template(
        "login.html"
    )


# ============================================================
# VOLUNTEER PROFILE
# ============================================================

@app.route(
    "/volunteer-profile",
    methods=["GET", "POST"]
)
def volunteer_profile():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "volunteer":
        return redirect(url_for("login"))

    connection = get_db_connection()

    if request.method == "POST":

        name = request.form["name"]
        skills = request.form["skills"]
        interests = request.form["interests"]
        location = request.form["location"]
        availability = request.form["availability"]
        experience = request.form["experience"]
        preferred_mode = request.form["preferred_mode"]
        hours_per_week = request.form["hours_per_week"]

        connection.execute(
            """
            UPDATE users
            SET name = ?
            WHERE user_id = ?
            """,
            (
                name,
                session["user_id"]
            )
        )

        existing = connection.execute(
            """
            SELECT profile_id
            FROM volunteer_profiles
            WHERE user_id = ?
            """,
            (
                session["user_id"],
            )
        ).fetchone()

        if existing:

            connection.execute(
                """
                UPDATE volunteer_profiles
                SET
                    skills = ?,
                    interests = ?,
                    location = ?,
                    availability = ?,
                    experience = ?,
                    preferred_mode = ?,
                    hours_per_week = ?
                WHERE user_id = ?
                """,
                (
                    skills,
                    interests,
                    location,
                    availability,
                    experience,
                    preferred_mode,
                    hours_per_week,
                    session["user_id"]
                )
            )

        else:

            connection.execute(
                """
                INSERT INTO volunteer_profiles
                (
                    user_id,
                    skills,
                    interests,
                    location,
                    availability,
                    experience,
                    preferred_mode,
                    hours_per_week
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session["user_id"],
                    skills,
                    interests,
                    location,
                    availability,
                    experience,
                    preferred_mode,
                    hours_per_week
                )
            )

        connection.commit()
        connection.close()

        session["name"] = name

        return redirect(
            url_for("volunteer_dashboard")
        )

    profile = connection.execute(
        """
        SELECT *
        FROM volunteer_profiles
        WHERE user_id = ?
        """,
        (
            session["user_id"],
        )
    ).fetchone()

    connection.close()

    return render_template(
        "volunteer_profile.html",
        profile=profile
    )


# ============================================================
# VOLUNTEER DASHBOARD
# ============================================================

@app.route("/volunteer-dashboard")
def volunteer_dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "volunteer":
        return redirect(url_for("login"))

    connection = get_db_connection()

    user = connection.execute(
        """
        SELECT *
        FROM users
        WHERE user_id = ?
        """,
        (
            session["user_id"],
        )
    ).fetchone()

    profile = connection.execute(
        """
        SELECT *
        FROM volunteer_profiles
        WHERE user_id = ?
        """,
        (
            session["user_id"],
        )
    ).fetchone()

    opportunity_rows = connection.execute(
        """
        SELECT
            opportunities.*,
            ngos.name AS ngo_name
        FROM opportunities
        LEFT JOIN ngos
            ON opportunities.ngo_id = ngos.ngo_id
        """
    ).fetchall()

    applications = connection.execute(
        """
        SELECT
            applications.application_id,
            applications.opportunity_id,
            applications.status,
            applications.applied_at,
            opportunities.title,
            opportunities.cause,
            ngos.name AS ngo_name
        FROM applications
        JOIN opportunities
            ON applications.opportunity_id =
               opportunities.opportunity_id
        LEFT JOIN ngos
            ON opportunities.ngo_id = ngos.ngo_id
        WHERE applications.user_id = ?
        ORDER BY applications.applied_at DESC
        """,
        (
            session["user_id"],
        )
    ).fetchall()

    completed = connection.execute(
        """
        SELECT COUNT(*) AS total
        FROM applications
        WHERE user_id = ?
        AND status = 'Completed'
        """,
        (
            session["user_id"],
        )
    ).fetchone()

    connection.close()

    # --------------------------------------------------------
    # BUILD VOLUNTEER OBJECT
    # --------------------------------------------------------

    volunteer = None

    if user and profile:

        volunteer = {
            "name": user["name"],
            "skills": profile["skills"] or "",
            "interests": profile["interests"] or "",
            "location": profile["location"] or "",
            "availability": profile["availability"] or "",
            "experience": profile["experience"] or "beginner",
            "preferred_mode": profile["preferred_mode"] or "offline",
            "hours_per_week": profile["hours_per_week"] or 0
        }

    # --------------------------------------------------------
    # BUILD OPPORTUNITIES
    # --------------------------------------------------------

    opportunity_list = []

    for row in opportunity_rows:

        opportunity_list.append(
            {
                "opportunity_id": row["opportunity_id"],
                "ngo_id": row["ngo_id"],
                "ngo_name": row["ngo_name"] or "Organization",
                "cause": row["cause"] or "",
                "opportunity_title": row["title"],
                "required_skills": row["required_skills"] or "",
                "location": row["location"] or "",
                "availability": row["availability"] or "",
                "hours_required": row["hours_required"] or 0,
                "mode": row["mode"] or "offline",
                "experience_required":
                    row["experience_required"] or "beginner"
            }
        )

    # --------------------------------------------------------
    # RECOMMENDATIONS
    # --------------------------------------------------------

    recommendations = []

    if volunteer and opportunity_list:

        recommendations = rank_opportunities(
            volunteer,
            opportunity_list,
            top_n=5
        )

    return render_template(
        "volunteer_dashboard.html",
        recommendations=recommendations,
        applications=applications,
        profile=profile,
        volunteer=volunteer,
        completed_activities=completed["total"]
    )


# ============================================================
# APPLY FOR OPPORTUNITY
# ============================================================

@app.route(
    "/apply/<int:opportunity_id>",
    methods=["POST"]
)
def apply_opportunity(opportunity_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "volunteer":
        return redirect(url_for("login"))

    connection = get_db_connection()

    opportunity = connection.execute(
        """
        SELECT opportunity_id
        FROM opportunities
        WHERE opportunity_id = ?
        """,
        (
            opportunity_id,
        )
    ).fetchone()

    if opportunity is None:

        connection.close()

        return """
            <h2>Opportunity not found.</h2>
            <a href="/volunteer-dashboard">
                Back to Dashboard
            </a>
        """

    existing = connection.execute(
        """
        SELECT application_id
        FROM applications
        WHERE user_id = ?
        AND opportunity_id = ?
        """,
        (
            session["user_id"],
            opportunity_id
        )
    ).fetchone()

    if existing:

        connection.close()

        return redirect(
            url_for("volunteer_dashboard")
        )

    connection.execute(
        """
        INSERT INTO applications
        (
            user_id,
            opportunity_id,
            status
        )
        VALUES (?, ?, 'Pending')
        """,
        (
            session["user_id"],
            opportunity_id
        )
    )

    connection.commit()
    connection.close()

    return redirect(
        url_for("volunteer_dashboard")
    )


# ============================================================
# NGO PROFILE HELPER
# ============================================================

def get_ngo_for_user(connection, user_id):

    ngo = connection.execute(
        """
        SELECT *
        FROM ngos
        WHERE user_id = ?
        LIMIT 1
        """,
        (
            user_id,
        )
    ).fetchone()

    if ngo:
        return ngo

    user = connection.execute(
        """
        SELECT *
        FROM users
        WHERE user_id = ?
        """,
        (
            user_id,
        )
    ).fetchone()

    if not user:
        return None

    ngo = connection.execute(
        """
        SELECT *
        FROM ngos
        WHERE email = ?
        LIMIT 1
        """,
        (
            user["email"],
        )
    ).fetchone()

    if ngo:

        connection.execute(
            """
            UPDATE ngos
            SET user_id = ?
            WHERE ngo_id = ?
            """,
            (
                user_id,
                ngo["ngo_id"]
            )
        )

        connection.commit()

        return connection.execute(
            """
            SELECT *
            FROM ngos
            WHERE ngo_id = ?
            """,
            (
                ngo["ngo_id"],
            )
        ).fetchone()

    return None


# ============================================================
# NGO PROFILE
# ============================================================

@app.route(
    "/ngo-profile",
    methods=["GET", "POST"]
)
def ngo_profile():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "ngo":
        return redirect(url_for("login"))

    connection = get_db_connection()

    user = connection.execute(
        """
        SELECT *
        FROM users
        WHERE user_id = ?
        """,
        (
            session["user_id"],
        )
    ).fetchone()

    ngo = get_ngo_for_user(
        connection,
        session["user_id"]
    )

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        cause = request.form["cause"]
        location = request.form["location"]
        description = request.form["description"]

        if ngo:

            connection.execute(
                """
                UPDATE ngos
                SET
                    name = ?,
                    email = ?,
                    cause = ?,
                    location = ?,
                    description = ?
                WHERE ngo_id = ?
                """,
                (
                    name,
                    email,
                    cause,
                    location,
                    description,
                    ngo["ngo_id"]
                )
            )

        else:

            connection.execute(
                """
                INSERT INTO ngos
                (
                    name,
                    email,
                    cause,
                    location,
                    description,
                    user_id
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    email,
                    cause,
                    location,
                    description,
                    session["user_id"]
                )
            )

        connection.execute(
            """
            UPDATE users
            SET name = ?, email = ?
            WHERE user_id = ?
            """,
            (
                name,
                email,
                session["user_id"]
            )
        )

        connection.commit()
        connection.close()

        session["name"] = name

        return redirect(
            url_for("ngo_dashboard")
        )

    connection.close()

    return render_template(
        "ngo_profile.html",
        ngo=ngo,
        user=user
    )


# ============================================================
# CREATE OPPORTUNITY
# ============================================================

@app.route(
    "/create-opportunity",
    methods=["GET", "POST"]
)
def create_opportunity():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "ngo":
        return redirect(url_for("login"))

    connection = get_db_connection()

    ngo = get_ngo_for_user(
        connection,
        session["user_id"]
    )

    if ngo is None:

        connection.close()

        return redirect(
            url_for("ngo_profile")
        )

    if request.method == "POST":

        title = request.form["title"]
        description = request.form["description"]
        cause = request.form["cause"]
        required_skills = request.form["required_skills"]
        location = request.form["location"]
        availability = request.form["availability"]
        hours_required = request.form["hours_required"]
        mode = request.form["mode"]
        experience_required = request.form[
            "experience_required"
        ]

        connection.execute(
            """
            INSERT INTO opportunities
            (
                ngo_id,
                title,
                description,
                cause,
                required_skills,
                location,
                availability,
                hours_required,
                mode,
                experience_required
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ngo["ngo_id"],
                title,
                description,
                cause,
                required_skills,
                location,
                availability,
                hours_required,
                mode,
                experience_required
            )
        )

        connection.commit()
        connection.close()

        return redirect(
            url_for("ngo_dashboard")
        )

    connection.close()

    return render_template(
        "create_opportunity.html",
        ngo=ngo
    )


# ============================================================
# DELETE OPPORTUNITY
# ============================================================

@app.route(
    "/delete-opportunity/<int:opportunity_id>",
    methods=["POST"]
)
def delete_opportunity(opportunity_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "ngo":
        return redirect(url_for("login"))

    connection = get_db_connection()

    ngo = get_ngo_for_user(
        connection,
        session["user_id"]
    )

    if ngo:

        opportunity = connection.execute(
            """
            SELECT opportunity_id
            FROM opportunities
            WHERE opportunity_id = ?
            AND ngo_id = ?
            """,
            (
                opportunity_id,
                ngo["ngo_id"]
            )
        ).fetchone()

        if opportunity:

            connection.execute(
                """
                DELETE FROM applications
                WHERE opportunity_id = ?
                """,
                (
                    opportunity_id,
                )
            )

            connection.execute(
                """
                DELETE FROM feedback
                WHERE opportunity_id = ?
                """,
                (
                    opportunity_id,
                )
            )

            connection.execute(
                """
                DELETE FROM opportunities
                WHERE opportunity_id = ?
                """,
                (
                    opportunity_id,
                )
            )

            connection.commit()

    connection.close()

    return redirect(
        url_for("ngo_dashboard")
    )


# ============================================================
# NGO DASHBOARD
# ============================================================

@app.route("/ngo-dashboard")
def ngo_dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "ngo":
        return redirect(url_for("login"))

    connection = get_db_connection()

    # --------------------------------------------------------
    # GET NGO PROFILE
    # --------------------------------------------------------

    ngo = get_ngo_for_user(
        connection,
        session["user_id"]
    )

    if ngo is None:

        connection.close()

        return redirect(
            url_for("ngo_profile")
        )

    # --------------------------------------------------------
    # GET OPPORTUNITIES CREATED BY THIS NGO
    # --------------------------------------------------------

    opportunities = connection.execute(
        """
        SELECT *
        FROM opportunities
        WHERE ngo_id = ?
        ORDER BY opportunity_id DESC
        """,
        (
            ngo["ngo_id"],
        )
    ).fetchall()

    # --------------------------------------------------------
    # GET ALL VOLUNTEERS WHO APPLIED
    # --------------------------------------------------------

    applicants = connection.execute(
        """
        SELECT
            applications.application_id,
            applications.status,
            applications.applied_at,

            users.user_id,
            users.name AS volunteer_name,
            users.email AS volunteer_email,

            volunteer_profiles.skills,
            volunteer_profiles.interests,
            volunteer_profiles.location,
            volunteer_profiles.availability,
            volunteer_profiles.experience,
            volunteer_profiles.preferred_mode,
            volunteer_profiles.hours_per_week,

            opportunities.opportunity_id,
            opportunities.title AS opportunity_title

        FROM applications

        INNER JOIN users
            ON applications.user_id = users.user_id

        LEFT JOIN volunteer_profiles
            ON applications.user_id = volunteer_profiles.user_id

        INNER JOIN opportunities
            ON applications.opportunity_id =
               opportunities.opportunity_id

        WHERE opportunities.ngo_id = ?

        ORDER BY applications.applied_at DESC
        """,
        (
            ngo["ngo_id"],
        )
    ).fetchall()

    # --------------------------------------------------------
    # APPLICATION COUNTS
    # --------------------------------------------------------

    total_applications = len(applicants)

    pending_applications = sum(
        1
        for applicant in applicants
        if applicant["status"] == "Pending"
    )

    accepted_applications = sum(
        1
        for applicant in applicants
        if applicant["status"] == "Accepted"
    )

    completed_applications = sum(
        1
        for applicant in applicants
        if applicant["status"] == "Completed"
    )

    connection.close()

    return render_template(
        "ngo_dashboard.html",
        ngo=ngo,
        opportunities=opportunities,
        applicants=applicants,
        total_applications=total_applications,
        pending_applications=pending_applications,
        accepted_applications=accepted_applications,
        completed_applications=completed_applications
    )


# ============================================================
# UPDATE APPLICATION STATUS
# ============================================================

@app.route(
    "/ngo/application/<int:application_id>/<string:new_status>",
    methods=["POST"]
)
def update_application_status(
    application_id,
    new_status
):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "ngo":
        return redirect(url_for("login"))

    allowed_statuses = [
        "Pending",
        "Accepted",
        "Rejected",
        "Completed"
    ]

    if new_status not in allowed_statuses:
        return redirect(
            url_for("ngo_dashboard")
        )

    connection = get_db_connection()

    # --------------------------------------------------------
    # GET NGO
    # --------------------------------------------------------

    ngo = get_ngo_for_user(
        connection,
        session["user_id"]
    )

    if ngo is None:

        connection.close()

        return redirect(
            url_for("ngo_dashboard")
        )

    # --------------------------------------------------------
    # VERIFY APPLICATION BELONGS TO THIS NGO
    # --------------------------------------------------------

    application = connection.execute(
        """
        SELECT
            applications.application_id
        FROM applications

        INNER JOIN opportunities
            ON applications.opportunity_id =
               opportunities.opportunity_id

        WHERE applications.application_id = ?
        AND opportunities.ngo_id = ?
        """,
        (
            application_id,
            ngo["ngo_id"]
        )
    ).fetchone()

    if application is None:

        connection.close()

        return redirect(
            url_for("ngo_dashboard")
        )

    # --------------------------------------------------------
    # UPDATE STATUS
    # --------------------------------------------------------

    connection.execute(
        """
        UPDATE applications
        SET status = ?
        WHERE application_id = ?
        """,
        (
            new_status,
            application_id
        )
    )

    connection.commit()
    connection.close()

    return redirect(
        url_for("ngo_dashboard")
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("home")
    )


# ============================================================
# INITIALIZE DATABASE
# ============================================================

def initialize_application():

    print("----------------------------------------")
    print("SevaConnect starting...")
    print("----------------------------------------")

    if DATABASE_URL:

        print(
            "Database mode: PostgreSQL"
        )

    else:

        print(
            "Database mode: SQLite (local development)"
        )

    init_database()
    load_csv_data()


# ============================================================
# START
# ============================================================

initialize_application()


if __name__ == "__main__":

    app.run(
        debug=True,
        use_reloader=False
    )