import sys
import os
sys.path.append(os.path.dirname(__file__))
import validator

def handle_ride_request_create(data, conn):
    """
    Create a new ride request and return the request_id
    Format: RIDE_REQUEST_CREATE|passenger_id|pickup_area|destination|request_time
    """
    try:
        parts = data.split("|")
        if len(parts) < 5:
            return "ERROR|Invalid message format"

        _, passenger_id, pickup_area, destination, request_time = parts[:5]
        preferred_vehicle_type = parts[5] if len(parts) > 5 else None

        # Validate passenger_id
        if not validator.validate_user_id(passenger_id):
            return "ERROR|Invalid passenger_id"

        # Validate pickup and destination
        location_check = validator.validate_ride_locations(pickup_area, destination)
        if location_check != "VALID":
            return location_check

        # Validate timestamp
        if not validator.validate_timestamp(request_time):
            return "ERROR|Invalid request_time"

        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO ride_requests (
                passenger_id, pickup_area, destination, request_time, preferred_vehicle_type, status, is_locked
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (passenger_id, pickup_area, destination, request_time, preferred_vehicle_type, "pending", False))

        request_id = cursor.lastrowid
        conn.commit()
        
        # CRITICAL FIX: Return the request_id in response
        return f"SUCCESS|Ride request created|{request_id}"
        
    except Exception as e:
        return f"ERROR|Ride request failed: {str(e)}"

def handle_ride_request_accept(command, conn, client_address=None):
    """Accept a ride request as driver with P2P connection info"""
    try:
        parts = command.split("|")
        # Now expecting: RIDE_REQUEST_ACCEPT|driver_id|request_id|acceptance_time|driver_port
        if len(parts) < 5:
            return "ERROR|Invalid format - expected driver_id|request_id|acceptance_time|driver_port"
        
        _, driver_id, request_id, acceptance_time, driver_port_str = parts
        
        # Get driver's IP address from client_address parameter
        if client_address:
            driver_ip = client_address[0]  # Extract IP from (IP, port) tuple
        else:
            driver_ip = "127.0.0.1"  # Fallback to localhost
        
        # Validate port number
        try:
            driver_port = int(driver_port_str)
            if not (1024 <= driver_port <= 65535):
                return "ERROR|Invalid port number (must be 1024-65535)"
        except ValueError:
            return "ERROR|Invalid port format"
        
        # Validate inputs
        if not validator.validate_user_id(driver_id) or not validator.validate_user_id(request_id):
            return "ERROR|Invalid user_id or request_id"
        
        cur = conn.cursor()
        
        # Check if ride is still available and not already accepted
        cur.execute("""
            SELECT status, is_locked, accepted_driver_id 
            FROM ride_requests 
            WHERE request_id = ? AND status = 'pending'
        """, (request_id,))
        
        ride = cur.fetchone()
        if not ride:
            return "ERROR|Ride not available or already taken"
        
        status, is_locked, accepted_driver = ride
        
        if is_locked or accepted_driver:
            return "ERROR|Ride already accepted by another driver"
        
        # Update the ride request with driver acceptance AND P2P connection info
        cur.execute("""
            UPDATE ride_requests 
            SET accepted_driver_id = ?, 
                acceptance_time = ?, 
                status = 'accepted', 
                is_locked = 1,
                driver_ip = ?,
                driver_port = ?,
                driver_p2p_status = 'online'
            WHERE request_id = ? AND status = 'pending'
        """, (driver_id, acceptance_time, driver_ip, driver_port, request_id))
        
        # Also update the rides table for active ride tracking
        cur.execute("""
            INSERT INTO rides (driver_id, passenger_id, start_time, status)
            SELECT ?, passenger_id, ?, 'active'
            FROM ride_requests WHERE request_id = ?
        """, (driver_id, acceptance_time, request_id))
        
        ride_id = cur.lastrowid
        
        # Update driver status to busy
        cur.execute("""
            UPDATE driver_status 
            SET is_online = 0 
            WHERE user_id = ?
        """, (driver_id,))
        
        conn.commit()
        
        print(f"✅ Ride accepted: request={request_id}, ride={ride_id}, driver={driver_ip}:{driver_port}")
        
        return f"SUCCESS|Ride accepted|{request_id}|{ride_id}"
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Ride accept error: {e}")
        import traceback
        traceback.print_exc()
        return f"ERROR|Ride request accept failed: {str(e)}"

