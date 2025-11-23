# validator.py
import re
from datetime import datetime
import sys
import os
sys.path.append(os.path.dirname(__file__))

def validate_user_id(user_id):
    return user_id.isdigit() and int(user_id) > 0

def validate_rating(rating):
    try:
        r = int(rating)
        return 1 <= r <= 5
    except:
        return False

def validate_timestamp(ts):
    try:
        datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
        return True
    except:
        return False

def validate_file_extension(ext):
    return ext.lower() in {"jpg", "jpeg", "png", "gif"}

def validate_username(username):
    return username and len(username.strip()) >= 3

def validate_email(email):
    # Make email optional
    if not email or len(email.strip()) == 0:
        return "VALID"  # Email is optional
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return "VALID" if re.match(pattern, email) else "ERROR|Invalid email"

def validate_password(password):
    return password and len(password) >= 6

def validate_name(name, field_name):
    if not name or len(name.strip()) == 0:
        return f"ERROR|{field_name} cannot be empty"
    return "VALID"

def validate_file_path(path):
    return path and len(path.strip()) > 0

def validate_boolean_flag(flag, field_name):
    if flag.lower() in ("true", "false", "0", "1"):
        return "VALID"
    return f"ERROR|Invalid {field_name}"

def validate_phone(phone):
    # Make phone optional - if provided, validate format
    if not phone or len(phone.strip()) == 0:
        return "VALID"  # Phone is optional
    if re.match(r'^\+?[\d\s\-\(\)]{10,}$', phone):
        return "VALID"
    return "ERROR|Invalid phone number"

def validate_area(area):
    return area and len(area.strip()) > 0

def validate_vehicle_info(model, color, license_plate):
    if not model or len(model.strip()) == 0:
        return "ERROR|Car model required"
    if not color or len(color.strip()) == 0:
        return "ERROR|Car color required"
    if not license_plate or len(license_plate.strip()) == 0:
        return "ERROR|License plate required"
    return "VALID"

def validate_ride_locations(start, end):
    if not start or len(start.strip()) == 0:
        return "ERROR|Start location required"
    if not end or len(end.strip()) == 0:
        return "ERROR|End location required"
    return "VALID"

def validate_coordinate(coord, coord_type):
    try:
        value = float(coord)
        if coord_type == "latitude":
            return -90 <= value <= 90
        else:  # longitude
            return -180 <= value <= 180
    except:
        return False