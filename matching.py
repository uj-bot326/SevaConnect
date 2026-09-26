# ============================================================
# SEVACONNECT - VOLUNTEER MATCHING ENGINE
# ============================================================

import re


# ============================================================
# TEXT / LIST HELPERS
# ============================================================

def make_list(value):
    """
    Convert comma-separated or semicolon-separated text
    into a clean lowercase list.
    """

    if value is None:
        return []

    text = str(value).strip().lower()

    if not text:
        return []

    text = text.replace(";", ",")

    return [
        item.strip()
        for item in text.split(",")
        if item.strip()
    ]


def normalize_text(value):
    """
    Clean text for comparison.
    """

    if value is None:
        return ""

    text = str(value).lower().strip()

    text = re.sub(r"\s+", " ", text)

    return text


# ============================================================
# SKILL MATCHING
# ============================================================

def skill_match(volunteer_skills, required_skills):
    """
    Calculates how many required skills are covered
    by the volunteer.

    Example:
    Volunteer:
        Python, Communication, Photography

    Opportunity:
        Python, Communication

    Result:
        1.0 = 100%
    """

    volunteer_skills = set(
        normalize_text(skill)
        for skill in volunteer_skills
    )

    required_skills = set(
        normalize_text(skill)
        for skill in required_skills
    )

    required_skills.discard("")

    if not required_skills:
        return 0

    matched_skills = volunteer_skills.intersection(
        required_skills
    )

    return len(matched_skills) / len(required_skills)


# ============================================================
# INTEREST MATCHING
# ============================================================

def interest_match(volunteer_interests, opportunity_cause):
    """
    Checks whether the opportunity's cause matches
    one of the volunteer's interests.
    """

    volunteer_interests = set(
        normalize_text(interest)
        for interest in volunteer_interests
    )

    opportunity_cause = normalize_text(
        opportunity_cause
    )

    if not opportunity_cause:
        return 0

    return 1 if opportunity_cause in volunteer_interests else 0


# ============================================================
# LOCATION MATCHING
# ============================================================

def location_match(volunteer_location, opportunity_location):
    """
    Exact location matching for the initial prototype.

    Remote opportunities are treated as compatible.
    """

    volunteer_location = normalize_text(
        volunteer_location
    )

    opportunity_location = normalize_text(
        opportunity_location
    )

    if not volunteer_location or not opportunity_location:
        return 0

    if opportunity_location == "remote":
        return 1

    if volunteer_location == "remote":
        return 1

    return 1 if volunteer_location == opportunity_location else 0


# ============================================================
# AVAILABILITY MATCHING
# ============================================================

def availability_match(
    volunteer_availability,
    opportunity_availability
):
    """
    Calculates the percentage of opportunity availability
    covered by the volunteer.
    """

    volunteer_availability = set(
        normalize_text(day)
        for day in volunteer_availability
    )

    opportunity_availability = set(
        normalize_text(day)
        for day in opportunity_availability
    )

    volunteer_availability.discard("")
    opportunity_availability.discard("")

    if not opportunity_availability:
        return 0

    matched_days = volunteer_availability.intersection(
        opportunity_availability
    )

    return len(matched_days) / len(opportunity_availability)


# ============================================================
# EXPERIENCE MATCHING
# ============================================================

def experience_match(
    volunteer_experience,
    required_experience
):
    """
    Checks whether the volunteer has enough experience
    for the opportunity.
    """

    levels = {
        "beginner": 1,
        "intermediate": 2,
        "advanced": 3
    }

    volunteer_experience = normalize_text(
        volunteer_experience
    )

    required_experience = normalize_text(
        required_experience
    )

    volunteer_level = levels.get(
        volunteer_experience,
        0
    )

    required_level = levels.get(
        required_experience,
        0
    )

    if volunteer_level >= required_level:
        return 1

    return 0


# ============================================================
# MODE MATCHING
# ============================================================

def mode_match(
    volunteer_mode,
    opportunity_mode
):
    """
    Checks compatibility between volunteer preference
    and opportunity mode.
    """

    volunteer_mode = normalize_text(
        volunteer_mode
    )

    opportunity_mode = normalize_text(
        opportunity_mode
    )

    if not volunteer_mode or not opportunity_mode:
        return 0

    # Exact match
    if volunteer_mode == opportunity_mode:
        return 1

    # Hybrid is compatible with either preference
    if volunteer_mode == "hybrid":
        return 1

    if opportunity_mode == "hybrid":
        return 1

    return 0


# ============================================================
# COMPLETE MATCH SCORE
# ============================================================

def calculate_score(volunteer, opportunity):
    """
    Calculate the overall SevaConnect match score.

    Current prototype weights:

    Skills       = 35%
    Interests    = 15%
    Availability = 20%
    Location     = 10%
    Experience   = 10%
    Mode         = 10%
    """

    volunteer_skills = make_list(
        volunteer.get("skills", "")
    )

    required_skills = make_list(
        opportunity.get("required_skills", "")
    )

    volunteer_interests = make_list(
        volunteer.get("interests", "")
    )

    volunteer_availability = make_list(
        volunteer.get("availability", "")
    )

    opportunity_availability = make_list(
        opportunity.get("availability", "")
    )

    skill_score = skill_match(
        volunteer_skills,
        required_skills
    )

    interest_score = interest_match(
        volunteer_interests,
        opportunity.get("cause", "")
    )

    availability_score = availability_match(
        volunteer_availability,
        opportunity_availability
    )

    location_score = location_match(
        volunteer.get("location", ""),
        opportunity.get("location", "")
    )

    experience_score = experience_match(
        volunteer.get("experience", ""),
        opportunity.get("experience_required", "")
    )

    mode_score = mode_match(
        volunteer.get("preferred_mode", ""),
        opportunity.get("mode", "")
    )

    final_score = (
        0.35 * skill_score +
        0.15 * interest_score +
        0.20 * availability_score +
        0.10 * location_score +
        0.10 * experience_score +
        0.10 * mode_score
    )

    return round(final_score * 100, 2)


