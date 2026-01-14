import socket

# --- Get Real Wi-Fi IP ---
def get_local_ip():
    """
    Tries to find the IP address of the actual network interface (Wi-Fi/Ethernet)
    by attempting to connect to a public DNS (8.8.8.8).
    This bypasses WSL/Virtual adapters.
    """

    # Create a UDP socket (SOCK_DGRAM)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        # Connect to public DNS (Google)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]

    # If something fails, fallback to localhost.
    except Exception:
        ip = '127.0.0.1'

    finally:
        s.close()

    return ip

# --- Print Cards ---
def get_card_name(rank, suit):

    # Mapping suit integers (0-3) to symbols
    suits_symbols = ['♡', '♢', '♧', '♤']
    rank_str = str(rank)

    # Convert special ranks (1, 11-13) to letters
    if rank == 1:
        rank_str = "A"
    elif rank == 11:
        rank_str = "J"
    elif rank == 12:
        rank_str = "Q"
    elif rank == 13:
        rank_str = "K"

    return f"{rank_str}{suits_symbols[suit]}"