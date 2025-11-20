import socket
import sys
import threading

clients = {} # conn -> username 
rooms = {} #room_name - > set of conns
lock = threading.Lock()

def broadcast(room, message, exclude=None):
    """Send a message to all in given room"""
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
        clients.pop(conn, None)
        for r in rooms.values():
            r.discard(conn)
    try:
        conn.close()
    except:
        pass
def handle_command(conn, line):
    """Parse a line and execute commands."""
    parts = line.strip().split()
    if not parts:
        return
    cmd, *args = parts
    cmd = cmd.upper()
    
# this is for when you connect to the server to give you a username
#but not let you change in the actual room"""
    if cmd == "USERNAME" and args:
        desired = args[0]
        with lock:
            if clients.get(conn) is None:
                clients[conn] = desired
                try:
                    conn.sendall(f"[Server] Welcome {desired}!\n".encode())
                except:
                    pass
            else:
                conn.sendall(b"[Server] Unknown or invalid command.\n")
        return
# Join command
    if cmd == "JOIN" and args:
        room = args[0]
        with lock:
            rooms.setdefault(room, set()).add(conn)
            uname = clients.get(conn) or "User"
        broadcast(room, f"[Server] {uname} joined {room}")
        return
# Leave command
    if cmd == "LEAVE" and args:
        room = args[0]
        with lock:
            if room in rooms and conn in rooms[room]:
                rooms[room].remove(conn)
            uname = clients.get(conn) or "User"
        broadcast(room, f"[Server] {uname} left {room}")
        return
# message command
    if cmd == "MSG" and len(args) >= 2:
        room = args[0]
        msg = " ".join(args[1:])
        with lock:
            uname = clients.get(conn) or "User"
        broadcast(room, f"[{room}] {uname}: {msg}", exclude=conn)
        return
# who command
    if cmd == "WHO" and args:
        room = args[0]
        with lock:
            members = [clients.get(c) or "User" for c in rooms.get(room, set())]
        conn.sendall(f"[Server] Users in {room}: {', '.join(members)}\n".encode())
        return

    conn.sendall(b"[Server] Unknown or invalid command.\n")
# handles what the client wants to do
def handle_client(conn, addr):
    print(f"[+] Connected by {addr}")
    with lock:
        clients[conn] = None

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
# the actual connection
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
