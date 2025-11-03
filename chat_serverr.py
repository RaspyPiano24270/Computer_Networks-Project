import socket
import sys
import threading
clients = {}   # conn -> username
rooms = {}     # room_name -> set of conns
lock = threading.Lock()

def broadcast(message, sender_conn):
    """Send a message to all clients except the sender."""
    for client in clients:
        if client != sender_conn:
            try:
                client.sendall(message.encode())
            except:
                clients.remove(client)

def broadcast(room, message, exclude=None):
    """Send message to everyone in a given room except the sender."""
    with lock:
        for c in list(rooms.get(room, set())):
            if c != exclude:
                try:
                    c.sendall((message + "\n").encode())
                except:
                    rooms[room].discard(c)

def disconnect_client(conn):
    """Remove a client from all rooms and the clients list."""
    with lock:
        username = clients.pop(conn, None)
        for r in rooms.values():
            r.discard(conn)
    conn.close()

def handle_command(conn, line):
    """Parse a line and execute commands."""
    parts = line.strip().split()
    if not parts:
        return
    cmd, *args = parts

    if cmd.upper() == "USERNAME" and args:
        with lock:
            clients[conn] = args[0]
        conn.sendall(f"[Server] Welcome {args[0]}!\n".encode())

    elif cmd.upper() == "JOIN" and args:
        room = args[0]
        with lock:
            rooms.setdefault(room, set()).add(conn)
        broadcast(room, f"[Server] {clients.get(conn,'?')} joined {room}")

    elif cmd.upper() == "LEAVE" and args:
        room = args[0]
        with lock:
            if room in rooms and conn in rooms[room]:
                rooms[room].remove(conn)
        broadcast(room, f"[Server] {clients.get(conn,'?')} left {room}")

    elif cmd.upper() == "MSG" and len(args) >= 2:
        room = args[0]
        msg = " ".join(args[1:])
        broadcast(room, f"[{room}] {clients.get(conn,'?')}: {msg}", exclude=conn)

    elif cmd.upper() == "WHO" and args:
        room = args[0]
        with lock:
            members = [clients.get(c,'?') for c in rooms.get(room,set()) if c in clients]
        conn.sendall(f"[Server] Users in {room}: {', '.join(members)}\n".encode())
        
    elif cmd.upper() == "HELP":
        help_text = (
            "Available commands:\n"
            "USERNAME <name> - set your username\n"
            "JOIN <room> - join a chat room\n"
            "LEAVE <room> - leave a chat room\n"
            "MSG <room> <message> - send a message to a room\n"
            "WHO <room> - list users in a room\n"
            "ROOMS - list active rooms and sizes\n"
            "HELP - show this help message\n"
            "QUIT - disconnect\n"
        )
        conn.sendall(help_text.encode())

    elif cmd.upper() == "QUIT":
        conn.sendall(b"[Server] Goodbye!\n")
        disconnect_client(conn)
        return

    elif cmd.upper() == "ROOMS":
        with lock:
            info = [f"{r} ({len(s)})" for r, s in rooms.items()]
        conn.sendall(f"[Server] Active rooms: {', '.join(info)}\n".encode())

    else:
        conn.sendall(b"[Server] Unknown or invalid command.\n")

def handle_client(conn, addr):
    print(f"[+] Connected by {addr}")
    with lock:
        clients[conn] = None  # placeholder until USERNAME command

    try:
        while True:
            data = conn.recv(1024).decode()
            if not data:
                break
            for line in data.strip().splitlines():
                handle_command(conn, line)
    except ConnectionResetError:
        pass
    finally:
        disconnect_client(conn)
        print(f"[-] Disconnected {addr}")

def main():
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <listen_port>")
        sys.exit(1)

    host = "0.0.0.0"
    port = int(sys.argv[1])

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(5)

    print(f"[*] Server listening on {host}:{port}")

    while True:
        conn, addr = server_socket.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    main()

