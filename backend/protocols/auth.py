import hashlib

from .validator import validator

def handle_register(data, conn):
    try:
        # Split the incoming message into parts
        parts = data.split("|")
        if len(parts) != 9:
            return "ERROR|Invalid registration format"

        # Unpack fields
        _, username, email, password, first_name, last_name, address, photo, is_driver = parts

        #  Validate username
        if not validator.validate_username(username):
            return "ERROR|Invalid username"

        #  Validate email
        if not validator.validate_email(email):
            return "ERROR|Invalid email"

        #  Validate password
        if not validator.validate_password(password):
            return "ERROR|Weak password"

        #  Validate first name and last name
        first_name_check = validator.validate_name(first_name, "First name")
        if first_name_check != "VALID":
            return first_name_check

        last_name_check = validator.validate_name(last_name, "Last name")
        if last_name_check != "VALID":
            return last_name_check

        #  Validate address (optional — you can add stricter rules if needed)
        if not address or len(address.strip()) == 0:
            return "ERROR|Address is required"

        #  Validate photo path (optional — you can add file extension check if needed)
        if not validator.validate_file_path(photo):
            return "ERROR|Invalid photo path"

        #  Validate is_driver flag
        flag_check = validator.validate_boolean_flag(is_driver, "Driver flag")
        if flag_check != "VALID":
            return flag_check

        # Hash the password securely
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        # Insert validated data into the database
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (username, email, password, first_name, last_name, address, photo, is_driver)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (username, email, hashed_password, first_name, last_name, address, photo, is_driver))

        conn.commit()
        return "SUCCESS|User registered"

    except Exception as e:
        return f"ERROR|Database error: {str(e)}"
    

def handle_login(data, conn):
    try:
        # Split the incoming message
        parts = data.split("|")
        if len(parts) != 3:
            return "ERROR|Invalid login format"

        _, username, password = parts

        #  Validate username and password
        if not validator.validate_username(username):
            return "ERROR|Invalid username"
        if not validator.validate_password(password):
            return "ERROR|Invalid password format"

        # Hash the password for comparison
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        cursor = conn.cursor()
        cursor.execute("SELECT password, email FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()

        if result is None:
            return "ERROR|Username not found"

        stored_password, stored_email = result

        if stored_password == hashed_password:
            return f"SUCCESS|Login successful|{stored_email}"
        else:
            return "ERROR|Incorrect password"

    except Exception as e:
        return f"ERROR|Login failed: {str(e)}"
    
def handle_logout(data, conn):
    try:
        # Split data into parts
        parts = data.split("|")
        if len(parts) != 3:
            return "ERROR|Invalid logout format"

        _, user_id, session_token = parts

        #  Validate user_id
        if not validator.validate_user_id(user_id):
            return "ERROR|Invalid user ID"

        # Validate session_token (basic length check)
        if not session_token or len(session_token.strip()) < 10:
            return "ERROR|Invalid session token"

        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE user_id=? AND session_token=?", (user_id, session_token))
        result = cursor.fetchone()

        if result is None:
            return "ERROR|Invalid session"

        cursor.execute("DELETE FROM sessions WHERE user_id=? AND session_token=?", (user_id, session_token))
        conn.commit()

        return "SUCCESS|Logout successful"

    except Exception as e:
        return f"ERROR|Logout failed: {str(e)}"
