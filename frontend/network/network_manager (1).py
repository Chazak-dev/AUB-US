import socket
import json
import threading

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

from config import Server_IP, Server_port

class NetworkManager:
    def __init__(self):
        self.socket = None
        self.connected = False

    def connect_to_server(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  
            self.socket.connect((Server_IP, Server_port))
            self.connected = True
            print("Connected to AUBus server")
            self._start_listening()  
            return True
        except Exception as e:
            print("Connection failed:", e)  
            return False

    def _start_listening(self):  
        def listen_thread():
            while self.connected:
                try:
                    data = self.socket.recv(1024).decode('utf-8')
                    if data:
                        message = json.loads(data)
                        self._handle_message(message)  
                except json.JSONDecodeError as e:
                    print("JSON error:", e)  
                except:
                    break
        thread = threading.Thread(target=listen_thread)
        thread.daemon = True
        thread.start()  
    
    def _handle_message(self, message):  
        print("Server says:", message)  
    
    def send_message(self, message_dict):
        if not self.connected:
            print("Not connected to server") 
            return False

        try:
            json_message = json.dumps(message_dict) 
            self.socket.send(json_message.encode('utf-8'))  
            print("Message sent:", message_dict['type'])  
            return True
        except Exception as e:  
            print("Send failed:", e)  
            self.connected = False
            return False
    
    def disconnect(self):
        self.connected = False
        if self.socket:
            self.socket.close()
        print("Disconnected from server")