import socket
import sys
import threading

def receive_messages(sock):
    while True:
        try:
            data, _ = sock.recvfrom(4096)
            if not data:
                print("[-] Server closed the connection.")
                break
            print(f"\n{data.decode().strip()}")
        except Exception:
            break

def main():
    if len(sys.argv) != 3:
        print(f"Usage: python {sys.argv[0]} <server_ip> <server_port>")
        sys.exit(1)

    server_ip = sys.argv[1]
    server_port = int(sys.argv[2])

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(1.0)

    # Send USERNAME command first
    username = input("Enter your username: ").strip()
    sock.sendto(f"USERNAME {username}".encode(), (server_ip, server_port))

    threading.Thread(target=receive_messages, args=(sock,), daemon=True).start()

    while True:
        try:
            message = input()
            if not message:
                continue
            sock.sendto(message.encode(), (server_ip, server_port))
        except KeyboardInterrupt:
            print("\nExiting...")
            break

if __name__ == "__main__":
    main()
