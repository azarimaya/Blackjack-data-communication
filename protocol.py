# Constants
import struct
from consts import *

def pad_string(text, length=TEAM_NAME_LEN):
    """
    Ensures a string is exactly 'length' bytes.
    Pads with null bytes (\x00) if short, truncates if long.
    """
    # Encode string to bytes first
    encoded = text.encode('utf-8')

    if len(encoded) < length:
        # Add padding
        return encoded + b'\x00' * (length - len(encoded))
    else:
        # Truncate
        return encoded[:length]

def decode_string(bytes_data):
    """
    Decodes bytes to string and removes null padding.
    """
    return bytes_data.decode('utf-8').rstrip('\x00')

def pack_offer(server_port, server_name):
    """
    Packs the Offer message.
    Args:
        server_port (int): The TCP port the server is listening on.
        server_name (str): The name of the server.
    Returns:
        bytes: The packed binary message.
    """
    padded_name = pad_string(server_name)

    # ! = Network Endian
    # I = Magic Cookie (4 bytes)
    # B = Message Type (1 byte)
    # H = Server Port (2 bytes)
    # 32s = Server Name (32 bytes)
    packed_data = struct.pack('!IBH32s', MAGIC_COOKIE, MSG_TYPE_OFFER, server_port, padded_name)
    return packed_data

def unpack_offer(data):
    """
    Unpacks the Offer message (Used by Client).
    """
    try:
        # Unpack returns a tuple
        cookie, msg_type, server_port, server_name_bytes = struct.unpack('!IBH32s', data)

        # Invalid packet
        if cookie != MAGIC_COOKIE:
            return None
        # Wrong message type
        if msg_type != MSG_TYPE_OFFER:
            return None

        return {
            "type": "OFFER",
            "server_port": server_port,
            "server_name": decode_string(server_name_bytes)
        }

    # Parsing failed
    except struct.error:
        return None

def pack_request(team_name, rounds):
    """
    Packs the Request message.
    Args:
        team_name (str): The name of the client team.
        rounds (int): The number of rounds the client wishes to play.
    Returns:
        bytes: The packed binary message.
    """
    padded_name = pad_string(team_name)

    # ! = Network Endian
    # I = Magic Cookie (4 bytes)
    # B = Message Type (1 byte)
    # B = Rounds (1 byte)
    # 32s = Team Name (32 bytes)
    return struct.pack('!IBB32s', MAGIC_COOKIE, MSG_TYPE_REQUEST, rounds, padded_name)

def unpack_request(data):
    """
    Unpacks the Request message (Used by Server).
    """
    try:
        # Unpack returns a tuple
        cookie, msg_type, rounds, team_name_bytes = struct.unpack('!IBB32s', data)

        # Invalid packet
        if cookie != MAGIC_COOKIE:
            return None
        # Wrong message type
        if msg_type != MSG_TYPE_REQUEST:
            return None

        return {
            "type": "REQUEST",
            "rounds": rounds,
            "team_name": decode_string(team_name_bytes)
        }

    # Parsing failed
    except struct.error:
        return None

def pack_payload_server(result, card_rank, card_suit):
    """
    Packs the Payload message (Server -> Client).
    result: 0 = Running, 1 = Tie, 2 = Loss, 3 = Win
    card_rank: 1-13
    card_suit: 0-3 (H, D, C, S)
    """

    # ! = Network Endian
    # I = Magic Cookie (4 bytes)
    # B = Message Type (1 byte)
    # B = Result (1 byte)
    # H = Card Rank (2 bytes)
    # B = Card Suit (1 byte)
    return struct.pack('!IBBHB', MAGIC_COOKIE, MSG_TYPE_PAYLOAD, result, card_rank, card_suit)

def unpack_payload_server(data):
    """
    Unpacks Payload (Client side receiving from Server)
    """
    try:
        # Unpack returns a tuple
        cookie, msg_type, result, rank, suit = struct.unpack('!IBBHB', data)

        # Validate that the packet starts with the correct protocol ID and message type
        if cookie != MAGIC_COOKIE or msg_type != MSG_TYPE_PAYLOAD:
            return None

        return {
            "type": "PAYLOAD_SERVER",
            "result": result,
            "rank": rank,
            "suit": suit
        }

    # Parsing failed
    except struct.error:
        return None

def pack_payload_client(decision):
    """
    Packs the Payload message (Client -> Server).
    decision: "Hit" or "Stand"
    """

    encoded_decision = decision.encode('utf-8')

    # ! = Network Endian
    # I = Magic Cookie (4 bytes)
    # B = Message Type (1 byte)
    # 5s = Decision (5 bytes)
    return struct.pack('!IB5s', MAGIC_COOKIE, MSG_TYPE_PAYLOAD, encoded_decision)

def unpack_payload_client(data):
    """
    Unpacks Payload (Server side receiving from Client)
    """
    try:
        # Unpack returns a tuple
        cookie, msg_type, decision_bytes = struct.unpack('!IB5s', data)

        # Validate that the packet starts with the correct protocol ID and message type
        if cookie != MAGIC_COOKIE or msg_type != MSG_TYPE_PAYLOAD:
            return None

        return {
            "type": "PAYLOAD_CLIENT",
            "decision": decode_string(decision_bytes)
        }

    # Parsing failed
    except struct.error:
        return None