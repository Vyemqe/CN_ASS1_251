import socket
import threading

PORT = 8000     # Default port if --server-port is not provided

class NetworkManager:
    def __init__(self, mode='cs', ip='0.0.0.0', port=PORT):
        self.mode = mode
        self.ip = ip
        self.port = port
        self.peers = []     # List to store peer information for mode='p2p'
    
    ### UTILITIES ###
    def setup_network(self):
        if self.mode == 'cs':
            print("[NetworkManager] Setting up Client-Server mode on {}:{}".format(self.ip, self.port))
            self.start_cs()
        else:
            print("[NetworkManager] Setting up Peer-to-Peer mode on {}:{}".format(self.ip, self.port))
            self.start_p2p()

    def start_cs(self):
        cs_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)    # IPv4, TCP
        try:
            cs_server.bind((self.ip, self.port))
            cs_server.listen(50)
            print("[CS Mode] Listening on {}:{}".format(self.ip, self.port))
            while True:
                conn, addr = cs_server.accept()
                print("[CS Mode] Accepted connection from {}:{}".format(addr[0], addr[1]))
                clientThread = threading.Thread(
                    target=self.handle_cs_client,
                    args=(conn, addr),
                    daemon=True
                )
                clientThread.start()
        except socket.error as e:
            print("Socket error in CS mode: {}".format(e))
        
    def handle_cs_client(self, conn, addr):
        """
        Handle client connections in Client-Server mode.

        :param conn (socket.socket): Client connection socket.
        :param addr (tuple): Client address (IP, port).
        """
        try:
            data = conn.recv(1024).decode('utf-8')
            print("[CS Mode] Received from {}: {}".format(addr, data))
            response = "Echo from CS server: " + data
            conn.sendall(response.encode('utf-8'))
        except Exception as e:
            print("[CS Mode] Error handling client {}: {}".format(addr, e))
        finally:
            conn.close()
        