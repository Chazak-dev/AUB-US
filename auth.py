import hashlib

import sys
import os
sys.path.append(os.path.dirname(__file__))
import validator

def handle_register(data, conn, sessions_dict, connection_sessions_dict):
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

        #  Validate password
        if not validator.validate_password(password):
            return "ERROR|Weak password"

               
        # Hash the password
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        # Insert into database
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (username, email, password, first_name, last_name, address, photo, is_driver)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (username, email, hashed_password, first_name, last_name, address, photo, is_driver))
       
        user_id = cursor.lastrowid
        conn.commit()
        
        user_data = {
            'username': username,
            'email': email,
            'user_id': user_id
        }
        sessions_dict[str(user_id)] = user_data
        connection_sessions_dict[conn] = str(user_id)
        
        return f"SUCCESS|User registered|{user_id}"

    except Exception as e:
        return f"ERROR|Database error: {str(e)}"

def handle_login(data, conn, sessions_dict, connection_sessions_dict):
    try:
        parts = data.split("|")
        if len(parts) != 3:
            return "ERROR|Invalid login format"

        _, username, password = parts

        if not validator.validate_username(username):
            return "ERROR|Invalid username"
        if not validator.validate_password(password):
            return "ERROR|Invalid password format"

        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        cursor = conn.cursor()
        cursor.execute("SELECT id, password, email FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()

        if result is None:
            return "ERROR|Username not found"

        user_id, stored_password, stored_email = result

        if stored_password == hashed_password:
            # CREATE SESSION like in register
            user_data = {
                'username': username,
                'email': stored_email,
                'user_id': user_id
            }
            sessions_dict[str(user_id)] = user_data
            connection_sessions_dict[conn] = str(user_id)
            
            return f"SUCCESS|Login successful|{stored_email}|{user_id}"
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
