import socket
import time
import threading
import random
import protocol
from protocol import *
import utils

# --- Game Logic Class ---
class Deck:

    def __init__(self):
        self.cards = []
        self.reset_deck()

    def reset_deck(self):
        self.cards = []

        # Generate 52 cards: 4 suits (0-3) x 13 ranks (1-13)
        for suit in range(4):
            for rank in range(1, 14):
                self.cards.append((rank, suit))

        # Shuffle the deck randomly
        random.shuffle(self.cards)

    def draw_card(self):
        # Remove and return the last card in the list
        return self.cards.pop()

    def calculate_score(self, hand):
        score = 0
        aces = 0

        # First pass: Count Aces as 11
        for rank, suit in hand:
            if rank == 1:    # Ace
                aces += 1
                score += 11
            elif rank >= 11: # J/Q/K
                score += 10
            else:            # Number cards
                score += rank

        # Second pass: If busted (>21), convert Aces from 11 to 1
        while score > 21 and aces > 0:
            score -= 10
            aces -= 1

        return score

# --- Server Class ---
class BlackjackServer:
    """
    Manages the Blackjack server.
    - Broadcasts availability via UDP.
    - Accepts client connections via TCP.
    - Manages game logic (Deck, Dealing, Scoring) for each client in a separate thread.
    """

    def __init__(self):
        self.tcp_port = 0
        self.server_name = "bl\033[1mACK\033[0mj\033[1mACK\033[0m"
        self.running = True

    def start_udp_broadcast(self):
        """
        Runs in a background thread. Broadcasts offer messages so clients can find the server.
        """

        # Find the real Wi-Fi IP to ensure broadcast works on LAN
        my_ip = utils.get_local_ip()
        print(f"--- Server started, broadcasting from {my_ip} on UDP {UDP_PORT} ---")

        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # Bind to the specific interface to force traffic through the correct adapter
            udp_socket.bind((my_ip, 0))
        except Exception as e:
            print(f"Warning: Could not bind broadcast socket to {my_ip}: {e}")

        # Enable Broadcast mode
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        while self.running:
            try:
                # specific protocol message with TCP port
                msg = protocol.pack_offer(self.tcp_port, self.server_name)
                # Send to everyone (255.255.255.255)
                udp_socket.sendto(msg, ('255.255.255.255', UDP_PORT))
                time.sleep(1)
            except Exception as e:
                print(f"UDP Broadcast Error: {e}")

    def handle_client(self, client_conn):
        """
        Handles a single client connection (Game Loop).
        """

        try:
            print(f"Starting game with {client_conn.getpeername()}")

            # --- 1. Handshake ---
            # Wait for the Client to send their "Request" message
            data = client_conn.recv(BUFFER_SIZE)
            # Convert raw bytes -> Python Dictionary
            request = protocol.unpack_request(data)

            # If the packet was invalid or not a Request - disconnect immediately
            if not request:
                client_conn.close()
                return

            # Extract the Game Settings from the dictionary
            total_rounds = request['rounds']
            team_name = request['team_name']

            print(f"Team '{team_name}' joined for {total_rounds} rounds.")

            # --- 2. Rounds Loop ---
            for round_num in range(1, total_rounds + 1):
                print(f"\n--- Round {round_num} / {total_rounds} vs {team_name} ---")

                # New Deck and hands for every round
                deck = Deck()
                player_hand = []
                dealer_hand = []
                player_busted = False

                # --- 3. Deal Player ---
                print("Dealing to player...")
                for _ in range(2):
                    card = deck.draw_card()
                    player_hand.append(card)
                    print(f"  Player got: {utils.get_card_name(card[0], card[1])}")

                    score = deck.calculate_score(player_hand)
                    if score > 21:
                        msg = protocol.pack_payload_server(RESULT_LOSS, card[0], card[1])
                        client_conn.sendall(msg)
                        player_busted = True
                        break
                    else:
                        msg = protocol.pack_payload_server(RESULT_NOT_OVER, card[0], card[1])
                        client_conn.sendall(msg)

                if not player_busted:
                    # --- 4. Deal Dealer ---
                    dealer_visible = deck.draw_card()
                    dealer_hidden = deck.draw_card()
                    dealer_hand = [dealer_visible, dealer_hidden]
                    print(f"Dealer shows: {utils.get_card_name(dealer_visible[0], dealer_visible[1])}")

                    # Send only the visible card to client
                    msg = protocol.pack_payload_server(RESULT_NOT_OVER, dealer_visible[0], dealer_visible[1])
                    client_conn.sendall(msg)

                    # --- 5. Player Moves (Hit/Stand) ---
                    while True:
                        # Wait for client to send "Hit" or "Stand"
                        data = client_conn.recv(BUFFER_SIZE)
                        msg = protocol.unpack_payload_client(data)
                        # Stop if connection lost/invalid
                        if not msg: break

                        # --- CASE A: Player Stands ---
                        if msg['decision'] == ACTION_STAND:
                            print(f"Player Stand. Score: {deck.calculate_score(player_hand)}")
                            # Exit loop, turn is over
                            break

                        # --- CASE B: Player Hits ---
                        if msg['decision'] == ACTION_HIT:
                            print("Player Hit.")
                            new_card = deck.draw_card()
                            player_hand.append(new_card)
                            print(f"  Player got: {utils.get_card_name(new_card[0], new_card[1])}")

                            # Check if this new card caused a Bust (>21)
                            score = deck.calculate_score(player_hand)

                            if score > 21:
                                print(f"  Player Busted! Score: {score}")
                                # Send LOSS immediately. Round ends for player.
                                msg = protocol.pack_payload_server(RESULT_LOSS, new_card[0], new_card[1])
                                client_conn.sendall(msg)
                                player_busted = True
                                break
                            else:
                                # Send the card and keep the loop running
                                msg = protocol.pack_payload_server(RESULT_NOT_OVER, new_card[0], new_card[1])
                                client_conn.sendall(msg)

                # --- 6. Dealer Moves ---
                if not player_busted:
                    # Reveal the hidden card to the client first
                    print(f"Dealer reveals hidden: {utils.get_card_name(dealer_hidden[0], dealer_hidden[1])}")
                    msg = protocol.pack_payload_server(RESULT_NOT_OVER, dealer_hidden[0], dealer_hidden[1])
                    client_conn.sendall(msg)

                    dealer_score = deck.calculate_score(dealer_hand)

                    # Dealer must hit until 17
                    while dealer_score < 17:
                        time.sleep(0.5) # Small delay for realism
                        new_card = deck.draw_card()
                        dealer_hand.append(new_card)
                        dealer_score = deck.calculate_score(dealer_hand)
                        print(f"  Dealer draws: {utils.get_card_name(new_card[0], new_card[1])}")

                        # Send new card to client (Game still running)
                        msg = protocol.pack_payload_server(RESULT_NOT_OVER, new_card[0], new_card[1])
                        client_conn.sendall(msg)

                    # --- 7. Determine Winner ---
                    player_score = deck.calculate_score(player_hand)
                    last_card = dealer_hand[-1]
                    print(f"Scores -> Player: {player_score} | Dealer: {dealer_score}")

                    # Compare scores to find the winner
                    if dealer_score > 21:
                        print("Dealer Busted. Player Wins!")
                        result = RESULT_WIN
                    elif player_score > dealer_score:
                        print("Player Wins!")
                        result = RESULT_WIN
                    elif player_score < dealer_score:
                        print("Dealer Wins.")
                        result = RESULT_LOSS
                    else:
                        print("It's a Tie.")
                        result = RESULT_TIE

                    # Send Final Result (Win/Loss/Tie) attached to the last card info
                    msg = protocol.pack_payload_server(result, last_card[0], last_card[1])
                    client_conn.sendall(msg)

                time.sleep(1)

            # --- End of Session ---
            print(f"Finished {total_rounds} rounds. Closing connection.")
            client_conn.close()

        except Exception as e:
            print(f"Game Error: {e}")
        finally:
            client_conn.close()

    def start_server(self):
        """
        Main entry point. Starts TCP listener and UDP broadcaster.
        """

        # Create a TCP socket (SOCK_STREAM) for game connections
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind(('', 0))

        # Retrieve the actual port number assigned by the OS
        self.tcp_port = server_socket.getsockname()[1]
        print(f"Listening for TCP connections on port {self.tcp_port}")

        # Start listening for incoming connections
        server_socket.listen()

        # Start the UDP Broadcast in a background thread (daemon=True kills it when main ends)
        udp_thread = threading.Thread(target=self.start_udp_broadcast)
        udp_thread.daemon = True
        udp_thread.start()

        # Set a timeout so the loop can check 'self.running' every second
        server_socket.settimeout(1.0)

        try:
            while self.running:
                try:
                    # distinct 'accept' call creates a new socket for the incoming client
                    client_socket, client_address = server_socket.accept()

                    # Start a dedicated thread for this client's game
                    client_handler = threading.Thread(target=self.handle_client, args=(client_socket,))
                    client_handler.start()

                except socket.timeout:
                    continue # No client connected this second, loop again

        except KeyboardInterrupt:
            self.running = False
        finally:
            server_socket.close()

if __name__ == "__main__":
    # Main entry point: Initialize and start the server
    server = BlackjackServer()
    server.start_server()