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
        self.message_received_callback = None 
        self.receive_thread = None

    def start_chat_server(self, port=9000):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('0.0.0.0', port))
            self.server_socket.listen(5)
            self.server_socket.settimeout(1.0)  # Add timeout to allow clean shutdown
            self.server_port = port
            self.listening = True

            print(f"✅ P2P Chat server listening on port {port}")

            thread = threading.Thread(target=self._accept_connections, daemon=True)
            thread.start()
            return True

        except Exception as e:
            print(f"❌ Failed to start chat server: {e}")
            return False

    def _accept_connections(self):
        while self.listening:
            try:
                conn, addr = self.server_socket.accept()
                print(f"✅ P2P connected to {addr}")
                self.peer_connection = conn
                self.connected_to_peer = True
                
                # Start receiving messages from this connection
                self.receive_thread = threading.Thread(
                    target=self._receive_messages, 
                    args=(conn,), 
                    daemon=True
                )
                self.receive_thread.start()
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.listening:  # Only print errors if we're supposed to be listening
                    print(f"❌ Connection acceptance error: {e}")
                break

    def _receive_messages(self, connection):
        """Receive messages from a specific connection"""
        while self.connected_to_peer and self.listening:
            try:
                data = connection.recv(4096).decode('utf-8')
                if not data:
                    print("❌ Peer disconnected")
                    self.connected_to_peer = False
                    break
                
                # Handle multiple JSON messages in case they get concatenated
                messages = data.split('}{')
                if len(messages) > 1:
                    # Reconstruct proper JSON
                    messages = [messages[0] + '}'] + ['{' + msg for msg in messages[1:-1]] + ['{' + messages[-1]]
                else:
                    messages = [data]
                
                for message_data in messages:
                    try:
                        message = json.loads(message_data)
                        self._handle_chat_message(message)
                    except json.JSONDecodeError:
                        print(f"❌ Invalid JSON received: {message_data}")
                        
            except ConnectionResetError:
                print("❌ Peer connection reset")
                self.connected_to_peer = False
                break
            except Exception as e:
                if self.connected_to_peer:  # Only log errors if we think we're connected
                    print(f"❌ Message receive error: {e}")
                break
        
        # Cleanup
        try:
            connection.close()
        except:
            pass
        
        self.connected_to_peer = False
        print("✅ Message receiving stopped")

    def _handle_chat_message(self, message):
        message_type = message.get('type')
        sender = message.get('student', 'Unknown')
        timestamp = message.get('time', 'now')

        if message_type == "chat_message":
            text = message.get('text', '')
            print(f"📨 {sender}: {text}")

            # Call UI callback if set
            if self.message_received_callback:
                self.message_received_callback(sender, text, timestamp)

        elif message_type == "image_message":
            self._handle_received_image(message)
            
        elif message_type == "voice_message":
            self._handle_received_audio(message)
            
        elif message_type == "location_message":
            self._handle_received_location(message)
        else:
            print(f"❓ Unknown message type: {message_type}")

    def _handle_received_image(self, message):
        try:
            student = message.get('student', 'Unknown')
            file_name = message.get('file_name', 'received_image.png')
            image_data = message.get('image_data', '')
            
            image_bytes = base64.b64decode(image_data)
            with open(file_name, 'wb') as f:
                f.write(image_bytes)
                
            print(f"🖼️ {student} sent an image: {file_name}")
            
            # Notify UI if callback is set
            if self.message_received_callback:
                self.message_received_callback(student, f"[Image: {file_name}]", message.get('time', 'now'))
            
        except Exception as e:
            print(f"❌ Failed to process received image: {e}")

    def _handle_received_audio(self, message):
        try:
            student = message.get('student', 'Unknown')
            file_name = message.get('file_name', 'received_audio.wav')
            audio_data = message.get('audio_data', '')
            
            audio_bytes = base64.b64decode(audio_data)
            with open(file_name, 'wb') as f:
                f.write(audio_bytes)
                
            print(f"🎵 {student} sent a voice message: {file_name}")
            
            # Notify UI if callback is set
            if self.message_received_callback:
                self.message_received_callback(student, f"[Voice Message: {file_name}]", message.get('time', 'now'))
            
        except Exception as e:
            print(f"❌ Failed to process received audio: {e}")

    def _handle_received_location(self, message):
        student = message.get('student', 'Unknown')
        lat = message.get('latitude')
        lon = message.get('longitude')
        
        print(f"📍 {student} shared location: {lat}, {lon}")
        
        # Notify UI if callback is set
        if self.message_received_callback:
            self.message_received_callback(student, f"[Location: {lat}, {lon}]", message.get('time', 'now'))

    def connect_to_peer(self, peer_IP, peer_port):
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(5.0)  # 5 second timeout for connection
            self.client_socket.connect((peer_IP, peer_port))
            self.client_socket.settimeout(None)  # Remove timeout after connection
            self.connected_to_peer = True
            
            # Start receiving messages from this connection
            self.receive_thread = threading.Thread(
                target=self._receive_messages, 
                args=(self.client_socket,), 
                daemon=True
            )
            self.receive_thread.start()
            
            print(f"✅ Connected to peer at {peer_IP}:{peer_port}")
            return True

        except socket.timeout:
            print(f"❌ Connection timeout to {peer_IP}:{peer_port}")
            return False
        except Exception as e:
            print(f"❌ Failed to connect to peer: {e}")
            return False

    def send_chat_message(self, text, student_name):
        if not self.connected_to_peer or not self.client_socket:
            print("❌ Not connected to any peer")
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
            print(f"✅ You: {text}")
            return True

        except Exception as e:
            print(f"❌ Failed to send message: {e}")
            self.connected_to_peer = False 
            return False

    def send_image(self, image_path, student_name):
        if not self.connected_to_peer:
            print("❌ Not connected to any peer")
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
            print(f"✅ You sent an image: {file_name}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send image: {e}")
            return False

    def send_voice_message(self, audio_path, student_name):
        if not self.connected_to_peer:
            print("❌ Not connected to any peer")
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
            print(f"✅ You sent a voice message: {file_name}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send voice message: {e}")
            return False

    def send_location(self, latitude, longitude, student_name):
        if not self.connected_to_peer:
            print("❌ Not connected to any peer")
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
            print(f"✅ You shared location: {latitude}, {longitude}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send location: {e}")
            return False

    def end_chat(self):
        print("🛑 Ending chat...")
        self.listening = False
        self.connected_to_peer = False
        
        # Close client socket
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
            self.client_socket = None
        
        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
            self.server_socket = None
        
        print("✅ Chat ended cleanly")

    def set_message_received_callback(self, callback):
        """Set callback function to handle received messages in UI"""
        self.message_received_callback = callback
        print("✅ Message callback set")