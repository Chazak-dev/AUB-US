import base64
import os
import sys
import re

sys.path.append(os.path.dirname(__file__))
import validator

def handle_profile_create(data, conn):
    try:
        # Split message into expected fields
        parts = data.split("|")
        if len(parts) != 8:
            return "ERROR|Invalid profile format"

        _, user_id, first_name, last_name, phone, area, is_driver, photo_path = parts

        # Validate user_id
        if not validator.validate_user_id(user_id):
            return "ERROR|Invalid user ID"

        # Validate names
        first_check = validator.validate_name(first_name, "First name")
        if first_check != "VALID":
            return first_check

        last_check = validator.validate_name(last_name, "Last name")
        if last_check != "VALID":
            return last_check
        
        # Validate driver flag
        flag_check = validator.validate_boolean_flag(is_driver, "Driver flag")
        if flag_check != "VALID":
            return flag_check

        # Validate photo path
        if not validator.validate_file_path(photo_path):
            return "ERROR|Invalid photo path"

        cursor = conn.cursor()
        cursor.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()

        if result is not None:
            return "ERROR|Profile already exists"

        # Insert with optional fields
        cursor.execute("""
            INSERT INTO profiles (user_id, first_name, last_name, phone, area, is_driver, profile_photo_path)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, first_name, last_name, phone, area, is_driver, photo_path))
        conn.commit()

        return "SUCCESS|Profile created"

    except Exception as e:
        return f"ERROR|Profile creation failed: {str(e)}"

def handle_profile_update(data, conn):
    """
    Update a user's profile information.
    Format: PROFILE_UPDATE|user_id|first_name|last_name|email|phone|area|is_driver|photo_path
    
    FIXED: Properly handles validator functions that return True instead of "VALID"
    """
    try:
        parts = data.split("|")
        if len(parts) != 9:
            return "ERROR|Invalid update format"

        _, user_id, first_name, last_name, email, phone, area, is_driver, photo_path = parts

        # Validate user_id
        if not validator.validate_user_id(user_id):
            return "ERROR|Invalid user ID"

        cursor = conn.cursor()
        cursor.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        if result is None:
            return "ERROR|Profile not found"

        # First name - FIXED validation check
        if first_name:
            check = validator.validate_name(first_name, "First name")
            # Accept both "VALID" string and True boolean
            if check not in ["VALID", True]:
                return check if isinstance(check, str) else "ERROR|Invalid first name"
            cursor.execute("UPDATE profiles SET first_name=? WHERE user_id=?", (first_name, user_id))
            cursor.execute("UPDATE users SET first_name=? WHERE id=?", (first_name, user_id))

        # Last name - FIXED validation check
        if last_name:
            check = validator.validate_name(last_name, "Last name")
            if check not in ["VALID", True]:
                return check if isinstance(check, str) else "ERROR|Invalid last name"
            cursor.execute("UPDATE profiles SET last_name=? WHERE user_id=?", (last_name, user_id))
            cursor.execute("UPDATE users SET last_name=? WHERE id=?", (last_name, user_id))

        # Email - FIXED validation check
        if email:
            check = validator.validate_email(email)
            if check not in ["VALID", True]:
                return check if isinstance(check, str) else "ERROR|Invalid email"
            cursor.execute("UPDATE users SET email=? WHERE id=?", (email, user_id))

        # Phone - FIXED validation check
        if phone:
            check = validator.validate_phone(phone)
            if check not in ["VALID", True]:
                return check if isinstance(check, str) else "ERROR|Invalid phone"
            cursor.execute("UPDATE profiles SET phone=? WHERE user_id=?", (phone, user_id))

        # Area - FIXED validation check
        if area:
            check = validator.validate_area(area)
            if check not in ["VALID", True]:
                return check if isinstance(check, str) else "ERROR|Invalid area"
            cursor.execute("UPDATE profiles SET area=? WHERE user_id=?", (area, user_id))
            cursor.execute("UPDATE users SET address=? WHERE id=?", (area, user_id))

        # Driver flag - FIXED validation check
        if is_driver != "":
            check = validator.validate_boolean_flag(is_driver, "Driver flag")
            if check not in ["VALID", True]:
                return check if isinstance(check, str) else "ERROR|Invalid driver flag"
            cursor.execute("UPDATE profiles SET is_driver=? WHERE user_id=?", (is_driver, user_id))
            cursor.execute("UPDATE users SET is_driver=? WHERE id=?", (is_driver, user_id))

        # Photo path - FIXED validation check
        if photo_path:
            check = validator.validate_file_path(photo_path)
            # validate_file_path might return True/False or "VALID"
            if check is False or (isinstance(check, str) and check not in ["VALID"]):
                return check if isinstance(check, str) else "ERROR|Invalid photo path"
            cursor.execute("UPDATE profiles SET profile_photo_path=? WHERE user_id=?", (photo_path, user_id))

        # Commit all updates
        conn.commit()

        # Return detailed success response
        return f"SUCCESS|Profile updated|{user_id}|{first_name}|{last_name}|{email}|{phone}|{area}|{is_driver}|{photo_path}"

    except Exception as e:
        conn.rollback()
        return f"ERROR|Profile update failed: {str(e)}"


def handle_profile_get(data, conn):
    try:
        parts = data.split("|")
        if len(parts) != 2:
            return "ERROR|Invalid request format"

        _, user_id = parts

        # Validate user_id
        if not validator.validate_user_id(user_id):
            return "ERROR|Invalid user ID"

        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.first_name, p.last_name, p.phone, p.area, p.is_driver, p.profile_photo_path, u.email
            FROM profiles p
            LEFT JOIN users u ON p.user_id = u.id
            WHERE p.user_id = ?
        """, (user_id,))
        result = cursor.fetchone()

        if result is None:
            return "ERROR|Profile not found"
        
        first_name, last_name, phone, area, is_driver, photo_path, email = result
        return f"SUCCESS|{first_name}|{last_name}|{email or ''}|{phone or ''}|{area or ''}|{is_driver}|{photo_path or ''}"

        
    except Exception as e:
        return f"ERROR|Profile retrieval failed: {str(e)}"
    
def handle_profile_photo_upload(data, conn):
    try:
        parts = data.split("|")
        if len(parts) != 4:
            return "ERROR|Invalid photo upload format"

        _, user_id, photo_data, file_extension = parts

        # Validate user_id
        if not validator.validate_user_id(user_id):
            return "ERROR|Invalid user ID"

        # Validate file extension
        if not validator.validate_file_extension(file_extension):
            return "ERROR|Unsupported file extension"

        cursor = conn.cursor()
        cursor.execute("SELECT * FROM profiles WHERE user_id=?", (user_id,))
        result = cursor.fetchone()

        if result is None:
            return "ERROR|Profile not found"

        # Decode base64 photo data
        try:
            image_bytes = base64.b64decode(photo_data)
        except Exception:
            return "ERROR|Invalid photo data"

        # Ensure photos directory exists
        photos_dir = "photos"
        if not os.path.exists(photos_dir):
            os.makedirs(photos_dir)

        # Build file path
        file_path = os.path.join(photos_dir, f"user_{user_id}.{file_extension}")

        # Save image to disk
        with open(file_path, "wb") as f:
            f.write(image_bytes)

        # Update profile record with photo path
        cursor.execute(
            "UPDATE profiles SET profile_photo_path=? WHERE user_id=?",
            (file_path, user_id)
        )
        conn.commit()

        return "SUCCESS|Photo uploaded"

    except Exception as e:
        return f"ERROR|Photo upload failed: {str(e)}"