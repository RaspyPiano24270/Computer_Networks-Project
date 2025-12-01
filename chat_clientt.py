import socket
import threading
import time
import sys

MAX_PACKET_SIZE = 4096
WINDOW_SIZE = 100
ACK_TIMEOUT_SECONDS = 1.0

# decodes the packet
def decode_packet(packet_bytes):
    try:
        parts = packet_bytes.decode().split("|", 2)
        seq_num = int(parts[0])
        ack_num = int(parts[1])
        payload = parts[2]
        return seq_num, ack_num, payload
    except Exception:
        return None, None, None

# connects to the client
class ChatClient:
    def __init__(self, server_ip, server_port):
        self.server_address = (server_ip, server_port)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(0.5)

        self.send_base = 0            
        self.next_sequence_number = 0 
        self.thread_lock = threading.Lock()
        self.send_window = {}         
        self.acks_received = set()
        self.running = True
# creates the packet
    def create_packet(self, seq_num, ack_num, message):
        return f"{seq_num}|{ack_num}|{message}".encode()
#resends packets that have ot been acknowledged 
    def resend_packets_loop(self):
        while self.running:
            time.sleep(0.1)
            current_time = time.time()
            with self.thread_lock:
                for seq_num in list(self.send_window.keys()):
                    message, last_sent_time, retrans_count = self.send_window[seq_num]

                    if seq_num in self.acks_received:
                        continue  # Already ACKed

                    if current_time - last_sent_time > ACK_TIMEOUT_SECONDS:
                        self.socket.sendto(self.create_packet(seq_num, 0, message), self.server_address)
                        self.send_window[seq_num] = (message, current_time, retrans_count + 1)
                        print(f"[Client] retransmitted seq {seq_num}")
# always running waiting for acks
    def receive_ack_loop(self):
        while self.running:
            try:
                data, _ = self.socket.recvfrom(MAX_PACKET_SIZE)
                seq_num, ack_num, payload = decode_packet(data)

                if payload == "" and seq_num == 0:
                    with self.thread_lock:
                        if ack_num in self.send_window and ack_num not in self.acks_received:
                            self.acks_received.add(ack_num)
                        while self.send_base in self.acks_received:
                            del self.send_window[self.send_base]
                            self.send_base += 1
                else:
                    print(f"\n{payload}")

            except socket.timeout:
                continue
            except Exception as e:
                print("[Client] Socket error:", e)
# text and inputs that popup when you first connect
    def start_up_messages(self):
        username = input("Enter username: ").strip()
        self.send_message(f"USERNAME {username}")

        print("Commands: JOIN <room>, LEAVE <room>, MSG <room> <text>, WHO <room>, ROOMS, QUIT")

        while True:
            user_input = input("> ").strip()
            if not user_input:
                continue

            if user_input.upper() == "QUIT":
                self.send_message("QUIT")
                break

            self.send_message(user_input)

        self.running = False
# sends message to the server
    def send_message(self, message):
        with self.thread_lock:
            if self.next_sequence_number < self.send_base + WINDOW_SIZE:
                seq_num = self.next_sequence_number
                self.send_window[seq_num] = (message, time.time(), 0)
                self.socket.sendto(self.create_packet(seq_num, 0, message), self.server_address)
                self.next_sequence_number += 1
#main
def main():
    if len(sys.argv) != 3:
        print(f"Usage: python {sys.argv[0]} <server_ip> <server_port>")
        sys.exit(1)

    client = ChatClient(sys.argv[1], int(sys.argv[2]))

    threading.Thread(target=client.receive_ack_loop, daemon=True).start()
    threading.Thread(target=client.resend_packets_loop, daemon=True).start()

    client.start_up_messages()


if __name__ == "__main__":
    main()