# ============================================================
# SCORE BREAKDOWN
# ============================================================

def get_score_breakdown(volunteer, opportunity):
    """
    Returns individual matching factors and final score.
    Useful for explainable recommendations.
    """

    volunteer_skills = make_list(
        volunteer.get("skills", "")
    )

    required_skills = make_list(
        opportunity.get("required_skills", "")
    )

    volunteer_interests = make_list(
        volunteer.get("interests", "")
    )

    volunteer_availability = make_list(
        volunteer.get("availability", "")
    )

    opportunity_availability = make_list(
        opportunity.get("availability", "")
    )

    skill_score = skill_match(
        volunteer_skills,
        required_skills
    )

    interest_score = interest_match(
        volunteer_interests,
        opportunity.get("cause", "")
    )

    availability_score = availability_match(
        volunteer_availability,
        opportunity_availability
    )

    location_score = location_match(
        volunteer.get("location", ""),
        opportunity.get("location", "")
    )

    experience_score = experience_match(
        volunteer.get("experience", ""),
        opportunity.get("experience_required", "")
    )

    mode_score = mode_match(
        volunteer.get("preferred_mode", ""),
        opportunity.get("mode", "")
    )

    final_score = (
        0.35 * skill_score +
        0.15 * interest_score +
        0.20 * availability_score +
        0.10 * location_score +
        0.10 * experience_score +
        0.10 * mode_score
    )

    return {
        "skills": round(skill_score * 100, 2),
        "interests": round(interest_score * 100, 2),
        "availability": round(availability_score * 100, 2),
        "location": round(location_score * 100, 2),
        "experience": round(experience_score * 100, 2),
        "mode": round(mode_score * 100, 2),
        "final_score": round(final_score * 100, 2)
    }


# ============================================================
# EXPLAINABLE RECOMMENDATIONS
# ============================================================

def get_recommendation_reasons(
    volunteer,
    opportunity
):
    """
    Generates human-readable explanations for
    why an opportunity was recommended.
    """

    reasons = []
    warnings = []

    volunteer_skills = make_list(
        volunteer.get("skills", "")
    )

    required_skills = make_list(
        opportunity.get("required_skills", "")
    )

    volunteer_interests = make_list(
        volunteer.get("interests", "")
    )

    opportunity_cause = normalize_text(
        opportunity.get("cause", "")
    )

    # -------------------------
    # Skills
    # -------------------------

    matched_skills = set(volunteer_skills).intersection(
        set(required_skills)
    )

    if matched_skills:

        reasons.append(
            "Your skills match the required skills."
        )

    else:

        warnings.append(
            "Your skills do not directly match "
            "the required skills."
        )

    # -------------------------
    # Interests
    # -------------------------

    if opportunity_cause in volunteer_interests:

        reasons.append(
            "The opportunity matches your interests."
        )

    else:

        warnings.append(
            "The opportunity cause does not match "
            "your listed interests."
        )

    # -------------------------
    # Availability
    # -------------------------

    availability_score = availability_match(
        make_list(volunteer.get("availability", "")),
        make_list(opportunity.get("availability", ""))
    )

    if availability_score > 0:

        reasons.append(
            "Your availability overlaps with "
            "the opportunity schedule."
        )

    else:

        warnings.append(
            "Your availability does not overlap "
            "with the opportunity schedule."
        )

    # -------------------------
    # Location
    # -------------------------

    location_score = location_match(
        volunteer.get("location", ""),
        opportunity.get("location", "")
    )

    if location_score == 1:

        reasons.append(
            "The location is compatible with your profile."
        )

    else:

        warnings.append(
            "The opportunity location differs "
            "from your location."
        )

    # -------------------------
    # Experience
    # -------------------------

    experience_score = experience_match(
        volunteer.get("experience", ""),
        opportunity.get("experience_required", "")
    )

    if experience_score == 1:

        reasons.append(
            "Your experience level satisfies "
            "the opportunity requirement."
        )

    else:

        warnings.append(
            "The opportunity requires more experience."
        )

    # -------------------------
    # Mode
    # -------------------------

    mode_score = mode_match(
        volunteer.get("preferred_mode", ""),
        opportunity.get("mode", "")
    )

    if mode_score == 1:

        reasons.append(
            "The volunteering mode matches your preference."
        )

    else:

        warnings.append(
            "The volunteering mode differs "
            "from your preference."
        )

    return reasons, warnings


# ============================================================
# RANK OPPORTUNITIES
# ============================================================

def rank_opportunities(
    volunteer,
    opportunities,
    top_n=5
):
    """
    Calculate scores for all opportunities and return
    the highest-ranked opportunities.
    """

    ranked = []

    for opportunity in opportunities:

        score = calculate_score(
            volunteer,
            opportunity
        )

        ranked.append({
            "opportunity": opportunity,
            "score": score
        })

    ranked.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    return ranked[:top_n]