import json

import sys
import os
sys.path.append(os.path.dirname(__file__))
import validator

def handle_driver_schedule_save(data, conn):
    try:
        # Split message into command, user_id, and JSON schedule
        _, user_id, schedule_json = data.split("|", 2)

        # Validate user_id
        if not validator.validate_user_id(user_id):
            return "ERROR|Invalid user ID"

        # Parse schedule JSON
        try:
            schedule = json.loads(schedule_json)
        except json.JSONDecodeError:
            return "ERROR|Invalid schedule format"

        cursor = conn.cursor()

        # Clear old schedule for this driver
        cursor.execute("DELETE from driver_schedules WHERE user_id=?", (user_id,))

        # Insert each day's schedule
        for day, info in schedule.items():
            enabled = info.get("enabled", False)
            start_time = info.get("start_time", None)
            end_time = info.get("end_time", None)

            # Optional: validate time format if needed
            cursor.execute("""
                INSERT INTO driver_schedules (user_id, day, enabled, start_time, end_time)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, day, enabled, start_time, end_time))

        conn.commit()
        return "SUCCESS|Schedule saved"

    except Exception as e:
        return f"ERROR|Schedule save failed: {str(e)}"
    
    
def handle_driver_car_info_save(data, conn):
    try:
        parts = data.split("|")
        if len(parts) != 5:
            return "ERROR|Invalid message format"

        _, user_id, car_model, car_color, license_plate = parts

        # Validate user_id
        if not validator.validate_user_id(user_id):
            return "ERROR|Invalid user ID"

        # Validate car info
        car_check = validator.validate_vehicle_info(car_model, car_color, license_plate)
        if car_check != "VALID":
            return car_check

        cursor = conn.cursor()
        cursor.execute("SELECT * from driver_cars WHERE user_id=?", (user_id,))
        result = cursor.fetchone()

        if result:
            cursor.execute("""
                UPDATE driver_cars
                SET car_model=?, car_color=?, license_plate=?
                WHERE user_id=?
            """, (car_model, car_color, license_plate, user_id))
        else:
            cursor.execute("""
                INSERT INTO driver_cars (user_id, car_model, car_color, license_plate)
                VALUES (?, ?, ?, ?)
            """, (user_id, car_model, car_color, license_plate))

        conn.commit()
        return "SUCCESS|Car info saved"

    except Exception as e:
        return f"ERROR|Car info save failed: {str(e)}"

    except Exception as e:
        return f"ERROR|Car info save failed: {str(e)}"

    
def handle_driver_route_save(data, conn):
    try:
        # Split message into command, user_id, start, end
        _, user_id, start_location, end_location = data.split("|")

        # Validate user_id
        if not validator.validate_user_id(user_id):
            return "ERROR|Invalid user ID"

        # Validate locations
        location_check = validator.validate_ride_locations(start_location, end_location)
        if location_check != "VALID":
            return location_check

        cursor = conn.cursor()
        cursor.execute("SELECT * from driver_routes WHERE user_id=?", (user_id,))
        result = cursor.fetchone()

        if result:
            cursor.execute("""
                UPDATE driver_routes
                SET start_location=?, end_location=?
                WHERE user_id=?
            """, (start_location, end_location, user_id))
        else:
            cursor.execute("""
                INSERT INTO driver_routes (user_id, start_location, end_location)
                VALUES (?, ?, ?)
            """, (user_id, start_location, end_location))

        conn.commit()
        return "SUCCESS|Route saved"

    except Exception as e:
        return f"ERROR|Route save failed: {str(e)}"

def handle_driver_online(data, conn):
    try:
        parts = data.split("|")
        if len(parts) < 2:
            return "ERROR|Invalid format"

        user_id = parts[1]
        latitude = parts[2] if len(parts) > 2 else None
        longitude = parts[3] if len(parts) > 3 else None

        # Validate user_id
        if not validator.validate_user_id(user_id):
            return "ERROR|Invalid user ID"

        # Validate coordinates if provided
        if latitude and not validator.validate_coordinate(latitude, "latitude"):
            return "ERROR|Invalid latitude"
        if longitude and not validator.validate_coordinate(longitude, "longitude"):
            return "ERROR|Invalid longitude"

        cursor = conn.cursor()
        cursor.execute("SELECT * from driver_status WHERE user_id=?", (user_id,))
        result = cursor.fetchone()

        if result:
            cursor.execute("""
                UPDATE driver_status
                SET is_online=?, latitude=?, longitude=?
                WHERE user_id=?
            """, (True, latitude, longitude, user_id))
        else:
            cursor.execute("""
                INSERT INTO driver_status (user_id, is_online, latitude, longitude)
                VALUES (?, ?, ?, ?)
            """, (user_id, True, latitude, longitude))

        conn.commit()
        return "SUCCESS|Driver online"

    except Exception as e:
        return f"ERROR|Driver online failed: {str(e)}"

def handle_driver_offline(data, conn):
    try:
        parts = data.split("|")
        if len(parts) < 2:
            return "ERROR|Invalid format"

        _, user_id = parts

        # Validate user_id
        if not validator.validate_user_id(user_id):
            return "ERROR|Invalid user ID"

        cursor = conn.cursor()
        cursor.execute("""
            UPDATE driver_status
            SET is_online=?, latitude=NULL, longitude=NULL
            WHERE user_id=?
        """, (False, user_id))

        conn.commit()
        return "SUCCESS|Driver offline"

    except Exception as e:
        return f"ERROR|Driver offline failed: {str(e)}"
    
def handle_driver_schedule_get(data, conn):
    """Get driver schedule"""
    try:
        _, user_id = data.split("|")
        
        if not validator.validate_user_id(user_id):
            return "ERROR|Invalid user ID"
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT day, enabled, start_time, end_time
            FROM driver_schedules
            WHERE user_id=?
        """, (user_id,))
        results = cursor.fetchall()
        
        if not results:
            return "SUCCESS|No schedule found"
        
        schedule_str = ";".join([f"{day}|{enabled}|{start}|{end}" for day, enabled, start, end in results])
        return f"SUCCESS|{schedule_str}"
        
    except Exception as e:
        return f"ERROR|Schedule get failed: {str(e)}"


def handle_driver_route_get(data, conn):
    """Get driver route"""
    try:
        _, user_id = data.split("|")
        
        if not validator.validate_user_id(user_id):
            return "ERROR|Invalid user ID"
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT start_location, end_location
            FROM driver_routes
            WHERE user_id=?
        """, (user_id,))
        result = cursor.fetchone()
        
        if not result:
            return "SUCCESS||"
        
        return f"SUCCESS|{result[0]}|{result[1]}"
        
    except Exception as e:
        return f"ERROR|Route get failed: {str(e)}"


def handle_driver_car_get(data, conn):
    """Get driver car info"""
    try:
        _, user_id = data.split("|")
        
        if not validator.validate_user_id(user_id):
            return "ERROR|Invalid user ID"
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT car_model, car_color, license_plate
            FROM driver_cars
            WHERE user_id=?
        """, (user_id,))
        result = cursor.fetchone()
        
        if not result:
            return "SUCCESS|||"
        
        return f"SUCCESS|{result[0]}|{result[1]}|{result[2]}"
        
    except Exception as e:
        return f"ERROR|Car info get failed: {str(e)}"

