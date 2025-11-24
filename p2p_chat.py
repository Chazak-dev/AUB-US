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
        self.connection_lock = threading.Lock()

    def start_chat_server(self, port=9000):
        """Start P2P server to accept connections"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # If port is 0, let OS assign random port
            if port == 0:
                self.server_socket.bind(('0.0.0.0', 0))
                self.server_port = self.server_socket.getsockname()[1]
            else:
                self.server_socket.bind(('0.0.0.0', port))
                self.server_port = port
                
            self.server_socket.listen(5)
            self.server_socket.settimeout(1.0)
            self.listening = True

            print(f"✅ P2P Chat server listening on port {self.server_port}")

            thread = threading.Thread(target=self._accept_connections, daemon=True)
            thread.start()
            return True

        except Exception as e:
            print(f"❌ Failed to start chat server: {e}")
            return False

    def _accept_connections(self):
        """Accept incoming P2P connections"""
        while self.listening:
            try:
                conn, addr = self.server_socket.accept()
                print(f"✅ P2P connection from {addr}")
                
                with self.connection_lock:
                    self.peer_connection = conn
                    self.connected_to_peer = True
                
                # Start receiving messages
                self.receive_thread = threading.Thread(
                    target=self._receive_messages, 
                    args=(conn,), 
                    daemon=True
                )
                self.receive_thread.start()
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.listening:
                    print(f"❌ Connection acceptance error: {e}")
                break

    def _receive_messages(self, connection):
        """Receive messages from peer"""
        buffer = ""
        
        while self.connected_to_peer and self.listening:
            try:
                data = connection.recv(4096).decode('utf-8')
                if not data:
                    print("❌ Peer disconnected")
                    self.connected_to_peer = False
                    break
                
                buffer += data
                
                # Process complete JSON messages
                while '{' in buffer and '}' in buffer:
                    start = buffer.find('{')
                    end = buffer.find('}', start) + 1
                    
                    if start != -1 and end > start:
                        message_str = buffer[start:end]
                        buffer = buffer[end:]
                        
                        try:
                            message = json.loads(message_str)
                            self._handle_chat_message(message)
                        except json.JSONDecodeError as e:
                            print(f"❌ JSON decode error: {e}")
                            
            except ConnectionResetError:
                print("❌ Peer connection reset")
                self.connected_to_peer = False
                break
            except Exception as e:
                if self.connected_to_peer:
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
        """Handle received chat message"""
        message_type = message.get('type')
        sender = message.get('student', message.get('driver', 'Unknown'))
        timestamp = message.get('time', 'now')

        if message_type == "chat_message":
            text = message.get('text', '')
            print(f"📨 {sender}: {text}")

            if self.message_received_callback:
                self.message_received_callback(sender, text, timestamp)

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
                
            print(f"🖼️ {student} sent an image: {file_name}")
            
            if self.message_received_callback:
                self.message_received_callback(student, f"[Image: {file_name}]", message.get('time', 'now'))
            
        except Exception as e:
            print(f"❌ Failed to process image: {e}")

    def _handle_received_audio(self, message):
        try:
            student = message.get('student', 'Unknown')
            file_name = message.get('file_name', 'received_audio.wav')
            audio_data = message.get('audio_data', '')
            
            audio_bytes = base64.b64decode(audio_data)
            with open(file_name, 'wb') as f:
                f.write(audio_bytes)
                
            print(f"🎵 {student} sent audio: {file_name}")
            
            if self.message_received_callback:
                self.message_received_callback(student, f"[Voice: {file_name}]", message.get('time', 'now'))
            
        except Exception as e:
            print(f"❌ Failed to process audio: {e}")

    def _handle_received_location(self, message):
        student = message.get('student', 'Unknown')
        lat = message.get('latitude')
        lon = message.get('longitude')
        
        print(f"📍 {student} shared location: {lat}, {lon}")
        
        if self.message_received_callback:
            self.message_received_callback(student, f"[Location: {lat}, {lon}]", message.get('time', 'now'))

    def connect_to_peer(self, peer_IP, peer_port):
        """Connect to peer as client"""
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(5.0)
            self.client_socket.connect((peer_IP, peer_port))
            self.client_socket.settimeout(None)
            
            with self.connection_lock:
                self.connected_to_peer = True
            
            # Start receiving from this connection
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
        """Send chat message to peer"""
        if not self.connected_to_peer:
            print("❌ Not connected to peer")
            return False

        try:
            message = {
                "type": "chat_message",
                "student": student_name,
                "text": text,
                "time": "now",
            }

            json_message = json.dumps(message)
            
            # Send via client socket or peer connection
            with self.connection_lock:
                if self.client_socket:
                    self.client_socket.send(json_message.encode('utf-8'))
                elif self.peer_connection:
                    self.peer_connection.send(json_message.encode('utf-8'))
                else:
                    print("❌ No active connection")
                    return False
                    
            print(f"✅ Sent: {text}")
            return True

        except Exception as e:
            print(f"❌ Failed to send message: {e}")
            self.connected_to_peer = False 
            return False

    def send_location(self, latitude, longitude, student_name):
        """Send location to peer"""
        if not self.connected_to_peer:
            print("❌ Not connected to peer")
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
            
            with self.connection_lock:
                if self.client_socket:
                    self.client_socket.send(json_message.encode('utf-8'))
                elif self.peer_connection:
                    self.peer_connection.send(json_message.encode('utf-8'))
                    
            print(f"✅ Sent location: {latitude}, {longitude}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send location: {e}")
            return False

    def end_chat(self):
        """Clean shutdown of P2P chat"""
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
        
        # Close peer connection
        if self.peer_connection:
            try:
                self.peer_connection.close()
            except:
                pass
            self.peer_connection = None
        
        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
            self.server_socket = None
        
        print("✅ Chat ended cleanly")

    def set_message_received_callback(self, callback):
        """Set callback for received messages"""
        self.message_received_callback = callback
        print("✅ Message callback set")
