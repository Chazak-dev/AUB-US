from validator import validator

def handle_chat_message_send(data, conn):
    """
    Handle sending a chat message.
    Expected format:
      CHAT_MESSAGE_SEND|request_id|sender_id|message_text|timestamp
    - request_id: positive integer
    - sender_id: positive integer
    - message_text: string (non-empty)
    - timestamp: YYYY-MM-DD HH:MM:SS
    """
    try:
        parts = data.split("|", 4)
        if len(parts) != 5:
            return "ERROR|Invalid message format"

        _, request_id, sender_id, message_text, timestamp = parts

        # Validate IDs
        if not validator.validate_user_id(request_id):
            return "ERROR|Invalid request_id"
        if not validator.validate_user_id(sender_id):
            return "ERROR|Invalid sender_id"

        # Validate message text
        if not message_text or len(message_text.strip()) == 0:
            return "ERROR|Message text cannot be empty"

        # Validate timestamp
        if not validator.validate_timestamp(timestamp):
            return "ERROR|Invalid timestamp"

        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO chat_messages (request_id, sender_id, message_text, timestamp)
            VALUES (?, ?, ?, ?)
        """, (request_id, sender_id, message_text, timestamp))
        conn.commit()

        return f"SUCCESS|Message sent for ride {request_id}"
    except Exception as e:
        return f"ERROR|Chat message send failed: {str(e)}"


def handle_chat_message_receive(data, conn):
    """
    Handle receiving chat messages for a ride.
    Expected format:
      CHAT_MESSAGE_RECEIVE|request_id
    - request_id: positive integer
    """
    try:
        parts = data.split("|")
        if len(parts) != 2:
            return "ERROR|Invalid message format"

        _, request_id = parts

        # Validate request_id
        if not validator.validate_user_id(request_id):
            return "ERROR|Invalid request_id"

        cursor = conn.cursor()
        cursor.execute("""
            SELECT sender_id, message_text, timestamp
            FROM chat_messages
            WHERE request_id=?
            ORDER BY timestamp ASC
        """, (request_id,))
        results = cursor.fetchall()

        if not results:
            return "ERROR|No messages found"

        # Build response string with all messages
        messages = ";".join([f"{sid}|{msg}|{ts}" for sid, msg, ts in results])
        return f"SUCCESS|{request_id}|{messages}"
    except Exception as e:
        return f"ERROR|Chat message receive failed: {str(e)}"


def handle_chat_media_send(data, conn):
    """
    Handle sending media in chat.
    Expected format:
      CHAT_MEDIA_SEND|request_id|sender_id|media_type|media_data|file_extension
    - request_id: positive integer
    - sender_id: positive integer
    - media_type: string (e.g., 'image', 'video')
    - media_data: base64 or encoded string
    - file_extension: jpg, png, etc.
    """
    try:
        parts = data.split("|", 5)
        if len(parts) != 6:
            return "ERROR|Invalid message format"

        _, request_id, sender_id, media_type, media_data, file_extension = parts

        # Validate IDs
        if not validator.validate_user_id(request_id):
            return "ERROR|Invalid request_id"
        if not validator.validate_user_id(sender_id):
            return "ERROR|Invalid sender_id"

        # Validate file extension
        if not validator.validate_file_extension(file_extension):
            return "ERROR|Unsupported file extension"

        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO chat_media (request_id, sender_id, media_type, media_data, file_extension)
            VALUES (?, ?, ?, ?, ?)
        """, (request_id, sender_id, media_type, media_data, file_extension))
        conn.commit()

        return f"SUCCESS|Media sent for ride {request_id}"
    except Exception as e:
        return f"ERROR|Chat media send failed: {str(e)}"


def handle_chat_status_update(data, conn):
    """
    Handle updating a user's chat status (e.g., online/offline).
    Expected format:
      CHAT_STATUS_UPDATE|user_id|status
    - user_id: positive integer
    - status: string (e.g., 'online', 'offline', 'typing')
    """
    try:
        parts = data.split("|")
        if len(parts) != 3:
            return "ERROR|Invalid message format"

        _, user_id, status = parts

        # Validate user_id
        if not validator.validate_user_id(user_id):
            return "ERROR|Invalid user_id"

        # Validate status (basic non-empty check)
        if not status or len(status.strip()) == 0:
            return "ERROR|Invalid status"

        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO chat_status (user_id, status, last_update)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET status=excluded.status, last_update=CURRENT_TIMESTAMP
        """, (user_id, status))
        conn.commit()

        return f"SUCCESS|User {user_id} status updated to {status}"
    except Exception as e:
        return f"ERROR|Chat status update failed: {str(e)}"