def handle_ride_requests_get_pending(command, conn):
    """Get all pending ride requests"""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT request_id, passenger_id, pickup_area, destination, request_time
            FROM ride_requests 
            WHERE status = 'pending' AND is_locked = 0
            ORDER BY request_time ASC
        """)
        
        pending_requests = cursor.fetchall()
        
        if not pending_requests:
            return "SUCCESS|No pending requests"
        
        response_parts = ["SUCCESS"]
        for request in pending_requests:
            response_parts.extend([
                str(request[0]),
                str(request[1]), 
                request[2],
                request[3],
                request[4]
            ])
        
        return "|".join(response_parts)
        
    except Exception as e:
        return f"ERROR|Failed to get pending requests: {str(e)}"

def handle_ride_request_status(data, conn):
    """Get status of a ride request"""
    try:
        _, request_id = data.split("|")

        # Validate request_id
        if not validator.validate_user_id(request_id):
            return "ERROR|Invalid request_id"

        cursor = conn.cursor()
        cursor.execute("""
            SELECT status, accepted_driver_id, acceptance_time, is_locked
            FROM ride_requests WHERE request_id=?
        """, (request_id,))
        result = cursor.fetchone()
        
        if result is None:
            return "ERROR|Request not found"

        status, accepted_driver_id, acceptance_time, is_locked = result
        return f"SUCCESS|{status}|{accepted_driver_id or 'None'}|{acceptance_time or 'None'}|Locked={is_locked}"
        
    except Exception as e:
        return f"ERROR|Status check failed: {str(e)}"

# Other ride functions...
def handle_ride_lock_acquire(data, conn):
    try:
        _, request_id, driver_id, lock_timestamp = data.split("|")
        if not validator.validate_user_id(request_id):
            return "ERROR|Invalid request_id"
        if not validator.validate_user_id(driver_id):
            return "ERROR|Invalid driver_id"
        if not validator.validate_timestamp(lock_timestamp):
            return "ERROR|Invalid timestamp"

        cursor = conn.cursor()
        cursor.execute("SELECT is_locked FROM ride_requests WHERE request_id=?", (request_id,))
        result = cursor.fetchone()
        if result is None:
            return "ERROR|Request not found"
        if result[0]:
            return f"RIDE_ALREADY_TAKEN|{request_id}|UnknownDriver"

        cursor.execute("""
            UPDATE ride_requests
            SET is_locked=?, accepted_driver_id=?, acceptance_time=?
            WHERE request_id=?
        """, (True, driver_id, lock_timestamp, request_id))

        conn.commit()
        return "SUCCESS|Lock acquired"
    except Exception as e:
        return f"ERROR|Lock acquire failed: {str(e)}"

def handle_ride_request_decline(data, conn):
    try:
        parts = data.split("|")
        if len(parts) < 3:
            return "ERROR|Invalid message format"

        _, driver_id, request_id = parts[:3]
        reason = parts[3] if len(parts) > 3 else None

        if not validator.validate_user_id(driver_id):
            return "ERROR|Invalid driver_id"
        if not validator.validate_user_id(request_id):
            return "ERROR|Invalid request_id"

        cursor = conn.cursor()
        cursor.execute("SELECT is_locked, accepted_driver_id FROM ride_requests WHERE request_id=?", (request_id,))
        result = cursor.fetchone()
        if result is None:
            return "ERROR|Request not found"

        is_locked, accepted_driver_id = result
        if not is_locked or int(driver_id) != int(accepted_driver_id):
            return "ERROR|You cannot decline this request"

        cursor.execute("""
            INSERT INTO ride_declines (driver_id, request_id, reason)
            VALUES (?, ?, ?)
        """, (driver_id, request_id, reason))

        cursor.execute("""
            UPDATE ride_requests
            SET status='declined', is_locked=?, accepted_driver_id=NULL, acceptance_time=NULL
            WHERE request_id=?
        """, (False, request_id))

        conn.commit()
        return "SUCCESS|Ride request declined"
    except Exception as e:
        return f"ERROR|Ride request decline failed: {str(e)}"

def handle_ride_request_expire(data, conn):
    try:
        _, request_id = data.split("|")
        if not validator.validate_user_id(request_id):
            return "ERROR|Invalid request_id"

        cursor = conn.cursor()
        cursor.execute("SELECT status FROM ride_requests WHERE request_id=?", (request_id,))
        result = cursor.fetchone()
        if result is None:
            return "ERROR|Request not found"

        status = result[0]
        if status != "pending":
            return f"ERROR|Request {request_id} is not pending (current status: {status})"

        cursor.execute("""
            UPDATE ride_requests
            SET status='expired', is_locked=?, accepted_driver_id=NULL, acceptance_time=NULL
            WHERE request_id=?
        """, (False, request_id))

        conn.commit()
        return f"SUCCESS|Ride request {request_id} expired"
    except Exception as e:
        return f"ERROR|Ride request expire failed: {str(e)}"

def handle_ride_request_cancel(data, conn):
    try:
        parts = data.split("|")
        if len(parts) < 3:
            return "ERROR|Invalid message format"

        _, request_id, passenger_id = parts[:3]
        reason = parts[3] if len(parts) > 3 else None

        if not validator.validate_user_id(request_id):
            return "ERROR|Invalid request_id"
        if not validator.validate_user_id(passenger_id):
            return "ERROR|Invalid passenger_id"

        cursor = conn.cursor()
        cursor.execute("SELECT status, passenger_id FROM ride_requests WHERE request_id=?", (request_id,))
        result = cursor.fetchone()
        if result is None:
            return "ERROR|Request not found"

        status, db_passenger_id = result
        if int(passenger_id) != int(db_passenger_id):
            return "ERROR|Passenger ID mismatch"

        if status not in ("pending", "accepted"):
            return f"ERROR|Request {request_id} cannot be cancelled (current status: {status})"

        cursor.execute("""
            INSERT INTO ride_cancellations (request_id, cancelled_by, reason)
            VALUES (?, ?, ?)
        """, (request_id, "passenger", reason))

        cursor.execute("""
            UPDATE ride_requests
            SET status='cancelled', is_locked=?, accepted_driver_id=NULL, acceptance_time=NULL
            WHERE request_id=?
        """, (False, request_id))

        conn.commit()
        return f"SUCCESS|Ride request {request_id} cancelled by passenger {passenger_id}"
    except Exception as e:
        return f"ERROR|Ride request cancel failed: {str(e)}"

def handle_ride_request_complete(data, conn):
    try:
        parts = data.split("|")
        if len(parts) < 3:
            return "ERROR|Invalid message format"

        _, request_id, completion_time = parts[:3]
        fare_final = parts[3] if len(parts) > 3 else None

        if not validator.validate_user_id(request_id):
            return "ERROR|Invalid request_id"
        if not validator.validate_timestamp(completion_time):
            return "ERROR|Invalid completion_time"

        cursor = conn.cursor()
        cursor.execute("SELECT status, is_locked FROM ride_requests WHERE request_id=?", (request_id,))
        result = cursor.fetchone()
        if result is None:
            return "ERROR|Request not found"

        status, is_locked = result
        if status != "accepted" or not is_locked:
            return "ERROR|Request not in accepted/locked state"

        cursor.execute("""
            UPDATE ride_requests
            SET status='completed', completion_time=?, fare_final=?, is_locked=?
            WHERE request_id=?
        """, (completion_time, fare_final, False, request_id))

        conn.commit()
        return "SUCCESS|Ride request completed"
    except Exception as e:
        return f"ERROR|Ride request complete failed: {str(e)}"

def handle_ride_cancel_active(data, conn):
    try:
        parts = data.split("|")
        if len(parts) < 3:
            return "ERROR|Invalid message format"

        _, request_id, cancelled_by = parts[:3]
        reason = parts[3] if len(parts) > 3 else None

        if not validator.validate_user_id(request_id):
            return "ERROR|Invalid request_id"

        cursor = conn.cursor()
        cursor.execute("SELECT status, is_locked FROM ride_requests WHERE request_id=?", (request_id,))
        result = cursor.fetchone()
        if result is None:
            return "ERROR|Request not found"

        status, is_locked = result
        if status not in ("pending", "accepted"):
            return "ERROR|Request not active"

        cursor.execute("""
            INSERT INTO ride_cancellations (request_id, cancelled_by, reason)
            VALUES (?, ?, ?)
        """, (request_id, cancelled_by, reason))

        cursor.execute("""
            UPDATE ride_requests
            SET status='cancelled', is_locked=?, accepted_driver_id=NULL, acceptance_time=NULL
            WHERE request_id=?
        """, (False, request_id))

        conn.commit()
        return "SUCCESS|Ride request cancelled"
    except Exception as e:
        return f"ERROR|Ride cancel failed: {str(e)}"

def handle_ride_status_update(data, conn):
    try:
        parts = data.split("|")
        if len(parts) < 3:
            return "ERROR|Invalid message format"

        _, request_id, status = parts[:3]
        eta_minutes = parts[3] if len(parts) > 3 and parts[3] else None
        current_location = parts[4] if len(parts) > 4 and parts[4] else None

        if not validator.validate_user_id(request_id):
            return "ERROR|Invalid request_id"

        cursor = conn.cursor()
        cursor.execute("SELECT request_id FROM ride_requests WHERE request_id=?", (request_id,))
        if cursor.fetchone() is None:
            return "ERROR|Request not found"

        cursor.execute("""
            UPDATE ride_requests
            SET current_status=?, eta_minutes=?, current_location=?
            WHERE request_id=?
        """, (status, eta_minutes, current_location, request_id))

        conn.commit()
        return f"SUCCESS|Ride {request_id} status updated to {status}"
    except Exception as e:
        return f"ERROR|Ride status update failed: {str(e)}"

def handle_ride_location_share(data, conn):
    try:
        parts = data.split("|")
        if len(parts) < 6:
            return "ERROR|Invalid message format"

        _, request_id, user_id, latitude, longitude, timestamp = parts

        if not validator.validate_user_id(request_id):
            return "ERROR|Invalid request_id"
        if not validator.validate_user_id(user_id):
            return "ERROR|Invalid user_id"
        if not validator.validate_coordinate(latitude, "latitude"):
            return "ERROR|Invalid latitude"
        if not validator.validate_coordinate(longitude, "longitude"):
            return "ERROR|Invalid longitude"
        if not validator.validate_timestamp(timestamp):
            return "ERROR|Invalid timestamp"

        cursor = conn.cursor()
        cursor.execute("SELECT request_id FROM ride_requests WHERE request_id=?", (request_id,))
        if cursor.fetchone() is None:
            return "ERROR|Request not found"

        cursor.execute("""
            INSERT INTO ride_locations (request_id, user_id, latitude, longitude, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (request_id, user_id, float(latitude), float(longitude), timestamp))

        conn.commit()
        return f"SUCCESS|Location shared for ride {request_id}"
    except Exception as e:
        return f"ERROR|Ride location share failed: {str(e)}"

