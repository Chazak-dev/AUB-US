import socket
import threading
import sqlite3
import json
from datetime import datetime  
import sys
import os

print(f"Current directory: {os.getcwd()}")
print(f"Database exists: {os.path.exists('aubus.db')}")
 
# Add protocols directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
protocols_dir = os.path.join(current_dir, 'protocols')
sys.path.insert(0, protocols_dir)

sessions = {}
connection_sessions = {}

# Import protocol handlers
try:
    import validator
    from auth import handle_login, handle_logout, handle_register
    from Profile import handle_profile_create, handle_profile_get, handle_profile_photo_upload, handle_profile_update
    from driver import handle_driver_car_get, handle_driver_car_info_save, handle_driver_offline, handle_driver_online
    from driver import handle_driver_route_get, handle_driver_route_save, handle_driver_schedule_get, handle_driver_schedule_save
    from ride import handle_ride_already_taken, handle_ride_cancel_active, handle_ride_location_history
    from ride import handle_ride_location_latest, handle_ride_location_share, handle_ride_lock_acquire, handle_ride_lock_release
    from ride import handle_ride_request_accept, handle_ride_request_cancel, handle_ride_request_complete
    from ride import handle_ride_request_create, handle_ride_request_decline, handle_ride_request_expire
    from ride import handle_ride_request_notify_drivers, handle_ride_request_status, handle_ride_status_update
    from ride import handle_ride_requests_get_pending,handle_ride_get_driver_info
    from rating import handle_rating_get, handle_rating_history_get, handle_rating_submit
    from notifications import handle_notification_clear, handle_notification_read, handle_notification_send
    from data_retrieve import handle_active_rides_get, handle_driver_stats_get, handle_passenger_stats_get, handle_ride_history_get
    from realtime_availability import handle_active_drivers_get, handle_driver_availability_get, handle_driver_availability_set
    from emergency import handle_emergency_contact_add, handle_emergency_contact_get, handle_emergency_contact_remove
    from emergency import handle_emergency_resolve, handle_emergency_test_contact, handle_emergency_trigger
    print("✅ All protocol handlers imported successfully")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

def json_to_pipe(json_message):
    """Convert teammate's JSON message to pipe-separated format."""
    message_type = json_message.get('type', '')
    data = json_message.get('data', {})

    if message_type == "Register":
        username = data.get('username', '')
        email = data.get('email', '')
        password = data.get('password', '')
        name = data.get('name', '')
        area = data.get('area', '')
        is_driver = data.get('driver', False)
        return f"REGISTER|{username}|{email}|{password}|{name}|{name}|{area}|default.jpg|{1 if is_driver else 0}"

    elif message_type == "Login":
        return f"LOGIN|{data.get('username', '')}|{data.get('password', '')}"

    elif message_type == "Request for a ride":
        return f"RIDE_REQUEST_CREATE|{data.get('student_ID', '')}|{data.get('area', '')}|AUB|{data.get('time', '')}"

    elif message_type == "Accept the ride":
        acceptance_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return f"RIDE_REQUEST_ACCEPT|{data.get('driver_ID', '')}|{data.get('ride_ID', '')}|{acceptance_time}"

    elif message_type == "Submit rating":
        return f"RATING_SUBMIT|{data.get('request_id', '')}|{data.get('rater_id', '')}|{data.get('target_id', '')}|{data.get('target_role', '')}|{data.get('rating', '')}|{data.get('comment', '')}"

    else:
        return f"ERROR|Unknown JSON message type: {message_type}"

def pipe_to_json(pipe_response):
    """Convert pipe-formatted response back to JSON format."""
    if not pipe_response:
        return {"status": "error", "message": "Empty response"}

    parts = pipe_response.split("|")
    if parts[0] == "SUCCESS":
        return {"status": "success", "message": "|".join(parts[1:])}
    elif parts[0] == "ERROR":
        return {"status": "error", "message": "|".join(parts[1:])}
    else:
        if "SUCCESS" in pipe_response:
            return {"status": "success", "data": pipe_response}
        else:
            return {"status": "error", "message": pipe_response}

