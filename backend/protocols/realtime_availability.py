from .validator import validator

def handle_driver_availability_set(message, conn):
    """
    Sets a driver's availability (online/offline).
    Expected:
      DRIVER_AVAILABILITY_SET|driver_id|status
    - driver_id: integer (string in message, cast as needed)
    - status: 'online' or 'offline'
    """

    # Split the raw message into parts
    parts = message.split("|")
    if len(parts) < 3:
        return "DRIVER_AVAILABILITY_SET|ERROR|Invalid format"

    # Unpack fields: command, driver_id, status
    _, driver_id, status = parts

    # Validate driver_id (must be positive integer)
    if not validator.validate_user_id(driver_id):
        return "DRIVER_AVAILABILITY_SET|ERROR|Invalid driver_id"

    # Normalize and validate status
    status = status.strip().lower()
    if status not in ("online", "offline"):
        return "DRIVER_AVAILABILITY_SET|ERROR|Invalid status"

    # Map status to integer for storage (1 = online, 0 = offline)
    availability_value = 1 if status == "online" else 0

    cur = conn.cursor()

    # Update the driver's availability in the drivers table
    cur.execute("""
        UPDATE drivers
        SET availability = ?
        WHERE id = ?
    """, (availability_value, driver_id))

    # If no rows were updated, the driver_id might be invalid
    if cur.rowcount == 0:
        return "DRIVER_AVAILABILITY_SET|ERROR|Driver not found"

    # Log the change to keep historical audit (optional but helpful)
    cur.execute("""
        INSERT INTO driver_status_logs (driver_id, status)
        VALUES (?, ?)
    """, (driver_id, status))

    # Persist both the update and the log entry
    conn.commit()

    # Respond with success and the new status
    return f"DRIVER_AVAILABILITY_SET|SUCCESS|driver_id={driver_id}|status={status}"


def handle_driver_availability_get(message, conn):
    """
    Retrieves a driver's current availability.
    Expected:
      DRIVER_AVAILABILITY_GET|driver_id
    """

    # Split the raw message into parts
    parts = message.split("|")
    if len(parts) < 2:
        return "DRIVER_AVAILABILITY_GET|ERROR|Invalid format"

    _, driver_id = parts

    # Validate driver_id
    if not validator.validate_user_id(driver_id):
        return "DRIVER_AVAILABILITY_GET|ERROR|Invalid driver_id"

    cur = conn.cursor()

    # Fetch the availability flag for the given driver
    cur.execute("""
        SELECT availability
        from .drivers
        WHERE id = ?
    """, (driver_id,))
    row = cur.fetchone()

    # If no driver found, return an error
    if not row:
        return "DRIVER_AVAILABILITY_GET|ERROR|Driver not found"

    # Translate integer flag back to human-readable status
    status = "online" if row[0] == 1 else "offline"

    return f"DRIVER_AVAILABILITY_GET|SUCCESS|driver_id={driver_id}|status={status}"


def handle_active_drivers_get(message, conn):
    """
    Lists all drivers who are currently online.
    Expected:
      ACTIVE_DRIVERS_GET
    """

    # Split the raw message into parts
    parts = message.split("|")
    # Command can be sent as a single token; ignore extra fields gracefully
    # Example: ACTIVE_DRIVERS_GET or ACTIVE_DRIVERS_GET|region(optional)
    command = parts[0]
    if command != "ACTIVE_DRIVERS_GET":
        return "ACTIVE_DRIVERS_GET|ERROR|Invalid command"

    cur = conn.cursor()

    # Retrieve minimal driver info for those online
    cur.execute("""
        SELECT id, name, vehicle
        from .drivers
        WHERE availability = 1
        ORDER BY id ASC
    """)
    rows = cur.fetchall()

    # If no drivers are online, return a clear message
    if not rows:
        return "ACTIVE_DRIVERS_GET|SUCCESS|No active drivers"

    # Format rows as a simple list of dict-like strings for the client
    # In production you'd serialize to JSON; here we keep your protocol style.
    formatted = ";".join([f"id={r[0]},name={r[1]},vehicle={r[2]}" for r in rows])

    return f"ACTIVE_DRIVERS_GET|SUCCESS|{formatted}"