def handle_ride_location_latest(data, conn):
    try:
        parts = data.split("|")
        if len(parts) != 2:
            return "ERROR|Invalid message format"

        _, request_id = parts

        if not validator.validate_user_id(request_id):
            return "ERROR|Invalid request_id"

        cursor = conn.cursor()
        cursor.execute("""
            SELECT latitude, longitude, timestamp, user_id
            FROM ride_locations
            WHERE request_id=?
            ORDER BY timestamp DESC
            LIMIT 1
        """, (request_id,))
        result = cursor.fetchone()

        if result is None:
            return "ERROR|No location data found"

        latitude, longitude, timestamp, user_id = result
        return f"SUCCESS|{request_id}|{latitude}|{longitude}|{timestamp}|User={user_id}"
    except Exception as e:
        return f"ERROR|Latest location query failed: {str(e)}"

def handle_ride_location_history(data, conn):
    try:
        parts = data.split("|")
        if len(parts) != 2:
            return "ERROR|Invalid message format"

        _, request_id = parts

        if not validator.validate_user_id(request_id):
            return "ERROR|Invalid request_id"

        cursor = conn.cursor()
        cursor.execute("""
            SELECT latitude, longitude, timestamp, user_id
            FROM ride_locations
            WHERE request_id=?
            ORDER BY timestamp ASC
        """, (request_id,))
        results = cursor.fetchall()

        if not results:
            return "ERROR|No location history found"

        history = ";".join([
            f"{lat},{lon},{ts},User={uid}"
            for lat, lon, ts, uid in results
        ])
        return f"SUCCESS|{request_id}|{history}"
    except Exception as e:
        return f"ERROR|Location history query failed: {str(e)}"
    
