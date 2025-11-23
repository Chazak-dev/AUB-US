import sys
import os
sys.path.append(os.path.dirname(__file__))
import validator

def handle_notification_send(message, conn):
    """
    Handle sending a notification.
    Expected format:
      NOTIFICATION_SEND|user_id|type|title|message|[related_id]
    - user_id: positive integer
    - type: string (e.g., 'alert', 'info')
    - title: short string
    - message: string
    - related_id: optional integer (e.g., ride_id)
    """
    try:
        # Split the incoming message by "|" to extract fields
        parts = message.split("|")
        if len(parts) < 5:
            return "NOTIFICATION_SEND|ERROR|Invalid format"

        # Unpack required fields
        _, user_id, ntype, title, msg, *related = parts

        # Validate user_id
        if not validator.validate_user_id(user_id):
            return "NOTIFICATION_SEND|ERROR|Invalid user_id"

        # Validate title/message (basic non-empty checks)
        if not title or len(title.strip()) == 0:
            return "NOTIFICATION_SEND|ERROR|Title cannot be empty"
        if not msg or len(msg.strip()) == 0:
            return "NOTIFICATION_SEND|ERROR|Message cannot be empty"

        # If related_id exists, validate it
        related_id = related[0] if related else None
        if related_id and not validator.validate_user_id(related_id):
            return "NOTIFICATION_SEND|ERROR|Invalid related_id"

        cur = conn.cursor()
        cur.execute("""
            INSERT INTO notifications (user_id, notification_type, title, message, related_id)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, ntype, title, msg, related_id))

        conn.commit()
        return f"NOTIFICATION_SEND|SUCCESS|notification_id={cur.lastrowid}"
    except Exception as e:
        return f"NOTIFICATION_SEND|ERROR|{str(e)}"


def handle_notification_read(message, conn):
    """
    Handle marking a notification as read.
    Expected format:
      NOTIFICATION_READ|notif_id|user_id
    - notif_id: positive integer
    - user_id: positive integer
    """
    try:
        parts = message.split("|")
        if len(parts) != 3:
            return "NOTIFICATION_READ|ERROR|Invalid format"

        _, notif_id, user_id = parts

        # Validate IDs
        if not validator.validate_user_id(notif_id):
            return "NOTIFICATION_READ|ERROR|Invalid notif_id"
        if not validator.validate_user_id(user_id):
            return "NOTIFICATION_READ|ERROR|Invalid user_id"

        cur = conn.cursor()
        cur.execute("""
            UPDATE notifications SET is_read = 1
            WHERE id = ? AND user_id = ?
        """, (notif_id, user_id))

        conn.commit()
        return f"NOTIFICATION_READ|SUCCESS|notification_id={notif_id}"
    except Exception as e:
        return f"NOTIFICATION_READ|ERROR|{str(e)}"


def handle_notification_clear(message, conn):
    """
    Handle clearing notifications.
    Expected format:
      NOTIFICATION_CLEAR|user_id|clear_type|[extra]
    - user_id: positive integer
    - clear_type: 'all', 'read', or 'by_date'
    - extra: optional date (YYYY-MM-DD HH:MM:SS) if clear_type = 'by_date'
    """
    try:
        parts = message.split("|")
        if len(parts) < 3:
            return "NOTIFICATION_CLEAR|ERROR|Invalid format"

        _, user_id, clear_type, *extra = parts

        # Validate user_id
        if not validator.validate_user_id(user_id):
            return "NOTIFICATION_CLEAR|ERROR|Invalid user_id"

        cur = conn.cursor()

        if clear_type == "all":
            cur.execute("DELETE from .notifications WHERE user_id = ?", (user_id,))
        elif clear_type == "read":
            cur.execute("DELETE from .notifications WHERE user_id = ? AND is_read = 1", (user_id,))
        elif clear_type == "by_date":
            date = extra[0] if extra else None
            if not date or not validator.validate_timestamp(date):
                return "NOTIFICATION_CLEAR|ERROR|Invalid date"
            cur.execute("DELETE from .notifications WHERE user_id = ? AND created_at < ?", (user_id, date))
        else:
            return "NOTIFICATION_CLEAR|ERROR|Invalid clear_type"

        count = cur.rowcount
        conn.commit()
        return f"NOTIFICATION_CLEAR|SUCCESS|count={count}"
    except Exception as e:
        return f"NOTIFICATION_CLEAR|ERROR|{str(e)}"