def process_command(command, conn, client_address=None):
    """Process pipe-formatted commands and return responses"""
    try:
        response = "ERROR|Unknown command"
        command_type = command.split("|")[0]
        user_id = connection_sessions.get(conn)
        
        # Authentication Protocols
        if command_type == "REGISTER":
            response = handle_register(command, conn, sessions, connection_sessions)
        elif command_type == "LOGIN":
            response = handle_login(command, conn, sessions, connection_sessions)
        elif command_type == "USER_LOGOUT":
            response = handle_logout(command, conn)
            
        # Profile Protocols
        elif command_type == "PROFILE_CREATE":
            response = handle_profile_create(command, conn)
        elif command_type == "PROFILE_UPDATE":
            response = handle_profile_update(command, conn)
        elif command_type == "PROFILE_GET":
            response = handle_profile_get(command, conn)
        elif command_type == "PROFILE_PHOTO_UPLOAD":
            response = handle_profile_photo_upload(command, conn)
            
        # Driver Protocols
        elif command_type == "DRIVER_ROUTE_SAVE":
            response = handle_driver_route_save(command, conn)
        elif command_type == "DRIVER_ONLINE":
            response = handle_driver_online(command, conn)
        elif command_type == "DRIVER_OFFLINE":
            response = handle_driver_offline(command, conn)
        elif command_type == "DRIVER_CAR_INFO":
            response = handle_driver_car_info_save(command, conn)
        elif command_type == "DRIVER_SCHEDULE":
            response = handle_driver_schedule_save(command, conn)
        elif command_type == "DRIVER_SCHEDULE_GET":
            response = handle_driver_schedule_get(command, conn)
        elif command_type == "DRIVER_ROUTE_GET":
            response = handle_driver_route_get(command, conn)
        elif command_type == "DRIVER_CAR_GET":
            response = handle_driver_car_get(command, conn)
                    
        # Ride Protocols
        elif command_type == "RIDE_REQUEST_CREATE":
            response = handle_ride_request_create(command, conn)
        elif command_type == "RIDE_REQUEST_NOTIFY_DRIVERS":
            response = handle_ride_request_notify_drivers(command, conn)
        elif command_type == "RIDE_REQUEST_ACCEPT":
            response = handle_ride_request_accept(command, conn, client_address)
        elif command_type == "RIDE_REQUEST_DECLINE":
            response = handle_ride_request_decline(command, conn)
        elif command_type == "RIDE_REQUEST_EXPIRE":
            response = handle_ride_request_expire(command, conn)
        elif command_type == "RIDE_REQUEST_CANCEL":
            response = handle_ride_request_cancel(command, conn)
        elif command_type == "RIDE_REQUEST_STATUS":
            response = handle_ride_request_status(command, conn)
        elif command_type == "RIDE_GET_DRIVER_INFO":
            response = handle_ride_get_driver_info(command, conn)
        elif command_type == "RIDE_REQUEST_COMPLETE":
            response = handle_ride_request_complete(command, conn)
        elif command_type == "RIDE_CANCEL_ACTIVE":
            response = handle_ride_cancel_active(command, conn)
        elif command_type == "RIDE_REQUESTS_GET_PENDING":
            response = handle_ride_requests_get_pending(command, conn)

        # Explicit locking
        elif command_type == "RIDE_LOCK_ACQUIRE":
            response = handle_ride_lock_acquire(command, conn)
        elif command_type == "RIDE_LOCK_RELEASE":
            response = handle_ride_lock_release(command, conn)
        elif command_type == "RIDE_ALREADY_TAKEN":
            response = handle_ride_already_taken(command, conn)

        # Ride tracking
        elif command_type == "RIDE_STATUS_UPDATE":
            response = handle_ride_status_update(command, conn)
        elif command_type == "RIDE_LOCATION_SHARE":
            response = handle_ride_location_share(command, conn)
        elif command_type == "RIDE_LOCATION_LATEST":
            response = handle_ride_location_latest(command, conn)
        elif command_type == "RIDE_LOCATION_HISTORY":
            response = handle_ride_location_history(command, conn)
            
        # Rating Protocols
        elif command_type == "RATING_SUBMIT":
            response = handle_rating_submit(command, conn)
        elif command_type == "RATING_GET":
            response = handle_rating_get(command, conn)
        elif command_type == "RATING_HISTORY_GET":
            response = handle_rating_history_get(command, conn)
            
        # Notification Protocols
        elif command_type == "NOTIFICATION_SEND":
            response = handle_notification_send(command, conn)
        elif command_type == "NOTIFICATION_READ":
            response = handle_notification_read(command, conn)
        elif command_type == "NOTIFICATION_CLEAR":
            response = handle_notification_clear(command, conn)

        # Data Retrieval Protocols
        elif command_type == "RIDE_HISTORY_GET":
            response = handle_ride_history_get(command, conn)
        elif command_type == "DRIVER_STATS_GET":
            response = handle_driver_stats_get(command, conn)
        elif command_type == "PASSENGER_STATS_GET":
            response = handle_passenger_stats_get(command, conn)
        elif command_type == "ACTIVE_RIDES_GET":
            response = handle_active_rides_get(command, conn)
            
        # Realtime Availability Protocols
        elif command_type == "DRIVER_AVAILABILITY_SET":
            response = handle_driver_availability_set(command, conn)
        elif command_type == "DRIVER_AVAILABILITY_GET":
            response = handle_driver_availability_get(command, conn)
        elif command_type == "ACTIVE_DRIVERS_GET":
            response = handle_active_drivers_get(command, conn)
            
        # Emergency Protocols
        elif command_type == "EMERGENCY_CONTACT_ADD":
            response = handle_emergency_contact_add(command, conn)
        elif command_type == "EMERGENCY_CONTACT_GET":
            response = handle_emergency_contact_get(command, conn)
        elif command_type == "EMERGENCY_CONTACT_REMOVE":
            response = handle_emergency_contact_remove(command, conn)
        elif command_type == "EMERGENCY_TEST_CONTACT":
            response = handle_emergency_test_contact(command, conn)
        elif command_type == "EMERGENCY_TRIGGER":
            response = handle_emergency_trigger(command, conn)
        elif command_type == "EMERGENCY_RESOLVE":
            response = handle_emergency_resolve(command, conn) 

        return response
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"ERROR|Server processing error: {str(e)}"

