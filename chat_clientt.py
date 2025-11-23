import tkinter as tk
from tkinter import scrolledtext, simpledialog, messagebox
import socket
import threading
import sys

class ChatClient:
    def __init__(self, root, server_ip, server_port):
        self.root = root
        self.root.title("Group Chat")

        self.server_addr = (server_ip, server_port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(1.0)

        self.username = simpledialog.askstring("Login", "Enter username:", parent=root)
        if not self.username:
            self.username = "Anonymous User"

        self.send_raw(f"USERNAME {self.username}")

        self.chat_display = scrolledtext.ScrolledText(root, wrap=tk.WORD, state='disabled', height=20)
        self.chat_display.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        entry_frame = tk.Frame(root)
        entry_frame.pack(fill=tk.X, padx=10, pady=(0,10))

        self.entry = tk.Entry(entry_frame)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entry.bind('<Return>', lambda e: self.send_command())

        send_button = tk.Button(entry_frame, text='Send', command=self.send_command)
        send_button.pack(side=tk.LEFT, padx=5)

        quit_button = tk.Button(root, text='Quit', command=self.quit)
        quit_button.pack(pady=(0,5))

        tk.Label(root, text='Commands: JOIN <room>, LEAVE <room>, MSG <room> <text>, WHO <room>, ROOMS').pack(pady=(0,5))

        self.running = True
        threading.Thread(target=self.receive_messages, daemon=True).start()

    def send_raw(self, message):
        try:
            self.sock.sendto((message + "\n").encode(), self.server_addr)
        except Exception as e:
            self.display_message(f"[-] Failed to send message: {e}")

    def send_command(self):
        cmd = self.entry.get().strip()
        if not cmd:
            return
        self.entry.delete(0, tk.END)
        self.send_raw(cmd)
        if cmd.upper().startswith("MSG "):
            parts = cmd.split()
            if len(parts) >= 3:
                room = parts[1]
                text = " ".join(parts[2:])
                self.display_message(f"You ({room}): {text}")

    def receive_messages(self):
        while self.running:
            try:
                data, _ = self.sock.recvfrom(4096)
                if not data:
                    self.display_message("[Server closed the connection]")
                    break
                self.display_message(data.decode().strip())
            except socket.timeout:
                continue
            except Exception:
                break
        self.running = False

    def display_message(self, msg):
        self.chat_display.configure(state='normal')
        self.chat_display.insert(tk.END, msg + '\n')
        self.chat_display.configure(state='disabled')
        self.chat_display.see(tk.END)

    def quit(self):
        self.running = False
        try:
            self.sock.close()
        except:
            pass
        self.root.destroy()

def main():
    if len(sys.argv) != 3:
        print(f"Usage: python {sys.argv[0]} <server_ip> <server_port>")
        sys.exit(1)

    server_ip = sys.argv[1]
    server_port = int(sys.argv[2])

    root = tk.Tk()
    client = ChatClient(root, server_ip, server_port)
    root.mainloop()

if __name__ == '__main__':
    main()
