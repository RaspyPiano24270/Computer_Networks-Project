import socket
import sys
import threading

clients = {}   # addr (ip,port) -> username
rooms = {}     # room_name -> set of addr
lock = threading.Lock()

def broadcast(room, message, exclude=None):
    with lock:
        for addr in list(rooms.get(room, set())):
            if addr != exclude:
                try:
                    server_sock.sendto((message + "\n").encode(), addr)
                except:
                    rooms[room].discard(addr)

def handle_command(data, addr):
    parts = data.strip().split()
    if not parts:
        return
    cmd, *args = parts

    if cmd.upper() == "USERNAME" and args:
        with lock:
            clients[addr] = args[0]
        server_sock.sendto(f"[Server] Welcome {args[0]}!\n".encode(), addr)

    elif cmd.upper() == "JOIN" and args:
        room = args[0]
        with lock:
            rooms.setdefault(room, set()).add(addr)
        uname = clients.get(addr, "?")
        broadcast(room, f"[Server] {uname} joined {room}")

    elif cmd.upper() == "LEAVE" and args:
        room = args[0]
        with lock:
            if room in rooms and addr in rooms[room]:
                rooms[room].remove(addr)
        uname = clients.get(addr, "?")
        broadcast(room, f"[Server] {uname} left {room}")

    elif cmd.upper() == "MSG" and len(args) >= 2:
        room = args[0]
        msg = " ".join(args[1:])
        uname = clients.get(addr, "?")
        broadcast(room, f"[{room}] {uname}: {msg}", exclude=addr)

    elif cmd.upper() == "WHO" and args:
        room = args[0]
        with lock:
            members = [clients.get(c, "?") for c in rooms.get(room, set())]
        server_sock.sendto(f"[Server] Users in {room}: {', '.join(members)}\n".encode(), addr)

    elif cmd.upper() == "ROOMS":
        with lock:
            info = [f"{r} ({len(s)})" for r, s in rooms.items()]
        server_sock.sendto(f"[Server] Active rooms: {', '.join(info)}\n".encode(), addr)

    else:
        server_sock.sendto(b"[Server] Unknown or invalid command.\n", addr)

def server_loop():
    while True:
        try:
            data, addr = server_sock.recvfrom(4096)
            if not data:
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
