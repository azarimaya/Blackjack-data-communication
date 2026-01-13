# Distributed Blackjack Game

A multi-threaded, multiplayer Blackjack game implementing a custom binary protocol over TCP/IP and UDP. This project demonstrates network programming concepts including socket management, concurrency, and packet serialization.

## Features

* **Auto-Discovery:** Clients automatically find the server using UDP Broadcasts.
* **Multi-Threaded Server:** Supports multiple players simultaneously on different threads.
* **Robust Networking:**
    * Custom binary protocol with strict endianness.
    * TCP message fragmentation handling.
    * Real IP binding (bypasses virtual adapters like WSL/Docker).
* **Interactive Client UI:**
    * Real-time statistics (Bust Probability calculator).
    * Color-coded terminal output (ANSI colors).

## Installation & Usage

### Prerequisites
* Python 3.6 or higher.
* A network environment allowing UDP Broadcasts (Local Wi-Fi or LAN).

### 1. Start the Server
The server listens for incoming connections and broadcasts its availability.
```bash
python server.py
```

### 2. Start the Client
Run the client in a separate terminal (or a different machine on the same Wi-Fi).
```bash
python client.py
```

## Project Structure
```bash
├── client.py       # Client application (UI, Game Loop, Stats)
├── server.py       # Server application (Multi-threading, Game Logic)
├── protocol.py     # Protocol serialization/deserialization logic
├── utils.py        # Helper functions (IP discovery, Card formatting)
├── consts.py       # Shared constants (Ports, Magic Cookies, Msg Types)
└── README.md       # Project documentation
```