import threading

class Tracker:
    """Central tracker server to manage registered peers."""

    def __init__(self):
        self.lock = threading.Lock()
        self.peers = []  # list of dicts: [{'ip': '127.0.0.1', 'port': 5001}, ...]

    def register_peer(self, ip, port):
        with self.lock:
            if not any(p['ip'] == ip and p['port'] == port for p in self.peers):
                self.peers.append({'ip': ip, 'port': port})
                print(f"[Tracker] Registered new peer: {ip}:{port}")
            return {'status': 'ok', 'message': 'Peer registered successfully'}
        
    def register_peer(self, peer):
        return self.register_peer(ip = peer['ip'], port = peer['port'])

    def get_peers(self):
        with self.lock:
            return {'peers': self.peers}

    def remove_peer(self, ip, port):
        with self.lock:
            self.peers = [p for p in self.peers if not (p['ip'] == ip and p['port'] == port)]
            print(f"[Tracker] Removed peer: {ip}:{port}")
            return {'status': 'ok', 'message': 'Peer removed'}
