import socket
import threading
import json
import time
import argparse
from datetime import datetime


class Peer:
    """
    Class Peer đại diện cho peer process trong hybrid chat application.
    Hỗ trợ đăng ký với tracker, khám phá peers, gửi/nhận tin nhắn P2P qua TCP socket,
    và polling messages. Tích hợp concurrency qua threading cho multi-peer connections.
    """
    
    def __init__(self, username, listen_port, tracker_host='localhost', tracker_port=9000):
        """
        Khởi tạo Peer.
        :param username: Tên peer (để đăng ký và gửi tin nhắn).
        :param listen_port: Port lắng nghe P2P connections.
        :param tracker_host: Host của tracker server.
        :param tracker_port: Port của tracker server.
        """
        self.username = username
        self.listen_port = listen_port
        self.tracker_host = tracker_host
        self.tracker_port = tracker_port
        self.peers = {}  # Cache peers: {username: (ip, port)}
        self.messages = []  # Lưu lịch sử tin nhắn local
        self.running = True
        self.listener_thread = None
        self.lock = threading.Lock()  # Thread-safe cho shared data
        
    def register(self):
        """
        Đăng ký với tracker (tương ứng fetch('/register')).
        Gửi lệnh REGISTER qua socket TCP.
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.tracker_host, self.tracker_port))
            local_ip = socket.gethostbyname(socket.gethostname())
            msg = f"REGISTER:{self.username}:{local_ip}:{self.listen_port}"
            sock.send(msg.encode('utf-8'))
            response = sock.recv(1024).decode('utf-8').strip()
            print("peer res:  " + response)
            sock.close()
            if response.startswith('ACK'):
                print(f"[Peer {self.username}] Đăng ký thành công: {response}")
                return True
            else:
                print(f"[Peer {self.username}] Đăng ký thất bại: {response}")
        except socket.error as e:
            print(f"[Peer {self.username}] Lỗi kết nối tracker: {e}")
        return False
    
    def load_peers(self):
        """
        Tải danh sách peers từ tracker (tương ứng fetch('/peers')).
        Giả lập qua socket LOOKUP * (hoặc endpoint HTTP trong backend).
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.tracker_host, self.tracker_port))
            msg = "LOOKUP:*"  # Lệnh lookup tất cả peers
            sock.send(msg.encode('utf-8'))
            response = sock.recv(2048).decode('utf-8').strip()  # Response có thể là JSON
            sock.close()
            if response.startswith('PEERS:'):
                # Giả lập parse JSON từ response (backend trả {'peers': [{'ip': 'x.x.x.x', 'port': 8001}]})
                peers_data = json.loads(response[6:])  # Bỏ prefix 'PEERS:'
                with self.lock:
                    self.peers = {p['username']: (p['ip'], p['port']) for p in peers_data['peers']}
                print(f"[Peer {self.username}] Đã tải {len(self.peers)} peers.")
                return list(self.peers.values())
            else:
                print(f"[Peer {self.username}] Không tải được peers: {response}")
        except (socket.error, json.JSONDecodeError) as e:
            print(f"[Peer {self.username}] Lỗi load peers: {e}")
        return []
    
    def send_message(self, target_username, msg):
    # Lookup target address
        if target_username in self.peers:
            ip, port = self.peers[target_username]
            addr = (ip, port)
            #print(f"[Peer {self.username}] Sử dụng cache cho {target_username} tại {addr}")
        else:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((self.tracker_host, self.tracker_port))
                lookup_cmd = f"LOOKUP:{target_username}"
                sock.send(lookup_cmd.encode('utf-8'))
                response = sock.recv(2048).decode('utf-8').strip()
                sock.close()
                if response.startswith('FOUND:'):
                    parts = response[6:].split(':')
                    if len(parts) == 2:
                        ip, port_str = parts
                        port = int(port_str)
                        addr = (ip, port)  # Fixed: Use tuple (ip, port) for connect
                        with self.lock:
                            self.peers[target_username] = addr
                        print(f"[Peer {self.username}] Found {target_username} at {addr}")
                    else:
                        print(f"[Peer {self.username}] Invalid response format: {response}")
                        return False
                else:
                    print(f"[Peer {self.username}] Peer not found: {response}")
                    return False
            except (socket.error, ValueError) as e:
                print(f"[Peer {self.username}] Lookup error: {e}")
                return False

            # Send P2P message
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(addr)
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            message_data = {
                'time': timestamp,
                'sender': self.username,
                'msg': msg
            }
            full_msg = f"MESSAGE:{json.dumps(message_data)}"
            sock.send(full_msg.encode('utf-8'))
            ack = sock.recv(1024).decode('utf-8').strip()
            sock.close()
            if ack.startswith('ACK'):
                with self.lock:
                    self.messages.append(message_data)
                print(f"[Peer {self.username}] Sent to {target_username}: {msg}")
                return True
            else:
                print(f"[Peer {self.username}] Send failed: {ack}")
        except socket.error as e:
            print(f"[Peer {self.username}] Send error: {e}")
        return False

    def broadcast_message(self, msg):
        """
        Broadcast tin nhắn đến tất cả peers (sử dụng load_peers để refresh danh sách).
        """
        self.load_peers()  # Refresh peer list
        success_count = 0
        for target_username, (ip, port) in self.peers.items():
            if target_username != self.username:  # Avoid self-send
                if self.send_message(target_username, msg):
                    success_count += 1
        print(f"[Peer {self.username}] Broadcast to {success_count}/{len(self.peers)-1} peers: {msg}")
        return success_count > 0
    
    def load_messages(self):
        """
        Tải tin nhắn (tương ứng fetch('/messages')).
        Polling từ tracker hoặc local cache; ở đây dùng local để demo.
        """
        return self.messages
    
    def start_listener(self):
        """
        Khởi động socket server để nhận P2P messages (multi-peer concurrency).
        Sử dụng threading để xử lý mỗi connection riêng biệt.
        """
        def handle_connection(conn, addr):
            try:
                data = conn.recv(2048).decode('utf-8').strip()
                if data.startswith('MESSAGE:'):
                    msg_data = json.loads(data[8:])  # Parse JSON message
                    with self.lock:
                        self.messages.append(msg_data)
                    print(f"[Peer {self.username}] Nhận từ {msg_data['sender']}: {msg_data['msg']}")
                    conn.send(b'ACK:Message received')
                else:
                    conn.send(b'NAK:Invalid message')
            except Exception as e:
                print(f"[Peer {self.username}] Lỗi xử lý connection: {e}")
            finally:
                conn.close()
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', self.listen_port))
        sock.listen(5)
        print(f"[Peer {self.username}] Lắng nghe P2P trên port {self.listen_port}")
        
        self.listener_thread = threading.Thread(target=self._accept_loop, args=(sock, handle_connection), daemon=True)
        self.listener_thread.start()
    
    def _accept_loop(self, sock, handler):
        while self.running:
            try:
                conn, addr = sock.accept()
                client_thread = threading.Thread(target=handler, args=(conn, addr), daemon=True)
                client_thread.start()
            except Exception as e:
                if self.running:
                    print(f"[Peer {self.username}] Lỗi accept: {e}")
    
    def run_cli(self):
        """
        Hỗ trợ lệnh: register, load_peers, send <target> <msg>, messages, quit.
        """
        if not self.register():
            return
        self.start_listener()
        print(f"[Peer {self.username}] Sẵn sàng. Lệnh: register | load_peers |broadcast <msg>| send <target> <msg> | messages | quit")
        while self.running:
            try:
                cmd = input("> ").strip().split()
                if not cmd:
                    continue
                if cmd[0] == 'register':
                    self.register()
                elif cmd[0] == 'load_peers':
                    self.load_peers()
                    print("Peers:", self.peers)
                elif cmd[0] == 'broadcast':
                    msg = ' '.join(cmd[1:])
                    self.broadcast_message(msg)
                elif cmd[0] == 'send' and len(cmd) >= 3:
                    target = cmd[1]
                    msg = ' '.join(cmd[2:])
                    self.send_message(target, msg)
                elif cmd[0] == 'messages':
                    msgs = self.load_messages()
                    for m in msgs[-5:]:  # Hiển thị 5 tin nhắn gần nhất
                        print(f"[{m['time']}] {m['sender']}: {m['msg']}")
                elif cmd[0] == 'quit':
                    self.running = False
                    break
                else:
                    print("Lệnh không hợp lệ.")
            except KeyboardInterrupt:
                self.running = False
                break
        print(f"[Peer {self.username}] Đang thoát.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Peer Client")
    parser.add_argument('--username', type=str, required=True, help="Tên peer (e.g., Alice)")
    parser.add_argument('--port', type=int, required=True, help="Port lắng nghe P2P (e.g., 8001)")
    parser.add_argument('--tracker-host', type=str, default='localhost', help="Host tracker (default: localhost)")
    parser.add_argument('--tracker-port', type=int, default=9000, help="Port tracker (default: 9000)")
    
    args = parser.parse_args()
    
    # Khởi tạo và test
    print(f"Khởi tạo Peer client: {args.username} trên port {args.port}")
    peer = Peer(args.username, args.port, args.tracker_host, args.tracker_port)
    
    # Test tự động: Đăng ký, load peers, gửi tin nhắn mẫu (nếu có target)
    print("Bước 1: Đăng ký với tracker...")
    if peer.register():
        print("Bước 2: Load danh sách peers...")
        peers = peer.load_peers()
        print(f"Tìm thấy {len(peers)} peers: {peers}")
        usernames = list(peer.peers.keys())
        # Test gửi tin nhắn (nếu có ít nhất 1 peer khác)
        if len(peers) > 1:
            target_usernames = [u for u in usernames if u != args.username]
            target =  target_usernames[0]
            print(f"Bước 3: Gửi tin nhắn mẫu đến {target}...")
            if peer.send_message(target, "Hello from test client!"):
                print("Gửi thành công.")
            else:
                print("Gửi thất bại.")
        
        # Chạy CLI để test tương tác
        print("\nChạy CLI test (gõ 'quit' để thoát)...")
        peer.run_cli()
    else:
        print("Lỗi đăng ký, không thể test.")