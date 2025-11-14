import socket
import threading
import json
import base64
import os
from config import Server_IP

class P2PChat:
    def __init__(self):
        self.server_port = None
        self.client_socket = None
        self.server_socket = None
        self.listening = False
        self.connected_to_peer = False
        self.peer_connection = None

    def start_chat_server(self, port=9000):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.bind((Server_IP, port))
            self.server_socket.listen()
            self.server_port = port
            self.listening = True

            print("P2P Chat server listening on port", port)

            thread = threading.Thread(target=self._accept_connections, daemon=True)
            thread.start()
            return True

        except Exception as e:
            print("Failed to start chat server:", e)
            return False

    def _accept_connections(self):
        while self.listening:
            try:
                conn, addr = self.server_socket.accept()
                print("P2P connected to", addr)
                self._handle_chat_connection(conn)

            except:
                break

    def _handle_chat_connection(self, connection):
        self.connected_to_peer = True
        self.peer_connection = connection

        while self.connected_to_peer:
            try:
                data = connection.recv(1024).decode('utf-8')
                if data:
                    message = json.loads(data)
                    self._handle_chat_message(message)

            except:
                break

        connection.close()

    def _handle_chat_message(self, message):
        message_type = message.get('type')
        
        if message_type == "chat_message":
            print(message.get('student', 'Unknown') + ":", message.get('text',''))
            
        elif message_type == "image_message":
            self._handle_received_image(message)
            
        elif message_type == "voice_message":
            self._handle_received_audio(message)
            
        elif message_type == "location_message":
            self._handle_received_location(message)

    def _handle_received_image(self, message):
        try:
            student = message.get('student', 'Unknown')
            file_name = message.get('file_name', 'received_image.png')
            image_data = message.get('image_data', '')
            
            image_bytes = base64.b64decode(image_data)
            with open(file_name, 'wb') as f:
                f.write(image_bytes)
                
            print(student, "sent an image:", file_name, "(saved to current directory)")
            
        except Exception as e:
            print("Failed to process received image:", e)

    def _handle_received_audio(self, message):
        try:
            student = message.get('student', 'Unknown')
            file_name = message.get('file_name', 'received_audio.wav')
            audio_data = message.get('audio_data', '')
            
            audio_bytes = base64.b64decode(audio_data)
            with open(file_name, 'wb') as f:
                f.write(audio_bytes)
                
            print(student, "sent a voice message:", file_name, "(saved to current directory)")
            
        except Exception as e:
            print("Failed to process received audio:", e)

    def _handle_received_location(self, message):
        student = message.get('student', 'Unknown')
        lat = message.get('latitude')
        lon = message.get('longitude')
        
        print(student, "shared location:", lat, ",", lon)

    def connect_to_peer(self, peer_IP, peer_port):
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((peer_IP, peer_port))
            self.connected_to_peer = True
            print("Connected to peer at", peer_IP + ":" + str(peer_port))
            return True

        except Exception as e:
            print("Failed to connect to peer:", e)
            return False

    def send_chat_message(self, text, student_name):
        if not self.connected_to_peer:
            print("Not connected to any peer")
            return False

        try:
            message = {
                "type": "chat_message",
                "student": student_name,
                "text": text,
                "time": "now",
            }

            json_message = json.dumps(message)
            self.client_socket.send(json_message.encode('utf-8'))
            print("You:", text)
            return True

        except Exception as e:
            print("Failed to send message:", e)
            self.connected_to_peer = False 
            return False

    def send_image(self, image_path, student_name):
        if not self.connected_to_peer:
            print("Not connected to any peer")
            return False
            
        try:
            with open(image_path, 'rb') as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
            
            file_name = os.path.basename(image_path)
            
            message = {
                "type": "image_message",
                "student": student_name,
                "file_name": file_name,
                "image_data": image_data,
                "time": "now"
            }
            
            json_message = json.dumps(message)
            self.client_socket.send(json_message.encode('utf-8'))
            print("You sent an image:", file_name)
            return True
            
        except Exception as e:
            print("Failed to send image:", e)
            return False

    def send_voice_message(self, audio_path, student_name):
        if not self.connected_to_peer:
            print("Not connected to any peer")
            return False
            
        try:
            with open(audio_path, 'rb') as audio_file:
                audio_data = base64.b64encode(audio_file.read()).decode('utf-8')
            
            file_name = os.path.basename(audio_path)
            
            message = {
                "type": "voice_message", 
                "student": student_name,
                "file_name": file_name,
                "audio_data": audio_data,
                "time": "now"
            }
            
            json_message = json.dumps(message)
            self.client_socket.send(json_message.encode('utf-8'))
            print("You sent a voice message:", file_name)
            return True
            
        except Exception as e:
            print("Failed to send voice message:", e)
            return False

    def send_location(self, latitude, longitude, student_name):
        if not self.connected_to_peer:
            print("Not connected to any peer")
            return False
            
        try:
            message = {
                "type": "location_message",
                "student": student_name,
                "latitude": latitude,
                "longitude": longitude,
                "time": "now"
            }
            
            json_message = json.dumps(message)
            self.client_socket.send(json_message.encode('utf-8'))
            print("You shared location:", latitude, ",", longitude)
            return True
            
        except Exception as e:
            print("Failed to send location:", e)
            return False

    def end_chat(self):
        self.listening = False
        self.connected_to_peer = False
        if self.client_socket:
            self.client_socket.close()
        if self.server_socket:
            self.server_socket.close()
        print("Chat ended")