def handle_ride_already_taken(data, conn):
    try:
        _, request_id, accepted_driver_name = data.split("|")

        if not validator.validate_user_id(request_id):
            return "ERROR|Invalid request_id"

        name_check = validator.validate_name(accepted_driver_name, "Driver name")
        if name_check != "VALID":
            return name_check

        return f"INFO|Ride {request_id} already taken by {accepted_driver_name}"
    except Exception as e:
        return f"ERROR|Already taken notify failed: {str(e)}"
    
def handle_ride_lock_release(data, conn):
    try:
        _, request_id = data.split("|")

        if not validator.validate_user_id(request_id):
            return "ERROR|Invalid request_id"

        cursor = conn.cursor()
        cursor.execute("""
            UPDATE ride_requests
            SET is_locked=?, accepted_driver_id=NULL, acceptance_time=NULL, status='pending'
            WHERE request_id=?
        """, (False, request_id))

        conn.commit()
        return "SUCCESS|Lock released"
    except Exception as e:
        return f"ERROR|Lock release failed: {str(e)}"

def handle_ride_request_notify_drivers(data, conn):
    try:
        parts = data.split("|")
        if len(parts) != 9:
            return "ERROR|Invalid message format"

        (_, request_id, passenger_name, passenger_rating,
         pickup_area, destination, estimated_fare,
         timeout_seconds, is_locked) = parts

        if not validator.validate_user_id(request_id):
            return "ERROR|Invalid request_id"
        name_check = validator.validate_name(passenger_name, "Passenger name")
        if name_check != "VALID":
            return name_check
        if not validator.validate_rating(passenger_rating):
            return "ERROR|Invalid passenger_rating"
        location_check = validator.validate_ride_locations(pickup_area, destination)
        if location_check != "VALID":
            return location_check
        try:
            estimated_fare = float(estimated_fare)
        except ValueError:
            return "ERROR|Invalid fare"
        try:
            timeout_seconds = int(timeout_seconds)
            if timeout_seconds <= 0:
                return "ERROR|Invalid timeout"
        except ValueError:
            return "ERROR|Invalid timeout"
        flag_check = validator.validate_boolean_flag(is_locked, "Lock flag")
        if flag_check != "VALID":
            return flag_check

        cursor = conn.cursor()
        cursor.execute("SELECT is_locked FROM ride_requests WHERE request_id=?", (request_id,))
        result = cursor.fetchone()
        if result and result[0]:
            return f"ERROR|Request {request_id} is locked"

        cursor.execute("""
            INSERT INTO ride_notifications (
                request_id, passenger_name, passenger_rating, pickup_area, destination,
                estimated_fare, timeout_seconds, is_locked
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (request_id, passenger_name, float(passenger_rating),
              pickup_area, destination, estimated_fare, timeout_seconds,
              is_locked.lower() == "true"))

        conn.commit()
        return "SUCCESS|Ride request notified"
    except Exception as e:
        return f"ERROR|Ride request notify failed: {str(e)}"



def handle_ride_get_driver_info(command, conn):
    """
    Get driver's P2P connection information for a ride request
    Format: RIDE_GET_DRIVER_INFO|request_id
    Returns: SUCCESS|driver_id|driver_ip|driver_port|driver_name|p2p_status
    """
    try:
        parts = command.split('|')
        if len(parts) != 2:
            return 'ERROR|Invalid format - expected request_id'
        
        _, request_id = parts
        
        cur = conn.cursor()
        
        # Get driver connection details and profile info
        cur.execute("""
            SELECT rr.accepted_driver_id, rr.driver_ip, rr.driver_port, 
                   p.first_name, p.last_name, rr.driver_p2p_status, rr.status
            FROM ride_requests rr
            LEFT JOIN profiles p ON rr.accepted_driver_id = p.user_id
            WHERE rr.request_id = ?
        """, (request_id,))
        
        result = cur.fetchone()
        
        if not result:
            return 'ERROR|Ride request not found'
        
        driver_id, driver_ip, driver_port, first_name, last_name, p2p_status, ride_status = result
        
        # Check if ride is accepted
        if ride_status != 'accepted':
            return f'ERROR|Ride not yet accepted (status: {ride_status})'
        
        # Check if connection info is available
        if not driver_ip or not driver_port:
            return 'ERROR|Driver connection info not yet available'
        
        # Build driver name
        driver_name = f'{first_name} {last_name}' if first_name and last_name else 'Driver'
        
        # Return connection info
        return f'SUCCESS|{driver_id}|{driver_ip}|{driver_port}|{driver_name}|{p2p_status or "pending"}'
        
    except Exception as e:
        print(f'❌ Error in handle_ride_get_driver_info: {e}')
        import traceback
        traceback.print_exc()
        return f'ERROR|Failed to get driver info: {str(e)}'