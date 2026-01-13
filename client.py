import socket
import sys
import os
import protocol
from protocol import *
import utils

# --- Colors for UI ---
class Colors:
    """
    ANSI Escape Codes for terminal coloring.
    Allows printing colored text in the console.
    """

    RESET = "\033[0m"
    RED = "\033[91m"  # For Bust / Loss
    GREEN = "\033[92m"  # For Win / Safe
    BOLD = "\033[1m"

    @staticmethod
    def card(text):
        # Formats card text as Bold
        return f"{Colors.BOLD}{text}{Colors.RESET}"

    @staticmethod
    def win(text):
        # Formats text as Bold Green
        return f"{Colors.GREEN}{Colors.BOLD}{text}{Colors.RESET}"

    @staticmethod
    def loss(text):
        # Formats text as Bold Red
        return f"{Colors.RED}{Colors.BOLD}{text}{Colors.RESET}"

# Enable ANSI colors in Windows terminal
os.system('')

def get_card_value(rank):
    """
    Returns the initial Blackjack value for a card rank.
    """

    # Ace is worth 11 by default (converted to 1 later if bust)
    if rank == 1:
        return 11

    # Face cards (Jack=11, Queen=12, King=13) are all worth 10
    if rank >= 11:
        return 10

    # Number cards (2-10) are worth their rank
    return rank

def calculate_stats(current_hand_ranks, dealer_visible_rank=None):
    """
    Calculates statistics based on the REMAINING cards in a 52-card deck.
    Subtracts Player's hand AND Dealer's visible card from the pool.
    """

    # 1. Start with a full deck: 4 cards of each rank (1-13)
    deck_pool = {rank: 4 for rank in range(1, 14)}

    # 2. Remove Player's known cards
    for rank in current_hand_ranks:
        if deck_pool[rank] > 0:
            deck_pool[rank] -= 1

    # 3. Remove Dealer's visible card (if we know it)
    if dealer_visible_rank and deck_pool[dealer_visible_rank] > 0:
        deck_pool[dealer_visible_rank] -= 1

    total_remaining_cards = sum(deck_pool.values())

    if total_remaining_cards == 0:
        return 0.0, 0.0

    safe_count = 0

    # 4. Simulate drawing from the remaining pool
    for rank, count in deck_pool.items():
        if count > 0:
            temp_hand = current_hand_ranks + [rank]

            if calculate_hand_score(temp_hand) <= 21:
                # If rank is safe, all copies of it in the deck are safe outcomes
                safe_count += count

    # 5. Calculate weighted percentages
    safe_prob = (safe_count / total_remaining_cards) * 100
    bust_prob = 100.0 - safe_prob

    return bust_prob, safe_prob

def calculate_hand_score(hand_ranks):
    """
    Calculates score from a list of ranks, handling Ace as 1 or 11.
    """
    score = 0
    aces = 0

    for rank in hand_ranks:
        if rank == 1:     # Ace counts as 11 initially
            aces += 1
            score += 11
        elif rank >= 11:  # Face cards (J, Q, K) count as 10
            score += 10
        else:             # Number cards (2-10) count as their rank
            score += rank

    # If score is over 21, reduce Aces from 11 to 1 to avoid busting
    while score > 21 and aces > 0:
        score -= 10
        aces -= 1

    return score

