# Test the config
from config import Server_IP, Server_port
print(f"Config: {Server_IP}:{Server_port}")

# Test direct connection
import socket
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((Server_IP, Server_port))
    print("✅ Connection successful!")
    sock.close()
except Exception as e:
    print(f"❌ Connection failed: {e}")