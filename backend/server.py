import socket
import threading
import sqlite3
import json
from datetime import datetime  
from protocols.validator import validator 

from protocols.auth import handle_register, handle_login, handle_logout
from protocols.profile import handle_profile_create,handle_profile_update,handle_profile_get,handle_profile_photo_upload
from protocols.driver import handle_driver_offline,handle_driver_car_info_save,handle_driver_online,handle_driver_route_save,handle_driver_schedule_save
from protocols.ride import ( handle_ride_request_create, handle_ride_request_notify_drivers, handle_ride_request_accept,handle_ride_request_decline, handle_ride_request_status, 
                            handle_ride_request_complete,handle_ride_cancel_active, handle_ride_lock_acquire, handle_ride_lock_release,handle_ride_already_taken, 
                            handle_ride_status_update, handle_ride_location_share, handle_ride_location_latest, handle_ride_location_history,handle_ride_request_cancel,handle_ride_request_expire)
from protocols.chat_and_communications import(handle_chat_message_send, handle_chat_message_receive,handle_chat_media_send, handle_chat_status_update)
from protocols.rating import(handle_rating_get,handle_rating_history_get,handle_rating_submit)
from protocols.notifications import(handle_notification_send,handle_notification_read,handle_notification_clear)
from protocols.data_retrieve import (handle_ride_history_get,handle_driver_stats_get,handle_passenger_stats_get,handle_active_rides_get)

from protocols.realtime_availability import (handle_driver_availability_set,handle_driver_availability_get,handle_active_drivers_get,)


def json_to_pipe(json_message):
    """
    Convert teammate's JSON message to your pipe-separated format.
    """
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
    """
    Convert your pipe-formatted response back to JSON format for teammates.
    """
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

def process_command(command, conn):
    """
    Process pipe-formatted commands and return responses
    """
    try:
        response = "ERROR|Unknown command"
        command_type = command.split("|")[0]

        # --- Authentication Protocols ---
        if command_type == "REGISTER":
            response = handle_register(command, conn)
        elif command_type == "LOGIN":
            response = handle_login(command, conn)
        elif command_type == "USER_LOGOUT":
            response = handle_logout(command, conn)
            
        # --- Profile Protocols ---
        elif command_type == "PROFILE_CREATE":
            response = handle_profile_create(command, conn)
        elif command_type == "PROFILE_UPDATE":
            response = handle_profile_update(command, conn)
        elif command_type == "PROFILE_GET":
            response = handle_profile_get(command, conn)
        elif command_type == "PROFILE_PHOTO_UPLOAD":
            response = handle_profile_photo_upload(command, conn)
            
        # --- Driver Protocols ---                
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
            
        # --- Ride Protocols ---
        elif command_type == "RIDE_REQUEST_CREATE":
            response = handle_ride_request_create(command, conn)
        elif command_type == "RIDE_REQUEST_NOTIFY_DRIVERS":
            response = handle_ride_request_notify_drivers(command, conn)
        elif command_type == "RIDE_REQUEST_ACCEPT":
            response = handle_ride_request_accept(command, conn)
        elif command_type == "RIDE_REQUEST_DECLINE":
            response = handle_ride_request_decline(command, conn)
        elif command_type == "RIDE_REQUEST_EXPIRE":
            response = handle_ride_request_expire(command, conn)
        elif command_type == "RIDE_REQUEST_CANCEL":
            response = handle_ride_request_cancel(command, conn)
        elif command_type == "RIDE_REQUEST_STATUS":
            response = handle_ride_request_status(command, conn)
        elif command_type == "RIDE_REQUEST_COMPLETE":
            response = handle_ride_request_complete(command, conn)
        elif command_type == "RIDE_CANCEL_ACTIVE":
            response = handle_ride_cancel_active(command, conn)

        # --- Explicit locking ---
        elif command_type == "RIDE_LOCK_ACQUIRE":
            response = handle_ride_lock_acquire(command, conn)
        elif command_type == "RIDE_LOCK_RELEASE":
            response = handle_ride_lock_release(command, conn)
        elif command_type == "RIDE_ALREADY_TAKEN":
            response = handle_ride_already_taken(command, conn)

        # --- Ride tracking ---
        elif command_type == "RIDE_STATUS_UPDATE":
            response = handle_ride_status_update(command, conn)
        elif command_type == "RIDE_LOCATION_SHARE":
            response = handle_ride_location_share(command, conn)
        elif command_type == "RIDE_LOCATION_LATEST":
            response = handle_ride_location_latest(command, conn)
        elif command_type == "RIDE_LOCATION_HISTORY":
            response = handle_ride_location_history(command, conn)
            
        # --- Chat and Communication ---
        elif command_type == "CHAT_MESSAGE_SEND":
            response = handle_chat_message_send(command, conn)
        elif command_type == "CHAT_MESSAGE_RECEIVE":
            response = handle_chat_message_receive(command, conn)
        elif command_type == "CHAT_MEDIA_SEND":
            response = handle_chat_media_send(command, conn)
        elif command_type == "CHAT_STATUS_UPDATE":
            response = handle_chat_status_update(command, conn)
            
        # --- Rating Protocols ---
        elif command_type == "RATING_SUBMIT":
            response = handle_rating_submit(command, conn)
        elif command_type == "RATING_GET":
            response = handle_rating_get(command, conn)
        elif command_type == "RATING_HISTORY_GET":
            response = handle_rating_history_get(command, conn)
            
        # --- Notification Protocols ---
        elif command_type == "NOTIFICATION_SEND":
            response = handle_notification_send(command, conn)
        elif command_type == "NOTIFICATION_READ":
            response = handle_notification_read(command, conn)
        elif command_type == "NOTIFICATION_CLEAR":
            response = handle_notification_clear(command, conn)

        # --- Data Retrieval Protocols ---
        elif command_type == "RIDE_HISTORY_GET":
            response = handle_ride_history_get(command, conn)
        elif command_type == "DRIVER_STATS_GET":
            response = handle_driver_stats_get(command, conn)
        elif command_type == "PASSENGER_STATS_GET":
            response = handle_passenger_stats_get(command, conn)
        elif command_type == "ACTIVE_RIDES_GET":
            response = handle_active_rides_get(command, conn)
            
        # --- Realtime Availability Protocols ---
        elif command_type == "DRIVER_AVAILABILITY_SET":
            response = handle_driver_availability_set(command, conn)
        elif command_type == "DRIVER_AVAILABILITY_GET":
            response = handle_driver_availability_get(command, conn)
        elif command_type == "ACTIVE_DRIVERS_GET":
            response = handle_active_drivers_get(command, conn)

        return response
        
    except Exception as e:
        return f"ERROR|Server processing error: {str(e)}"

# check_same_thread=False allows multiple threads to use the same connection
conn = sqlite3.connect("C:/Users/itsch/Desktop/aubus.db", check_same_thread=False)
cursor = conn.cursor()

HOST = 'localhost' 
PORT = 8888

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
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
                    pipe_response = process_command(pipe_command, conn)
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
                    pipe_response = process_command(pipe_command, conn)
                    print(f"[{address}] Pipe response: {pipe_response}")
                    
                    # Send pipe response directly
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
                try:
                    # Try to send error in appropriate format
                    if raw_message.decode("utf-8").strip().startswith("{"):
                        # JSON error
                        json_error = {"status": "error", "message": str(e)}
                        connection.send(json.dumps(json_error).encode("utf-8"))
                    else:
                        # Pipe error
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