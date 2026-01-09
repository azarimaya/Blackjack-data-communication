"""
Constants used throughout the Blackjack project.
"""

# --- Network Constants ---
UDP_PORT = 13122
BUFFER_SIZE = 1024
BROADCAST_IP = '<broadcast>'

# --- Protocol Constants ---
MAGIC_COOKIE = 0xabcddcba

# Message Types
MSG_TYPE_OFFER = 0x02    # Server -> Client (UDP)
MSG_TYPE_REQUEST = 0x03  # Client -> Server (TCP)
MSG_TYPE_PAYLOAD = 0x04  # Bidirectional (TCP)

# Field Lengths (in bytes)
SERVER_NAME_LEN = 32
TEAM_NAME_LEN = 32
MSG_TYPE_LEN = 1
PORT_LEN = 2

# --- Game Constants ---
# Card Suits
SUIT_HEART = 0
SUIT_DIAMOND = 1
SUIT_CLUB = 2
SUIT_SPADE = 3

# Game Results
RESULT_WIN = 0x03
RESULT_LOSS = 0x02
RESULT_TIE = 0x01
RESULT_NOT_OVER = 0x00

# Player Actions
ACTION_HIT = "Hit"
ACTION_STAND = "Stand"