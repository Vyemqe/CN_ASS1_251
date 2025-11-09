import socket
import threading

PORT = 8000     # Default port if --server-port is not provided

class NetworkManager:
    peers = []  # List to store peer information for mode='p2p'
                # format: peers = [(conn, addr), ...]
    def __init__(self, mode='cs', ip='0.0.0.0', port=PORT):
        self.mode = mode
        self.ip = ip
        self.port = port
        self.server_socket = None
    
    ### UTILITIES ###
    def setup_network(self):
        if self.mode == 'cs':
            print("[NetworkManager] Setting up Client-Server mode on {}:{}".format(self.ip, self.port))
            self.start_cs()
        else:
            print("[NetworkManager] Setting up Peer-to-Peer mode on {}:{}".format(self.ip, self.port))
            self.start_p2p()

    ### CLIENT - SERVER ###
    def start_cs(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)    # IPv4, TCP
        try:
            self.server_socket.bind((self.ip, self.port))
            self.server_socket.listen(50)
            print("[CS Mode] Listening on {}:{}".format(self.ip, self.port))
            while True:
                conn, addr = self.server_socket.accept()
                print("[CS Mode] Accepted connection from {}:{}".format(addr[0], addr[1]))
                clientThread = threading.Thread(
                    target=self.accept_cs_client,
                    args=(conn, addr),
                    daemon=True
                )
                clientThread.start()
        except socket.error as e:
            print("Socket error in CS mode: {}".format(e))
    
    def accept_cs_client(self, conn, addr):
        """
        Accept and handle a client connection in Client-Server mode.

        :param conn (socket.socket): Client connection socket.
        :param addr (tuple): Client address (IP, port).
        """
        while True:
            conn, addr = self.server_socket.accept()
            print("[CS Mode] Handling client {}:{}".format(addr[0], addr[1]))
            clientThread = threading.Thread(
                                target=self.handle_cs_client,
                                args=(conn, addr),
                                daemon=True
                            )
            clientThread.start()
        
    def handle_cs_client(self, conn, addr):
        """
        Handle client connections in Client-Server mode.

        :param conn (socket.socket): Client connection socket.
        :param addr (tuple): Client address (IP, port).
        """
        try:
            msg = conn.recv(1024).decode('utf-8')
            print("[CS Mode] Received from {}: {}".format(addr, msg))
            # response = "Echo from CS server: " + msg
            # conn.sendall(response.encode('utf-8'))
        except Exception as e:
            print("[CS Mode] Error handling client {}: {}".format(addr, e))
        finally:
            conn.close()
    
    ### PEER - TO - PEER ###
    def start_p2p(self) -> None:
        peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        peer_socket.bind((self.ip, self.port))
        peer_socket.listen(5)
        print("[P2P Mode] Listening for peers on {}:{}".format(self.ip, self.port))
        peerThread = threading.Thread(
                        target=self.accept_peers,
                        args=(peer_socket,),
                        daemon=True
                    )
        peerThread.start()
    
    def accept_peers(self, peer_socket) -> None:
        """
        Accept incoming peer connections in Peer-to-Peer mode.

        :param server_socket (socket.socket): The server socket to accept connections on.
        """
        while True:
            conn, addr = peer_socket.accept()
            print("[P2P Mode] Accepted peer connection from {}:{}".format(addr[0], addr[1]))
            NetworkManager.peers.append((conn, addr))
            peerThread = threading.Thread(
                            target=self.handle_peer_connections,
                            args=(conn,addr),
                            daemon=True
                        )
            peerThread.start()
    
    def handle_peer_connections(self, conn, addr) -> None:
        while True:
            try:
                msg = conn.recv(1024).decode('utf-8')
                if not msg:
                    break
                print("[P2P Mode] Message received from {}: {}".format(addr, msg))
            except:
                break
        print("[P2P Mode] Peer {} disconnected".format(addr))
        NetworkManager.peers.remove((conn, addr))
        conn.close()
    
    def broadcast(self, message) -> None:
        """
        Broadcast a message to all connected peers.

        :param message (str): The message to broadcast.
        """
        for conn, addr in NetworkManager.peers:
            try:
                conn.sendall(message.encode('utf-8'))
                print("[P2P Mode] Sent to {}: {}".format(addr, message))
            except Exception as e:
                print("[P2P Mode] Error sending to {}: {}".format(addr, e))
    
    def send_to_peer(self, message: str) -> None:
        """
        Send a message directly to a specific peer.

        :param message (str): The message to send.
        """
        # Sample format: 'ip:port| msg'
        try:
            dest, msg = message.split('|', 2)   # Maybe changed to 1???
            dest_ip, dest_port = dest.strip().split(':')
            dest_port = int(dest_port)

            peer_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # IPv4 & UDP
            peer_socket.connect((dest_ip, dest_port))
            peer_socket.sendall(msg.strip().encode('utf-8'))
            print("[P2P Mode] Message is directly sent to {}:{}".format(dest, msg.strip()))
            peer_socket.close()
        except:
            print("[P2P Mode] Cannot forward to peer {}".format(dest))
        