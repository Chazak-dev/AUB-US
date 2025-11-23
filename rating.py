import sys
import os
sys.path.append(os.path.dirname(__file__))
import validator

def handle_rating_submit(data, conn):
    """
    Handle RATING_SUBMIT command.
    Format: RATING_SUBMIT|request_id|rater_id|target_id|target_role|rating|comment
    - target_role: 'driver' or 'passenger'
    """
    try:
        parts = data.split("|")
        if len(parts) < 6:
            return "ERROR|Invalid message format"

        _, request_id, rater_id, target_id, target_role, rating = parts[:6]
        comment = parts[6] if len(parts) > 6 else None

        # Validate IDs
        if not validator.validate_user_id(request_id):
            return "ERROR|Invalid request_id"
        if not validator.validate_user_id(rater_id):
            return "ERROR|Invalid rater_id"
        if not validator.validate_user_id(target_id):
            return "ERROR|Invalid target_id"

        # Validate role
        if target_role not in ("driver", "passenger"):
            return "ERROR|Invalid target_role"

        # Validate rating
        if not validator.validate_rating(rating):
            return "ERROR|Invalid rating value"

        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO ride_ratings (request_id, rater_id, target_id, target_role, rating, comment)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (request_id, rater_id, target_id, target_role, int(rating), comment))

        conn.commit()
        return f"SUCCESS|Rating submitted for {target_role} {target_id}"
    except Exception as e:
        return f"ERROR|Rating submit failed: {str(e)}"

def handle_rating_get(data, conn):
    """
    Handle RATING_GET command.
    Format: RATING_GET|target_id|target_role
    Returns average rating and count for the target.
    """
    try:
        parts = data.split("|")
        if len(parts) != 3:
            return "ERROR|Invalid message format"

        _, target_id, target_role = parts

        # Validate inputs
        if not validator.validate_user_id(target_id):
            return "ERROR|Invalid target_id"
        if target_role not in ("driver", "passenger"):
            return "ERROR|Invalid target_role"

        cursor = conn.cursor()
        cursor.execute("""
            SELECT AVG(rating), COUNT(*)
            from .ride_ratings
            WHERE target_id=? AND target_role=?
        """, (target_id, target_role))
        result = cursor.fetchone()

        if result is None or result[1] == 0:
            return f"SUCCESS|{target_role.capitalize()} {target_id} has no ratings"

        avg_rating, count = result
        return f"SUCCESS|{target_role.capitalize()} {target_id}|Average={avg_rating:.2f}|Count={count}"
    except Exception as e:
        return f"ERROR|Rating get failed: {str(e)}"

def handle_rating_history_get(data, conn):
    """
    Handle RATING_HISTORY_GET command.
    Format: RATING_HISTORY_GET|target_id|target_role|limit|offset
    Returns paginated rating history for the target.
    """
    try:
        parts = data.split("|")
        if len(parts) < 3:
            return "ERROR|Invalid message format"

        _, target_id, target_role = parts[:3]
        limit = int(parts[3]) if len(parts) > 3 and parts[3] else 10
        offset = int(parts[4]) if len(parts) > 4 and parts[4] else 0

        # Validate inputs
        if not validator.validate_user_id(target_id):
            return "ERROR|Invalid target_id"
        if target_role not in ("driver", "passenger"):
            return "ERROR|Invalid target_role"
        if limit <= 0 or offset < 0:
            return "ERROR|Invalid pagination values"

        cursor = conn.cursor()
        cursor.execute("""
            SELECT request_id, rater_id, rating, comment, timestamp
            from .ride_ratings
            WHERE target_id=? AND target_role=?
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        """, (target_id, target_role, limit, offset))
        results = cursor.fetchall()

        if not results:
            return f"SUCCESS|{target_role.capitalize()} {target_id} has no rating history"

        history = ";".join([
            f"{req}|Rater={rid}|{rate}|{comment}|{ts}"
            for req, rid, rate, comment, ts in results
        ])
        return f"SUCCESS|{target_role.capitalize()} {target_id}|{history}"
    except Exception as e:
        return f"ERROR|Rating history get failed: {str(e)}"
