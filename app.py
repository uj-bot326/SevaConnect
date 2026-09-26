from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import pandas as pd

from matching import rank_opportunities


# ============================================================
# APP CONFIGURATION
# ============================================================

app = Flask(__name__)

app.secret_key = "sevaconnect-secret-key"

DATABASE = "database.db"


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_db_connection():

    connection = sqlite3.connect(DATABASE)

    connection.row_factory = sqlite3.Row

    return connection


# ============================================================
# DATABASE HELPER
# ============================================================

def add_column_if_missing(
    connection,
    table_name,
    column_name,
    column_definition
):

    columns = connection.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    existing_columns = [
        column["name"]
        for column in columns
    ]

    if column_name not in existing_columns:

        connection.execute(
            f"""
            ALTER TABLE {table_name}
            ADD COLUMN {column_name}
            {column_definition}
            """
        )


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_database():

    connection = get_db_connection()


    # --------------------------------------------------------
    # Volunteers
    # --------------------------------------------------------

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

    connection.execute("""
        CREATE TABLE IF NOT EXISTS ngos (

            ngo_id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            email TEXT UNIQUE NOT NULL,

            cause TEXT,

            location TEXT,

            description TEXT

        )
    """)


    # Add user_id to existing NGO table if needed

    add_column_if_missing(
        connection,
        "ngos",
        "user_id",
        "INTEGER"
    )


    # --------------------------------------------------------
    # Opportunities
    # --------------------------------------------------------

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

            experience_required TEXT,

            FOREIGN KEY (ngo_id)
                REFERENCES ngos(ngo_id)

        )
    """)


    # --------------------------------------------------------
    # Feedback
    # --------------------------------------------------------

    connection.execute("""
        CREATE TABLE IF NOT EXISTS feedback (

            feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,

            volunteer_id INTEGER,

            opportunity_id INTEGER,

            rating INTEGER,

            comments TEXT,

            created_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (volunteer_id)
                REFERENCES volunteers(volunteer_id),

            FOREIGN KEY (opportunity_id)
                REFERENCES opportunities(opportunity_id)

        )
    """)


    # --------------------------------------------------------
    # Users
    # --------------------------------------------------------

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
    # Volunteer Profiles
    # --------------------------------------------------------

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

            hours_per_week INTEGER,

            FOREIGN KEY (user_id)
                REFERENCES users(user_id)

        )
    """)


    # --------------------------------------------------------
    # Applications
    # --------------------------------------------------------

    connection.execute("""
        CREATE TABLE IF NOT EXISTS applications (

            application_id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            opportunity_id INTEGER NOT NULL,

            status TEXT DEFAULT 'Pending',

            applied_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(user_id, opportunity_id),

            FOREIGN KEY (user_id)
                REFERENCES users(user_id),

            FOREIGN KEY (opportunity_id)
                REFERENCES opportunities(opportunity_id)

        )
    """)


    connection.commit()

    connection.close()


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

    except FileNotFoundError as error:

        print(
            "CSV file not found:",
            error
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

    print(
        "CSV data loaded successfully!"
    )


# ============================================================
# SAFE VALUE HELPER
# ============================================================

def safe_value(
    row,
    names,
    default=""
):

    if row is None:

        return default


    for name in names:

        try:

            if name in row.keys():

                value = row[name]

                if value is not None:

                    return value

        except Exception:

            pass


    return default


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


        except sqlite3.IntegrityError:

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
                url_for(
                    "volunteer_dashboard"
                )
            )


        if user["role"] == "ngo":

            return redirect(
                url_for(
                    "ngo_dashboard"
                )
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

        return redirect(
            url_for("login")
        )


    if session.get("role") != "volunteer":

        return redirect(
            url_for("login")
        )


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


        existing_profile = connection.execute(
            """
            SELECT profile_id
            FROM volunteer_profiles
            WHERE user_id = ?
            """,
            (
                session["user_id"],
            )
        ).fetchone()


        if existing_profile:

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
            url_for(
                "volunteer_dashboard"
            )
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
# NORMALIZE RECOMMENDATIONS
# ============================================================

def normalize_recommendations(
    raw_recommendations,
    opportunity_list
):

    normalized = []


    if not raw_recommendations:

        return normalized


    for item in raw_recommendations:

        if not isinstance(item, dict):

            continue


        if "opportunity" in item:

            base = item.get(
                "opportunity"
            )

            if not isinstance(base, dict):

                continue

            opportunity = dict(base)

            score = item.get(
                "score",
                item.get(
                    "match_score",
                    0
                )
            )

        else:

            opportunity = dict(item)

            score = opportunity.get(
                "score",
                opportunity.get(
                    "match_score",
                    0
                )
            )


        if "opportunity_id" not in opportunity:

            if "id" in opportunity:

                opportunity["opportunity_id"] = (
                    opportunity["id"]
                )


        if "opportunity_title" not in opportunity:

            if "title" in opportunity:

                opportunity["opportunity_title"] = (
                    opportunity["title"]
                )

            elif "opportunity_name" in opportunity:

                opportunity["opportunity_title"] = (
                    opportunity["opportunity_name"]
                )

            elif "name" in opportunity:

                opportunity["opportunity_title"] = (
                    opportunity["name"]
                )

            else:

                opportunity["opportunity_title"] = (
                    "Volunteer Opportunity"
                )


        opportunity.setdefault(
            "ngo_name",
            "Organization"
        )

        opportunity.setdefault(
            "cause",
            ""
        )

        opportunity.setdefault(
            "required_skills",
            ""
        )

        opportunity.setdefault(
            "location",
            ""
        )

        opportunity.setdefault(
            "availability",
            ""
        )

        opportunity.setdefault(
            "hours_required",
            0
        )

        opportunity.setdefault(
            "mode",
            "offline"
        )

        opportunity.setdefault(
            "experience_required",
            "beginner"
        )


        try:

            score = float(score)

        except (
            TypeError,
            ValueError
        ):

            score = 0


        if score <= 1:

            score = score * 100


        opportunity["score"] = round(
            max(
                0,
                min(
                    score,
                    100
                )
            ),
            1
        )


        if opportunity.get(
            "opportunity_id"
        ) is not None:

            normalized.append(
                opportunity
            )


    if not normalized and opportunity_list:

        for opportunity in opportunity_list[:5]:

            fallback = dict(
                opportunity
            )

            fallback["score"] = 0

            normalized.append(
                fallback
            )


    return normalized[:5]


# ============================================================
# VOLUNTEER DASHBOARD
# ============================================================

@app.route(
    "/volunteer-dashboard"
)
def volunteer_dashboard():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    if session.get("role") != "volunteer":

        return redirect(
            url_for("login")
        )


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


    profile_row = connection.execute(
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
            ON opportunities.ngo_id =
               ngos.ngo_id

        ORDER BY opportunities.opportunity_id ASC
        """
    ).fetchall()


    application_rows = connection.execute(
        """
        SELECT

            applications.application_id,

            applications.opportunity_id,

            applications.status,

            applications.applied_at,

            opportunities.title,

            opportunities.cause,

            opportunities.location,

            opportunities.mode,

            opportunities.hours_required,

            ngos.name AS ngo_name

        FROM applications

        JOIN opportunities
            ON applications.opportunity_id =
               opportunities.opportunity_id

        LEFT JOIN ngos
            ON opportunities.ngo_id =
               ngos.ngo_id

        WHERE applications.user_id = ?

        ORDER BY applications.applied_at DESC
        """,
        (
            session["user_id"],
        )
    ).fetchall()


    applied_rows = connection.execute(
        """
        SELECT opportunity_id

        FROM applications

        WHERE user_id = ?
        """,
        (
            session["user_id"],
        )
    ).fetchall()


    applied_opportunity_ids = {
        row["opportunity_id"]
        for row in applied_rows
    }


    completed_row = connection.execute(
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


    completed_activities = (
        completed_row["total"]
        if completed_row
        else 0
    )


    connection.close()


    volunteer = None


    if user:

        volunteer = {

            "name": user["name"],

            "skills": safe_value(
                profile_row,
                [
                    "skills",
                    "skill"
                ]
            ),

            "interests": safe_value(
                profile_row,
                [
                    "interests",
                    "interest"
                ]
            ),

            "location": safe_value(
                profile_row,
                [
                    "location",
                    "city"
                ]
            ),

            "availability": safe_value(
                profile_row,
                [
                    "availability",
                    "available_days"
                ]
            ),

            "experience": safe_value(
                profile_row,
                [
                    "experience",
                    "experience_level"
                ],
                "beginner"
            ),

            "preferred_mode": safe_value(
                profile_row,
                [
                    "preferred_mode",
                    "mode",
                    "preferred_volunteering_mode"
                ],
                "offline"
            ),

            "hours_per_week": safe_value(
                profile_row,
                [
                    "hours_per_week",
                    "hours"
                ],
                0
            )
        }


    opportunity_list = []


    for row in opportunity_rows:

        opportunity = {

            "opportunity_id":
                safe_value(
                    row,
                    [
                        "opportunity_id",
                        "id"
                    ]
                ),

            "ngo_id":
                safe_value(
                    row,
                    [
                        "ngo_id"
                    ]
                ),

            "ngo_name":
                safe_value(
                    row,
                    [
                        "ngo_name",
                        "name"
                    ],
                    "Organization"
                ),

            "cause":
                safe_value(
                    row,
                    [
                        "cause",
                        "category"
                    ]
                ),

            "opportunity_title":
                safe_value(
                    row,
                    [
                        "title",
                        "opportunity_title",
                        "opportunity_name",
                        "name"
                    ],
                    "Volunteer Opportunity"
                ),

            "required_skills":
                safe_value(
                    row,
                    [
                        "required_skills",
                        "skills_required",
                        "skills"
                    ]
                ),

            "location":
                safe_value(
                    row,
                    [
                        "location",
                        "city"
                    ]
                ),

            "availability":
                safe_value(
                    row,
                    [
                        "availability",
                        "available_days"
                    ]
                ),

            "hours_required":
                safe_value(
                    row,
                    [
                        "hours_required",
                        "hours",
                        "required_hours"
                    ],
                    0
                ),

            "mode":
                safe_value(
                    row,
                    [
                        "mode",
                        "volunteering_mode"
                    ],
                    "offline"
                ),

            "experience_required":
                safe_value(
                    row,
                    [
                        "experience_required",
                        "required_experience",
                        "experience_level"
                    ],
                    "beginner"
                )
        }


        opportunity_list.append(
            opportunity
        )


    recommendations = []


    if volunteer and opportunity_list:

        try:

            raw_recommendations = (
                rank_opportunities(
                    volunteer,
                    opportunity_list,
                    top_n=5
                )
            )


            recommendations = (
                normalize_recommendations(
                    raw_recommendations,
                    opportunity_list
                )
            )


        except Exception as error:

            print(
                "Recommendation error:",
                error
            )

            recommendations = []

            for opportunity in opportunity_list[:5]:

                fallback = dict(
                    opportunity
                )

                fallback["score"] = 0

                recommendations.append(
                    fallback
                )


    return render_template(

        "volunteer_dashboard.html",

        recommendations=recommendations,

        applications=application_rows,

        applied_opportunity_ids=applied_opportunity_ids,

        profile=profile_row,

        volunteer=volunteer,

        completed_activities=completed_activities

    )


# ============================================================
# APPLY FOR OPPORTUNITY
# ============================================================

@app.route(
    "/apply/<int:opportunity_id>",
    methods=["POST"]
)
def apply_opportunity(
    opportunity_id
):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    if session.get("role") != "volunteer":

        return redirect(
            url_for("login")
        )


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
            <h2>
                Opportunity not found.
            </h2>

            <a href="/volunteer-dashboard">
                Back to Dashboard
            </a>
        """


    existing_application = connection.execute(
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


    if existing_application:

        connection.close()

        return redirect(
            url_for(
                "volunteer_dashboard"
            )
        )


    try:

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


    except sqlite3.IntegrityError:

        connection.rollback()


    connection.close()


    return redirect(
        url_for(
            "volunteer_dashboard"
        )
    )


# ============================================================
# ENSURE NGO PROFILE
# ============================================================

def get_ngo_for_user():

    connection = get_db_connection()


    ngo = connection.execute(
        """
        SELECT *

        FROM ngos

        WHERE user_id = ?

        LIMIT 1
        """,
        (
            session["user_id"],
        )
    ).fetchone()


    if ngo is None:

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


        if user:

            # Try to find NGO by email

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
                        session["user_id"],
                        ngo["ngo_id"]
                    )
                )

                connection.commit()

                ngo = connection.execute(
                    """
                    SELECT *

                    FROM ngos

                    WHERE ngo_id = ?
                    """,
                    (
                        ngo["ngo_id"],
                    )
                ).fetchone()


            else:

                # Create NGO profile automatically

                connection.execute(
                    """
                    INSERT INTO ngos
                    (
                        user_id,
                        name,
                        email,
                        cause,
                        location,
                        description
                    )

                    VALUES (?, ?, ?, '', '', '')
                    """,
                    (
                        session["user_id"],
                        user["name"],
                        user["email"]
                    )
                )

                connection.commit()


                ngo = connection.execute(
                    """
                    SELECT *

                    FROM ngos

                    WHERE user_id = ?

                    LIMIT 1
                    """,
                    (
                        session["user_id"],
                    )
                ).fetchone()


    connection.close()


    return ngo


# ============================================================
# NGO PROFILE
# ============================================================

@app.route(
    "/ngo-profile",
    methods=["GET", "POST"]
)
def ngo_profile():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    if session.get("role") != "ngo":

        return redirect(
            url_for("login")
        )


    ngo = get_ngo_for_user()


    if request.method == "POST":

        name = request.form["name"]

        email = request.form["email"]

        cause = request.form["cause"]

        location = request.form["location"]

        description = request.form["description"]


        connection = get_db_connection()


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


        connection.execute(
            """
            UPDATE users

            SET
                name = ?,
                email = ?

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
            url_for(
                "ngo_dashboard"
            )
        )


    return render_template(
        "ngo_profile.html",
        ngo=ngo
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

        return redirect(
            url_for("login")
        )


    if session.get("role") != "ngo":

        return redirect(
            url_for("login")
        )


    ngo = get_ngo_for_user()


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


        connection = get_db_connection()


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
            url_for(
                "ngo_dashboard"
            )
        )


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
def delete_opportunity(
    opportunity_id
):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    if session.get("role") != "ngo":

        return redirect(
            url_for("login")
        )


    ngo = get_ngo_for_user()


    connection = get_db_connection()


    # Delete applications first

    connection.execute(
        """
        DELETE FROM applications

        WHERE opportunity_id = ?

        AND opportunity_id IN (

            SELECT opportunity_id

            FROM opportunities

            WHERE opportunity_id = ?

            AND ngo_id = ?

        )
        """,
        (
            opportunity_id,
            opportunity_id,
            ngo["ngo_id"]
        )
    )


    # Delete opportunity

    connection.execute(
        """
        DELETE FROM opportunities

        WHERE opportunity_id = ?

        AND ngo_id = ?
        """,
        (
            opportunity_id,
            ngo["ngo_id"]
        )
    )


    connection.commit()

    connection.close()


    return redirect(
        url_for(
            "ngo_dashboard"
        )
    )


# ============================================================
# NGO DASHBOARD
# ============================================================

@app.route(
    "/ngo-dashboard"
)
def ngo_dashboard():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    if session.get("role") != "ngo":

        return redirect(
            url_for("login")
        )


    ngo = get_ngo_for_user()


    connection = get_db_connection()


    # --------------------------------------------------------
    # NGO OPPORTUNITIES
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
    # TOTAL APPLICATIONS
    # --------------------------------------------------------

    total_applications = connection.execute(
        """
        SELECT COUNT(*) AS total

        FROM applications

        JOIN opportunities

            ON applications.opportunity_id =
               opportunities.opportunity_id

        WHERE opportunities.ngo_id = ?
        """,
        (
            ngo["ngo_id"],
        )
    ).fetchone()["total"]


    # --------------------------------------------------------
    # PENDING
    # --------------------------------------------------------

    pending_applications = connection.execute(
        """
        SELECT COUNT(*) AS total

        FROM applications

        JOIN opportunities

            ON applications.opportunity_id =
               opportunities.opportunity_id

        WHERE opportunities.ngo_id = ?

        AND applications.status = 'Pending'
        """,
        (
            ngo["ngo_id"],
        )
    ).fetchone()["total"]


    # --------------------------------------------------------
    # ACCEPTED
    # --------------------------------------------------------

    accepted_applications = connection.execute(
        """
        SELECT COUNT(*) AS total

        FROM applications

        JOIN opportunities

            ON applications.opportunity_id =
               opportunities.opportunity_id

        WHERE opportunities.ngo_id = ?

        AND applications.status = 'Accepted'
        """,
        (
            ngo["ngo_id"],
        )
    ).fetchone()["total"]


    # --------------------------------------------------------
    # APPLICANTS
    # --------------------------------------------------------

    applicants = connection.execute(
        """
        SELECT

            applications.application_id,

            applications.opportunity_id,

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

            opportunities.title AS opportunity_title,

            opportunities.cause

        FROM applications

        JOIN users

            ON applications.user_id =
               users.user_id

        LEFT JOIN volunteer_profiles

            ON users.user_id =
               volunteer_profiles.user_id

        JOIN opportunities

            ON applications.opportunity_id =
               opportunities.opportunity_id

        WHERE opportunities.ngo_id = ?

        ORDER BY applications.applied_at DESC
        """,
        (
            ngo["ngo_id"],
        )
    ).fetchall()


    connection.close()


    return render_template(

        "ngo_dashboard.html",

        ngo=ngo,

        opportunities=opportunities,

        applicants=applicants,

        total_applications=total_applications,

        pending_applications=pending_applications,

        accepted_applications=accepted_applications

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

        return redirect(
            url_for("login")
        )


    if session.get("role") != "ngo":

        return redirect(
            url_for("login")
        )


    allowed_statuses = [
        "Accepted",
        "Rejected",
        "Pending",
        "Completed"
    ]


    if new_status not in allowed_statuses:

        return redirect(
            url_for(
                "ngo_dashboard"
            )
        )


    ngo = get_ngo_for_user()


    connection = get_db_connection()


    application = connection.execute(
        """
        SELECT

            applications.application_id

        FROM applications

        JOIN opportunities

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


    if application:

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
        url_for(
            "ngo_dashboard"
        )
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route(
    "/logout"
)
def logout():

    session.clear()

    return redirect(
        url_for("home")
    )


# ============================================================
# START APPLICATION
# ============================================================

if __name__ == "__main__":

    init_database()

    load_csv_data()

    app.run(
        debug=True,
        use_reloader=False
    )