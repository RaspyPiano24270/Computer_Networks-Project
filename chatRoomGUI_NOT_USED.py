import tkinter as tk
from tkinter import scrolledtext, simpledialog, messagebox
import threading
import time
import queue

# test server
class ChatServer:
    def __init__(self):
        self.rooms = {}  # room_name -> set of usernames
        self.clients = {}  # username -> client.receive()
        self.lock = threading.Lock()

    def register(self, username, receive_func):
        with self.lock:
            self.clients[username] = receive_func

    def unregister(self, username):
        with self.lock:
            for room in self.rooms.values():
                room.discard(username)
            if username in self.clients:
                del self.clients[username]

    def handle_command(self, username, command_line):
        parts = command_line.strip().split()
        if not parts:
            return

        cmd = parts[0].upper()
        args = parts[1:]

        if cmd == 'JOIN' and len(args) >= 1:
            room = args[0]
            with self.lock:
                if room not in self.rooms:
                    self.rooms[room] = set()
                self.rooms[room].add(username)
            self._broadcast(room, f"{username} joined {room}")

        elif cmd == 'LEAVE' and len(args) >= 1:
            room = args[0]
            with self.lock:
                if room in self.rooms and username in self.rooms[room]:
                    self.rooms[room].remove(username)
            self._broadcast(room, f"{username} left {room}")

        elif cmd == 'MSG' and len(args) >= 2:
            room = args[0]
            text = ' '.join(args[1:])
            self._broadcast(room, f"[{room}] {username}: {text}")

        else:
            if username in self.clients:
                self.clients[username](f"Unknown command or invalid syntax: {command_line}")

    def _broadcast(self, room, message):
        with self.lock:
            if room not in self.rooms:
                return
            for user in list(self.rooms[room]):
                if user in self.clients:
                    self.clients[user](message)

#  user GUI
class ChatClient:
    def __init__(self, root, server: ChatServer):
        self.root = root
        self.server = server
        self.username = simpledialog.askstring('Login', 'Enter username:')
        if not self.username:
            self.username = f'user{int(time.time())%1000}'
        self.server.register(self.username, self.receive_message)

        self.root.title(f"Group Chat - {self.username}")

        # Chat display
        self.chat_display = scrolledtext.ScrolledText(root, wrap=tk.WORD, state='disabled', height=20)
        self.chat_display.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # Entry box
        entry_frame = tk.Frame(root)
        entry_frame.pack(fill=tk.X, padx=10, pady=(0,10))

        self.entry = tk.Entry(entry_frame)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entry.bind('<Return>', lambda e: self.send_command())

        send_button = tk.Button(entry_frame, text='Send', command=self.send_command)
        send_button.pack(side=tk.LEFT, padx=5)

        # Quit button
        quit_button = tk.Button(root, text='Quit', command=self.quit)
        quit_button.pack(pady=(0,5))

        # Info label
        tk.Label(root, text='Commands: JOIN <room>, LEAVE <room>, MSG <room> <text>').pack(pady=(0,5))

    def send_command(self):
        cmd = self.entry.get().strip()
        if not cmd:
            return
        self.entry.delete(0, tk.END)
        self.server.handle_command(self.username, cmd)

    def receive_message(self, message):
        self.chat_display.configure(state='normal')
        self.chat_display.insert(tk.END, message + '\n')
        self.chat_display.configure(state='disabled')
        self.chat_display.see(tk.END)

    def quit(self):
        self.server.unregister(self.username)
        self.root.destroy()

def start_app():
    server = ChatServer()
    root = tk.Tk()
    ChatClient(root, server)

    # background bot to show room activity
    def bot():
        bot_user = 'bot'
        server.register(bot_user, lambda msg: None)
        server.handle_command(bot_user, 'JOIN general')
        messages = ["Hey there!", "Welcome to the chat.", "Try JOIN general!", "Use MSG general Hello!"]
        while True:
            time.sleep(3)
            server.handle_command(bot_user, f"MSG general {messages[int(time.time()) % len(messages)]}")
    threading.Thread(target=bot, daemon=True).start()

    root.mainloop()

if __name__ == '__main__':
    start_app()
