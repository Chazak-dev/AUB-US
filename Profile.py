import base64
import os
import sys

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

    except Exception as e:
        return f"ERROR|Profile creation failed: {str(e)}"

def handle_profile_update(data, conn):
    try:
        parts = data.split("|")
        if len(parts) != 8:
            return "ERROR|Invalid update format"

        _, user_id, first_name, last_name, phone, area, is_driver, photo_path = parts

        # Validate user_id
        if not validator.validate_user_id(user_id):
            return "ERROR|Invalid user ID"

        cursor = conn.cursor()
        cursor.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()

        if result is None:
            return "ERROR|Profile not found"

        # Update fields only if valid and present
        if first_name:
            first_check = validator.validate_name(first_name, "First name")
            if first_check != "VALID":
                return first_check
            cursor.execute("UPDATE profiles SET first_name=? WHERE user_id=?", (first_name, user_id))

        if last_name:
            last_check = validator.validate_name(last_name, "Last name")
            if last_check != "VALID":
                return last_check
            cursor.execute("UPDATE profiles SET last_name=? WHERE user_id=?", (last_name, user_id))

        if phone:
            phone_check = validator.validate_phone(phone)
            if phone_check != "VALID":
                return phone_check
            cursor.execute("UPDATE profiles SET phone=? WHERE user_id=?", (phone, user_id))

        if area:
            area_check = validator.validate_area(area)
            if area_check != "VALID":
                return area_check
            cursor.execute("UPDATE profiles SET area=? WHERE user_id=?", (area, user_id))

        if is_driver:
            flag_check = validator.validate_boolean_flag(is_driver, "Driver flag")
            if flag_check != "VALID":
                return flag_check
            cursor.execute("UPDATE profiles SET is_driver=? WHERE user_id=?", (is_driver, user_id))

        if photo_path:
            if not validator.validate_file_path(photo_path):
                return "ERROR|Invalid photo path"
            cursor.execute("UPDATE profiles SET profile_photo_path=? WHERE user_id=?", (photo_path, user_id))

        conn.commit()
        return "SUCCESS|Profile updated"

    except Exception as e:
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
            SELECT first_name, last_name, phone, area, is_driver, profile_photo_path
            FROM profiles
            WHERE user_id = ?
        """, (user_id,))
        result = cursor.fetchone()

        if result is None:
            return "ERROR|Profile not found"

        first_name, last_name, phone, area, is_driver, photo_path = result
        return f"SUCCESS|{first_name}|{last_name}|{phone}|{area}|{is_driver}|{photo_path}"

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