class BlackjackClient:
    """
    Manages the client-side logic for the Blackjack game.
    - Listens for UDP broadcast offers.
    - Connects to the server via TCP.
    - Handles the interactive game loop (UI, decisions, stats).
    """

    def __init__(self, team_name):
        self.team_name = team_name  # Set the name dynamically
        self.udp_port = UDP_PORT
        self.buffer_size = BUFFER_SIZE

    def safe_recv(self, sock, size):
        """
        Helper: Ensures exactly 'size' bytes are received from the socket.
        Crucial for TCP because packets can be fragmented.
        """
        data = b''
        while len(data) < size:
            # Receive whatever is available up to the remaining needed amount
            chunk = sock.recv(size - len(data))
            if not chunk:
                raise Exception("Connection closed unexpectedly")
            data += chunk
        return data

    def listen_for_offer(self):
        """
        Listens for UDP broadcast messages from a Blackjack server.
        Returns:
            (server_ip, server_port) tuple when a valid offer is found.
        """

        # 1. Get the real Wi-Fi IP to ensure we listen on the correct network adapter
        my_ip = utils.get_local_ip()
        print(f"--- Client started, listening for offers at {my_ip} on port {self.udp_port} ---")

        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Allow multiple applications to listen on the same port
        try:
            udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except AttributeError:
            # Fallback for OS that don't support SO_REUSEPORT
            udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # 2. Bind only to the real IP
        try:
            udp_socket.bind((my_ip, self.udp_port))
        except:
            print(Colors.loss(f"Warning: Could not bind to {my_ip}, falling back to all interfaces."))
            udp_socket.bind(('', self.udp_port))

        # Set a timeout so the loop wakes up every second to check for Ctrl+C
        udp_socket.settimeout(1.0)

        while True:
            try:
                # Wait for a packet (max 1 second)
                data, addr = udp_socket.recvfrom(self.buffer_size)

                try:
                    # Validate the packet magic cookie and type
                    offer = protocol.unpack_offer(data)
                    if offer:
                        print(f"Received Offer from '{offer['server_name']}' at {addr[0]}")
                        return addr[0], offer['server_port']
                except Exception:
                    pass # Ignore invalid packets (garbage data)

            except socket.timeout:
                # Loop again to check for interrupts
                continue
            except Exception as e:
                print(f"Error: {e}")

    def connect_to_server(self, server_ip, server_port, rounds_to_play):
        """
        Main Game Loop.
        Connects via TCP, plays the requested rounds, and handles user input.
        """
        print(f"Connecting to {server_ip}:{server_port}...")
        try:
            # Establish TCP connection
            tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcp_socket.connect((server_ip, server_port))
            print(Colors.win("Connected!"))

            # Send the initial Request Packet (Name + Rounds)
            request_packet = protocol.pack_request(self.team_name, rounds_to_play)
            tcp_socket.sendall(request_packet)

            wins = 0

            # --- Start Rounds ---
            for round_num in range(1, rounds_to_play + 1):
                print(f"\n{'=' * 15} ROUND {round_num} / {rounds_to_play} {'=' * 15}")

                my_hand_ranks = []
                dealer_hand_ranks = []
                round_over = False

                # --- 1. Initial Deal (Player gets 2 cards) ---
                for i in range(2):
                    if round_over: break

                    # Read exactly 9 bytes (Header + Payload)
                    data = self.safe_recv(tcp_socket, 9)
                    msg = protocol.unpack_payload_server(data)

                    # Store rank to calculate stats
                    my_hand_ranks.append(msg['rank'])
                    current_score = calculate_hand_score(my_hand_ranks)

                    card_text = Colors.card(utils.get_card_name(msg['rank'], msg['suit']))
                    print(f"My Card {i + 1}: {card_text}")

                if round_over:
                    continue

                print(f"--> My Total: {Colors.win(str(current_score))}")

                # --- 2. Dealer Initial Card ---
                data = self.safe_recv(tcp_socket, 9)
                msg = protocol.unpack_payload_server(data)

                dealer_hand_ranks.append(msg['rank'])
                print(f"Dealer Shows: {Colors.card(utils.get_card_name(msg['rank'], msg['suit']))}")

                # --- 3. Player Decision Loop ---
                while True:
                    # Calculate Probability of Busting vs Safe Hit
                    bust_prob, safe_prob = calculate_stats(my_hand_ranks)

                    if current_score < 21:
                        print(
                            f"Stats: Bust Chance {Colors.loss(f'{bust_prob:.0f}%')} | Safe Hit Chance {Colors.win(f'{safe_prob:.0f}%')}")

                    choice = input("Your move? (h)it or (s)tand: ").lower()

                    # === Player Hits ===
                    if choice in ['h', ACTION_HIT]:
                        tcp_socket.sendall(protocol.pack_payload_client(ACTION_HIT))

                        data = self.safe_recv(tcp_socket, 9)
                        msg = protocol.unpack_payload_server(data)

                        # Update hand and score
                        my_hand_ranks.append(msg['rank'])
                        current_score = calculate_hand_score(my_hand_ranks)
                        card_name = utils.get_card_name(msg['rank'], msg['suit'])

                        if msg['result'] == RESULT_NOT_OVER:
                            print(f"Dealt: {Colors.card(card_name)} | Total: {Colors.win(str(current_score))}")
                        else:
                            # Server said we lost (Bust)
                            print(f"Dealt: {Colors.card(card_name)} | Total: {Colors.loss(str(current_score))}")
                            print(Colors.loss("👮‍♂️ YOU BUSTED! 👮‍♂️"))
                            break

                    # === Player Stands ===
                    elif choice in ['s', ACTION_STAND]:
                        tcp_socket.sendall(protocol.pack_payload_client(ACTION_STAND))
                        print(f"Standing on {current_score}. Dealer's turn...")

                        # Wait for Dealer to finish their turn
                        while True:
                            data = self.safe_recv(tcp_socket, 9)
                            msg = protocol.unpack_payload_server(data)
                            card_name = utils.get_card_name(msg['rank'], msg['suit'])

                            if msg['result'] == RESULT_NOT_OVER:
                                # Dealer drew a card but game isn't over
                                dealer_hand_ranks.append(msg['rank'])
                                dealer_score = calculate_hand_score(dealer_hand_ranks)
                                print(f"Dealer draws: {Colors.card(card_name)}")
                            else:
                                # Game Over packet received
                                dealer_score = calculate_hand_score(dealer_hand_ranks)
                                print(f"Dealer's Final Total: {dealer_score}")

                                if msg['result'] == RESULT_WIN:
                                    print(Colors.win("✴✴ YOU WIN! ✴✴"))
                                    wins += 1
                                elif msg['result'] == RESULT_LOSS:
                                    print(Colors.loss("🤬 YOU LOST! 🤬"))
                                elif msg['result'] == RESULT_TIE:
                                    print("☞ IT'S A TIE! ☜")
                                break
                        break

            # --- Session Summary ---
            if rounds_to_play > 0:
                win_rate = (wins / rounds_to_play) * 100
            else:
                win_rate = 0.0
            print(f"\n{'=== SESSION SUMMARY ==='}")
            print(f"Finished {rounds_to_play} rounds. Win Rate: {Colors.win(f'{win_rate:.1f}%')}")

        except Exception as e:
            print(f"Error: {e}")

        finally:
            if tcp_socket: tcp_socket.close()
            print(Colors.loss("--- Disconnected ---"))

if __name__ == "__main__":
    # 1. Ask for Team Name once at the start
    my_name = input("Enter your team name: ")
    if not my_name.strip():
        my_name = ""  # Default fallback
        print(f"Defaulting to '{my_name}'")

    # 2. Initialize client with the name
    client = BlackjackClient(my_name)

    while True:
        try:
            # --- CHECK FOR EXIT COMMAND HERE ---
            user_input = input("\nHow many rounds do you want to play? (type 'exit' for exit): ")

            if user_input.lower() == 'exit':
                print(Colors.card("Goodbye!"))
                sys.exit()

            user_rounds = int(user_input)

        except ValueError:
            user_rounds = 3
            print(Colors.loss("Invalid number, defaulting to 3 rounds."))

        server_ip, server_port = client.listen_for_offer()
        client.connect_to_server(server_ip, server_port, user_rounds)