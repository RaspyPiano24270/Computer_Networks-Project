import socket
import threading
import time

MAX_PACKET_SIZE = 4096
WINDOW_SIZE = 100
ACK_TIMEOUT_SECONDS = 1.0

thread_lock = threading.Lock()

client_usernames = {}  
chat_rooms = {}        
client_states = {}     
client_metrics = {}    
max_clients_connected = 0
#time for later calc
def current_time_millis():
    return int(time.time() * 1000)


def create_packet(sequence_num, ack_num, message):
    return f"{sequence_num}|{ack_num}|{message}".encode()
#decodes the packet 
def decode_packet(packet_bytes):
    try:
        parts = packet_bytes.decode().split("|", 2)
        seq_num = int(parts[0])
        ack_num = int(parts[1])
        payload = parts[2]
        return seq_num, ack_num, payload #payload is bassically the message being sent
    except Exception:
        return None, None, None
#sending the packet
def send_packet(sock, client_addr, sequence_num, ack_num, message):
    packet = create_packet(sequence_num, ack_num, message)
    sock.sendto(packet, client_addr)
#sending the acknowledgment
def send_ack(sock, client_addr, ack_num):
    packet = create_packet(0, ack_num, "")
    sock.sendto(packet, client_addr)
# starts tracking the metrics for each client that joins
def initialize_client(client_addr):
    global max_clients_connected
    with thread_lock:
        if client_addr not in client_states:
            client_states[client_addr] = {
                "expected_sequence": 0,
                "out_of_order_buffer": {},
                "send_window": {},
            }
            client_metrics[client_addr] = {
                "retransmissions_count": 0,
                "out_of_order_count": 0,
                "latency_list": [],
                "messages_received": 0,
                "bytes_received": 0,
                "start_timestamp": None,
                "end_timestamp": None,
                "total_packets_received": 0,
                "acks_received": set(),
            }
        max_clients_connected = max(max_clients_connected, len(client_states))
# latency metric
def latency_metrics(client_addr, packet_recv_time):
    if client_addr not in client_metrics:
        return
    now = current_time_millis()
    latency = now - packet_recv_time
    client_metrics[client_addr]["latency_list"].append(latency)
# if a messahe is sount out of order this fixes it
def deliver_ordered_messages(client_addr):
    state = client_states.get(client_addr)
    if not state:
        return

    expected_seq = state["expected_sequence"]

    while expected_seq in state["out_of_order_buffer"]:
        payload, recv_time = state["out_of_order_buffer"].pop(expected_seq)

        process_chat_command(client_addr, payload)
        # updating metrics
        latency_metrics(client_addr, recv_time)

        if client_addr in client_metrics:
            metrics = client_metrics[client_addr]
            metrics["messages_received"] += 1
            metrics["bytes_received"] += len(payload)
            if metrics["start_timestamp"] is None:
                metrics["start_timestamp"] = recv_time
            metrics["end_timestamp"] = current_time_millis()

        state["expected_sequence"] += 1
        expected_seq = state["expected_sequence"]
# gets the required information from the client in order to execute the command
def process_chat_command(client_addr, message):
    parts = message.strip().split()
    if not parts:
        return

    command, *args = parts
    command = command.upper()
    username = client_usernames.get(client_addr, "?")
# username command
    if command == "USERNAME" and args:
        username = args[0]
        with thread_lock:
            client_usernames[client_addr] = username
        send_packet(server_socket, client_addr, 0, client_states[client_addr]["expected_sequence"] - 1,
                    f"[Server] Welcome {username}!")
        print(f"[Server] Registered username '{username}' from {client_addr}")
# join command
    elif command == "JOIN" and args:
        room_name = args[0]
        with thread_lock:
            chat_rooms.setdefault(room_name, set()).add(client_addr)
        broadcast_message(room_name, f"[Server] {username} joined {room_name}")
# leave command
    elif command == "LEAVE" and args:
        room_name = args[0]
        with thread_lock:
            if room_name in chat_rooms and client_addr in chat_rooms[room_name]:
                chat_rooms[room_name].remove(client_addr)
        broadcast_message(room_name, f"[Server] {username} left {room_name}")
# msg command
    elif command == "MSG" and len(args) >= 2:
        room_name = args[0]
        chat_message = " ".join(args[1:])
        broadcast_message(room_name, f"[{room_name}] {username}: {chat_message}", exclude_addr=client_addr)
# who command
    elif command == "WHO" and args:
        room_name = args[0]
        with thread_lock:
            members = [client_usernames.get(c_addr, "?") for c_addr in chat_rooms.get(room_name, set())]
        send_packet(server_socket, client_addr, 0, client_states[client_addr]["expected_sequence"] - 1,
                    f"[Server] Users in {room_name}: {', '.join(members)}")
# rooms command
    elif command == "ROOMS":
        with thread_lock:
            room_info = [f"{room} ({len(members)})" for room, members in chat_rooms.items()]
        send_packet(server_socket, client_addr, 0, client_states[client_addr]["expected_sequence"] - 1,
                    f"[Server] Active rooms: {', '.join(room_info)}")
