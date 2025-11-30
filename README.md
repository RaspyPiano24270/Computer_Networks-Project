# Computer_Networks-Project

1 Team Information
TEAM NAME: TEAM 4
TEAM MEMBERS: Gabriel Acuna, Travis Shows, Eric Gerner, Allison Harvel, Alejandra Flores
Group Chat

2 Project Overview

We want to make a group chat that has the ability to join and leave rooms, and to send messages between them. We also want to have a feature that shows the presence of the chat room for example it states “user had entered the chat room”


3 Transport Protocol Design Plan
I believe that we will be using TCP like because we will be using sockets in order to connect multiple users at the same time to the same server so that they will be able to communicate

4 Application Layer Design Plan
* How concurrency will be supported (at least 2 clients).


Message format and command grammar:
-JOIN <room> - client joins a specific chat room
-LEAVE <room> - client leaves a specific chat room 
-MSG <room> <room> - sends a message to ALL users in a given room
-WHO <room> - lists all users currently in a specific chat room
-NOTIFY <text> - used by the server to broadcast system messages e.g: “user X has joined the room”


	How your client and server will interact:
-The client establishes a TCP connection with the server and authenticates with a username (or ID)
-Once connected, the client can send commands (e.g: JOIN), which the server will parse and then route to the correct room. 
-The server maintains a mapping of chat rooms and connected clients. When a message is received, the server relays it to all clients that are currently in that room.
-The server will also send system notifications (e.g: user joined/left) automatically.


How concurrency will be supported (at least 2 clients):
-The server will handle multiple client connections simultaneously using either threading or async I/O
-Each client will run its own thread or asynchronous task so messages from one client won’t block others.
-Synchronization mechanisms (such as locks or message queues) will ensure safe access to shared data structures like the list of rooms.
-The design supports dynamic joining and leaving, multiple clients will be able to interact simultaneously without interrupting others.


5 Testing and Metrics Plan
From what we have researched you can have emulators that simulate packet loss so we can just ramp it up as we progress the levels
The metrics that we intend to measure is whether or not the message sends and how long it takes the message to send to the other user.

6 Chat Server Commands

The chat server now supports the following commands:

- `JOIN <room>` – Join a chat room.
- `LEAVE <room>` – Leave a chat room.
- `MSG <room> <message>` – Send a message to all users in a chat room.
- `WHO <room>` – List all users currently in a specific chat room.
- `ROOMS` – List all active chat rooms and their user counts.


  
7 Progress Summary (Midterm Status)
We have been able to make it so that 2 people can be connected to the same server and chat with each other however we still need to implement the actual rooms and presence to make it like a chat room.

8 Run Instructions 
to the tin the code it is pretty simple all you have to do is put python followed by the code name, and for the client side you do bassically the same thing however in between the code name and the port number you put the ip of the server
example:
python chat_serverr.py 
python chat_clientt.py <server ip> 5000



