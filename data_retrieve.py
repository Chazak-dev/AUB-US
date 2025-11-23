import sys
import os
sys.path.append(os.path.dirname(__file__))
import validator

# These are read‑only queries, so they won’t modify the database,
# just fetch information for the client.

def handle_ride_history_get(message, conn):
    """
    Fetch ride history for a user.
    Expected format:
      RIDE_HISTORY_GET|user_id|limit|offset|start_date|end_date
    - user_id: positive integer
    - limit: optional, default 20
    - offset: optional, default 0
    - start_date/end_date: optional, YYYY-MM-DD HH:MM:SS
    """
    try:
        parts = message.split("|")
        if len(parts) < 2:
            return "RIDE_HISTORY_GET|ERROR|Invalid format"

        user_id = parts[1]
        limit = int(parts[2]) if len(parts) > 2 and parts[2] else 20
        offset = int(parts[3]) if len(parts) > 3 and parts[3] else 0
        start_date = parts[4] if len(parts) > 4 and parts[4] else None
        end_date = parts[5] if len(parts) > 5 and parts[5] else None

        # Validate user_id
        if not validator.validate_user_id(user_id):
            return "RIDE_HISTORY_GET|ERROR|Invalid user_id"

        # Validate pagination
        if limit <= 0 or offset < 0:
            return "RIDE_HISTORY_GET|ERROR|Invalid limit/offset"

        # Validate optional dates
        if start_date and not validator.validate_timestamp(start_date):
            return "RIDE_HISTORY_GET|ERROR|Invalid start_date"
        if end_date and not validator.validate_timestamp(end_date):
            return "RIDE_HISTORY_GET|ERROR|Invalid end_date"

        cur = conn.cursor()

        # Build base query: rides where user is driver OR passenger
        query = """
            SELECT * from rides
            WHERE (driver_id = ? OR passenger_id = ?)
        """
        params = [user_id, user_id]

        # Add optional time range filters
        if start_date:
            query += " AND start_time >= ?"
            params.append(start_date)
        if end_date:
            query += " AND end_time <= ?"
            params.append(end_date)

        # Add ordering, limit, and offset
        query += " ORDER BY start_time DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cur.execute(query, params)
        rows = cur.fetchall()

        return f"RIDE_HISTORY_GET|SUCCESS|{rows}"
    except Exception as e:
        return f"RIDE_HISTORY_GET|ERROR|{str(e)}"


def handle_driver_stats_get(message, conn):
    """
    Fetch driver statistics.
    Expected format:
      DRIVER_STATS_GET|driver_id|time_period
    - driver_id: positive integer
    - time_period: 'day', 'week', 'month', or 'all'
    """
    try:
        parts = message.split("|")
        if len(parts) != 3:
            return "DRIVER_STATS_GET|ERROR|Invalid format"

        _, driver_id, time_period = parts

        # Validate driver_id
        if not validator.validate_user_id(driver_id):
            return "DRIVER_STATS_GET|ERROR|Invalid driver_id"

        # Validate time_period
        if time_period not in ("day", "week", "month", "all"):
            return "DRIVER_STATS_GET|ERROR|Invalid time_period"

        cur = conn.cursor()

        # Build time filter based on period
        time_filter = ""
        if time_period == "day":
            time_filter = "AND start_time >= datetime('now', '-1 day')"
        elif time_period == "week":
            time_filter = "AND start_time >= datetime('now', '-7 days')"
        elif time_period == "month":
            time_filter = "AND start_time >= datetime('now', '-1 month')"
        # "all" means no filter

        query = f"""
            SELECT COUNT(*) as total_rides,
                   AVG(fare) as avg_fare,
                   SUM(fare) as total_earnings
            from rides
            WHERE driver_id = ? {time_filter}
        """
        cur.execute(query, (driver_id,))
        stats = cur.fetchone()

        return f"DRIVER_STATS_GET|SUCCESS|{stats}"
    except Exception as e:
        return f"DRIVER_STATS_GET|ERROR|{str(e)}"


def handle_passenger_stats_get(message, conn):
    """
    Fetch passenger statistics.
    Expected format:
      PASSENGER_STATS_GET|passenger_id
    - passenger_id: positive integer
    """
    try:
        parts = message.split("|")
        if len(parts) != 2:
            return "PASSENGER_STATS_GET|ERROR|Invalid format"

        _, passenger_id = parts

        # Validate passenger_id
        if not validator.validate_user_id(passenger_id):
            return "PASSENGER_STATS_GET|ERROR|Invalid passenger_id"

        cur = conn.cursor()
        query = """
            SELECT COUNT(*) as total_rides,
                   AVG(fare) as avg_fare,
                   SUM(fare) as total_spent
            from rides
            WHERE passenger_id = ?
        """
        cur.execute(query, (passenger_id,))
        stats = cur.fetchone()

        return f"PASSENGER_STATS_GET|SUCCESS|{stats}"
    except Exception as e:
        return f"PASSENGER_STATS_GET|ERROR|{str(e)}"


def handle_active_rides_get(message, conn):
    """
    Fetch active rides for a user.
    Expected format:
      ACTIVE_RIDES_GET|user_id
    - user_id: positive integer
    """
    try:
        parts = message.split("|")
        if len(parts) != 2:
            return "ACTIVE_RIDES_GET|ERROR|Invalid format"

        _, user_id = parts

        # Validate user_id
        if not validator.validate_user_id(user_id):
            return "ACTIVE_RIDES_GET|ERROR|Invalid user_id"

        cur = conn.cursor()
        query = """
            SELECT * from rides
            WHERE (driver_id = ? OR passenger_id = ?)
            AND status = 'active'
        """
        cur.execute(query, (user_id, user_id))
        rows = cur.fetchall()

        return f"ACTIVE_RIDES_GET|SUCCESS|{rows}"
    except Exception as e:
        return f"ACTIVE_RIDES_GET|ERROR|{str(e)}"