# Database connection
from config import DATABASE_PATH

print(f"Database path: {DATABASE_PATH}")
print(f"Database exists: {os.path.exists(DATABASE_PATH)}")

# Use check_same_thread=False for multi-threaded access
conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
cursor = conn.cursor()

HOST = 'localhost' 
PORT = 8888

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Allow port reuse
server.bind((HOST, PORT))
server.listen(10)

print(f"[LISTENING] Server is listening on {HOST}:{PORT}")

def handle_client(connection, address):
    print(f"[NEW CONNECTION] {address} connected.")
    try:
        while True:
            raw_message = connection.recv(1024)
            if not raw_message:
                break

            try:
                # Try to parse as JSON first (teammate's format)
                try:
                    json_message = json.loads(raw_message.decode("utf-8").strip())
                    print(f"[{address}] JSON: {json_message}")
                    
                    # Convert JSON to pipe format
                    pipe_command = json_to_pipe(json_message)
                    print(f"[{address}] Converted to pipe: {pipe_command}")
                    
                    # Process the command
                    pipe_response = process_command(pipe_command, conn, address)
                    print(f"[{address}] Pipe response: {pipe_response}")
                    
                    # Convert response back to JSON
                    json_response = pipe_to_json(pipe_response)
                    print(f"[{address}] JSON response: {json_response}")
                    
                    # Send JSON response
                    response_data = json.dumps(json_response).encode("utf-8")
                    
                except json.JSONDecodeError:
                    # Handle as pipe format (your original format)
                    pipe_command = raw_message.decode("utf-8").strip()
                    print(f"[{address}] PIPE: {pipe_command}")
                    
                    # Process the command directly
                    pipe_response = process_command(pipe_command, conn, address)
                    print(f"[{address}] Pipe response: {pipe_response}")
                    
                    # Send pipe response directly
                    if not isinstance(pipe_response, str):
                        pipe_response = str(pipe_response)

                    response_data = pipe_response.encode("utf-8")
                
                # Send the response
                try:
                    connection.send(response_data)
                except (BrokenPipeError, ConnectionResetError):
                    print(f"[SEND ERROR] {address} disconnected")
                    break
                    
            except Exception as e:
                error_msg = f"ERROR|Message processing error: {str(e)}"
                print(f"[PROCESSING ERROR] {address}: {e}")
                import traceback
                traceback.print_exc()
                try:
                    if raw_message.decode("utf-8").strip().startswith("{"):
                        json_error = {"status": "error", "message": str(e)}
                        connection.send(json.dumps(json_error).encode("utf-8"))
                    else:
                        connection.send(error_msg.encode("utf-8"))
                except:
                    pass

    except Exception as e:
        print(f"[CONNECTION ERROR] {address}: {e}")
    finally:
        print(f"[CLOSING CONNECTION] {address}")
        try:
            connection.close()
        except:
            pass

def start():
    print(f"[STARTING] Server started on {HOST}:{PORT}")
    print("[INFO] Server now supports both JSON and pipe protocols")
    while True:
        try:
            connection, address = server.accept()
            thread = threading.Thread(target=handle_client, args=(connection, address))
            thread.daemon = True
            thread.start()
            print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")
        except Exception as e:
            print(f"[ACCEPT ERROR] {e}")

if __name__ == "__main__":
    try:
        start()
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Server shutting down...")
    finally:
        server.close()
        if conn:
            conn.close()