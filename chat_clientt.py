import tkinter as tk
from tkinter import scrolledtext, simpledialog, messagebox
import socket
import threading
import sys

#window
class ChatClient:
    def __init__(self, root, server_ip, server_port):
        self.root = root
        self.root.title("Group Chat")

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect((server_ip, server_port))
        except Exception as e:
            messagebox.showerror("Connection Error", f"Could not connect to server: {e}")
            root.destroy()
            return
 #username
        self.username = simpledialog.askstring("Login", "Enter username:", parent=root)
        if not self.username:
            self.username = "Anonymous User"


        self.send_raw(f"USERNAME {self.username}")
# ui
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

#thread
        self.running = True
        threading.Thread(target=self.receive_messages, daemon=True).start()

        
#sends the raw message to the server
    def send_raw(self, message):
        try:
            self.sock.sendall((message + "\n").encode())
        except Exception as e:
            self.display_message(f"[-] Failed to send message: {e}")
# send the command to seld more for gui
    def send_command(self):
        cmd = self.entry.get().strip()
        if not cmd:
            return
        self.entry.delete(0, tk.END)

        self.send_raw(cmd)

        # shows your messages
        if cmd.upper().startswith("MSG "):
            parts = cmd.split()
            if len(parts) >= 3:
                room = parts[1]
                text = " ".join(parts[2:])
                self.display_message(f"You ({room}): {text}")
#receive and show the message
    def receive_messages(self):
        while self.running:
            try:
                data = self.sock.recv(1024).decode()
                if not data:
                    self.display_message("[Server closed the connection]")
                    break
                for line in data.strip().splitlines():
                    self.display_message(line)
            except Exception:
                break
        self.running = False
        try:
            self.sock.close()
        except:
            pass
#displays message
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

#main
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
