import socket
import sys
import threading

clients = {}  # addr (ip,port) -> username
rooms = {}    # room_name -> set of addr
lock = threading.Lock()

def broadcast(room, message, exclude=None):
    """Send a message to all clients in a room, except exclude."""
    with lock:
        for addr in list(rooms.get(room, set())):
            if addr != exclude:
                try:
                    server_sock.sendto((message + "\n").encode(), addr)
                except:
                    rooms[room].discard(addr)

def disconnect_client(addr):
    """Remove client from all rooms and clients dict."""
    with lock:
        clients.pop(addr, None)
        for r in rooms.values():
            r.discard(addr)

def handle_command(data, addr):
    parts = data.strip().split()
    if not parts:
        return
    cmd, *args = parts
    cmd = cmd.upper()

    if cmd == "USERNAME" and args:
        desired = args[0]
        with lock:
            if addr not in clients:
                clients[addr] = desired
                try:
                    server_sock.sendto(f"[Server] Welcome {desired}!\n".encode(), addr)
                except:
                    pass
            else:
                server_sock.sendto(b"[Server] Unknown or invalid command.\n", addr)
        return

    if cmd == "JOIN" and args:
        room = args[0]
        with lock:
            rooms.setdefault(room, set()).add(addr)
            uname = clients.get(addr, "User")
        broadcast(room, f"[Server] {uname} joined {room}")
        return

    if cmd == "LEAVE" and args:
        room = args[0]
        with lock:
            if room in rooms and addr in rooms[room]:
                rooms[room].remove(addr)
            uname = clients.get(addr, "User")
        broadcast(room, f"[Server] {uname} left {room}")
        return

    if cmd == "ROOMS":
        with lock:
            info = [room for room in rooms.keys()]
        server_sock.sendto(f"[Server] Active rooms: {', '.join(info)}\n".encode(), addr)
        return

    if cmd == "MSG" and len(args) >= 2:
        room = args[0]
        msg = " ".join(args[1:])
        with lock:
            uname = clients.get(addr, "User")
        broadcast(room, f"[{room}] {uname}: {msg}", exclude=addr)
        return

    if cmd == "WHO" and args:
        room = args[0]
        with lock:
            members = [clients.get(c, "User") for c in rooms.get(room, set())]
        server_sock.sendto(f"[Server] Users in {room}: {', '.join(members)}\n".encode(), addr)
        return

    server_sock.sendto(b"[Server] Unknown or invalid command.\n", addr)

def server_loop():
a    while True:
        try:
            data, addr = server_sock.recvfrom(4096)
            if not data:
                disconnect_client(addr)
                continue
            handle_command(data.decode(), addr)
        except Exception as e:
            print(f"[Server] Error: {e}")

def main():
    global server_sock
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <listen_port>")
        sys.exit(1)

    port = int(sys.argv[1])
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_sock.bind(("0.0.0.0", port))

    print(f"[*] UDP Server listening on 0.0.0.0:{port}")

    server_loop()

if __name__ == "__main__":
    main()