# quit command
    elif command == "QUIT":
        print(f"[Server] User '{username}' disconnected")
        print_client_metrics(client_addr)

        with thread_lock:
            client_usernames.pop(client_addr, None)
            for members in chat_rooms.values():
                members.discard(client_addr)
            client_states.pop(client_addr, None)
            client_metrics.pop(client_addr, None)

    else:
        send_packet(server_socket, client_addr, 0, client_states[client_addr]["expected_sequence"] - 1,
                    "[Server] Unknown command")
#brodacast the mesage to other users
def broadcast_message(room_name, message, exclude_addr=None):
    with thread_lock:
        for client_addr in list(chat_rooms.get(room_name, set())):
            if client_addr != exclude_addr:
                send_packet(server_socket, client_addr, 0,
                            client_states[client_addr]["expected_sequence"] - 1, message)
# this code retansmits packets that havent been sent 
def retransmit_unacked_packets(sock):
    while True:
        time.sleep(0.1)
        with thread_lock:
            for client_addr, state in client_states.items():
                current_time = time.time()
                send_window = state["send_window"]

                for seq_num in list(send_window.keys()):
                    message, last_sent_time, retrans_count = send_window[seq_num]

                    if client_addr in client_metrics and seq_num in client_metrics[client_addr].get("acks_received", set()):
                        continue  

                    if current_time - last_sent_time > ACK_TIMEOUT_SECONDS:
                        sock.sendto(create_packet(seq_num, state["expected_sequence"] - 1, message), client_addr)
                        if client_addr in client_metrics:
                            client_metrics[client_addr]["retransmissions_count"] += 1
                        send_window[seq_num] = (message, current_time, retrans_count + 1)
                        print(f"[Server] Retransmitted packet seq {seq_num} to {client_addr}")
#gets information for metrics
def print_client_metrics(client_addr):
    import statistics

    metrics = client_metrics.get(client_addr)
    if not metrics:
        print(f"No metrics for {client_addr}")
        return

    latencies = metrics["latency_list"]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0

    percentile_95 = 0
    if len(latencies) >= 20:
        sorted_lat = sorted(latencies)
        percentile_95 = sorted_lat[int(len(latencies) * 0.95) - 1]

    start = metrics.get("start_timestamp")
    end = metrics.get("end_timestamp")
    duration_sec = (end - start) / 1000 if start and end and end > start else 0
    goodput = metrics.get("messages_received", 0) / duration_sec if duration_sec > 0 else 0

    bytes_recv = metrics.get("bytes_received", 0)
    retransmissions = metrics.get("retransmissions_count", 0)
    retrans_per_kb = retransmissions / (bytes_recv / 1024) if bytes_recv else 0

    total_msgs = metrics.get("messages_received", 0)
    out_of_order = metrics.get("out_of_order_count", 0)
    out_of_order_pct = (out_of_order / total_msgs) * 100 if total_msgs else 0
#print out the metrics
    print("\n--- Metrics ---")
    print(f"Average latency (ms): {avg_latency:.2f}")
    print(f"95th percentile latency (ms): {percentile_95:.2f}")
    print(f"Goodput (messages/sec): {goodput:.2f}")
    print(f"Retransmissions per KB: {retrans_per_kb:.2f}")
    print(f"Out-of-order messages: {out_of_order} ({out_of_order_pct:.2f}%)")
    print(f"Max concurrent clients: {max_clients_connected}")
    print("---------------------------")
# This does like decoding receiving bassically everything the server need to do
def server_loop():
    while True:
        try:
            packet, client_addr = server_socket.recvfrom(MAX_PACKET_SIZE)
        except Exception as e:
            print("[Server] Socket error:", e)
            continue
        initialize_client(client_addr)

        seq_num, ack_num, payload = decode_packet(packet)
        if seq_num is None:
            continue

        state = client_states.get(client_addr)
        if state is None:
            continue

        with thread_lock:
            if client_addr not in client_metrics:
                client_metrics[client_addr] = {
                    "retransmissions_count": 0,
                    "out_of_order_count": 0,
                    "latency_list": [],
                    "messages_received": 0,
                    "bytes_received": 0,
                    "start_timestamp": None,
                    "end_timestamp": None,
                    "total_packets_received": 0,
                    "acks_received": set(),
                }

            client_metrics[client_addr]["acks_received"].add(ack_num)
            client_metrics[client_addr]["total_packets_received"] += 1

            if seq_num < state["expected_sequence"]:
                send_ack(server_socket, client_addr, seq_num)
                continue
            if seq_num not in state["out_of_order_buffer"]:
                state["out_of_order_buffer"][seq_num] = (payload, current_time_millis())
                if seq_num > state["expected_sequence"]:
                    client_metrics[client_addr]["out_of_order_count"] += 1
                send_ack(server_socket, client_addr, seq_num)

        deliver_ordered_messages(client_addr)
#main
def main():
    global server_socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind(("0.0.0.0", 5000))

    print("[Server] Listening on port 5000")

    threading.Thread(target=retransmit_unacked_packets, args=(server_socket,), daemon=True).start()

    try:
        server_loop()
    except KeyboardInterrupt:
        print("\n[Server] Shutting down")
        for addr in list(client_metrics.keys()):
            print_client_metrics(addr)
        print("[Server] Server stopped")
if __name__ == "__main__":
    main()
