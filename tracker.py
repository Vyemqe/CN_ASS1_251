# tracker.py - Tracker Server cho Hybrid Chat (phần 2.2)
import socket
import threading
import argparse
from datetime import datetime

# Storage peers: {username: (ip, port)}
PEERS = {}
PEERS_LOCK = threading.Lock()

def add_peer(username, ip, port):
    with PEERS_LOCK:
        PEERS[username] = (ip, int(port))
        print(f"[Tracker] Register peer: {username} at {ip}:{port}")

def lookup_peer(username):
    with PEERS_LOCK:
        return PEERS.get(username)

def handle_tracker_client(conn, addr):
    import json
    try:
        data = conn.recv(1024).decode('utf-8').strip()
        if data.startswith('REGISTER:'):
            parts = data.split(':')
            if len(parts) != 4:
                conn.send(b'NAK:Invalid format (expected REGISTER:username:ip:port)')
                return
            cmd, username, ip, port_str = parts
            if not port_str:
                conn.send(b'NAK:Port cannot be empty')
                return
            try:
                port = int(port_str)
                if not (1024 <= port <= 65535):
                    conn.send(b'NAK:Port must be between 1024 and 65535')
                    return
            except ValueError:
                conn.send(b'NAK:Invalid port value (must be an integer)')
                return
            add_peer(username, ip, port)
            conn.send(b'ACK:Registered')
        elif data.startswith('LOOKUP:'):
            parts = data.split(':')
            if len(parts) != 2:
                conn.send(b'NAK:Invalid format (expected LOOKUP:target_username or LOOKUP:*)')
                return
            
            cmd, target = parts
            if target == '*':
                # LOOKUP tất cả peers - trả JSON list
                with PEERS_LOCK:
                    peers_list = [{'username': k, 'ip': v[0], 'port': v[1]} for k, v in PEERS.items()]
                peers_json = json.dumps({'peers': peers_list})
                full_response = f"PEERS:{peers_json}\n"
                conn.send(full_response.encode('utf-8'))
                print(f"[Tracker] Trả LOOKUP:* {len(peers_list)} peers")
            else:
                # LOOKUP peer cụ thể
                peer_info = lookup_peer(target)
                if peer_info:
                    full_response = f"FOUND:{peer_info[0]}:{peer_info[1]}\n"
                    conn.send(full_response.encode('utf-8'))
                    print(f"[Tracker] Trả FOUND cho {target}: {peer_info[0]}:{peer_info[1]}")
                else:
                    conn.send(b'NAK:Peer not found\n')
                    print(f"[Tracker] NAK cho LOOKUP:{target} - không tồn tại")
        else:
            conn.send(b'NAK:Unknown command')
            print(f"[Tracker] NAK: Unknown command '{data}'")
    except Exception as e:
        print(f"[Tracker] Lỗi xử lý client {addr}: {e}")
    finally:
        conn.close()

def run_tracker(ip, port):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((ip, port))
    server.listen(5)
    print(f"[Tracker] Listening on {ip}:{port}")
    while True:
        conn, addr = server.accept()
        print(f"[Tracker] Accepted connection from {addr}")
        client_thread = threading.Thread(target=handle_tracker_client, args=(conn, addr), daemon=True)
        client_thread.start()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chạy Tracker Server")
    parser.add_argument('--ip', default='0.0.0.0')
    parser.add_argument('--port', type=int, default=9000)
    args = parser.parse_args()
    run_tracker(args.ip, args.port)