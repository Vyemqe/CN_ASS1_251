#
# Copyright (C) 2025 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course,
# and is released under the "MIT License Agreement". Please see the LICENSE
# file that should have been included as part of this package.
#
# WeApRous release
#
# The authors hereby grant to Licensee personal permission to use
# and modify the Licensed Source Code for the sole purpose of studying
# while attending the course
#


"""
start_sampleapp
~~~~~~~~~~~~~~~~~

This module provides a sample RESTful web application using the WeApRous framework.

It defines basic route handlers and launches a TCP-based backend server to serve
HTTP requests. The application includes a login endpoint and a greeting endpoint,
and can be configured via command-line arguments.
"""

# import json
# import socket
import argparse

from daemon.weaprous import WeApRous
from daemon.networkmode import NetworkManager   # network layer
from daemon.tracker import Tracker
from daemon.peer import Peer

PORT = 8000  # Default port

app = WeApRous()

tracker = Tracker()   # TODO: Place your tracker obj here!

@app.route('/login', methods=['POST'])
def login(headers="guest", body="anonymous"):
    """
    Handle user login via POST request.

    This route simulates a login process and prints the provided headers and body
    to the console.

    :param headers (str): The request headers or user identifier.
    :param body (str): The request body or login payload.
    """
    print("[SampleApp] Logging in {} to {}".format(headers, body))

@app.route('/hello', methods=['PUT'])
def hello(headers, body):
    """
    Handle greeting via PUT request.

    This route prints a greeting message to the console using the provided headers
    and body.

    :param headers (str): The request headers or user identifier.
    :param body (str): The request body or message payload.
    """
    print("[SampleApp] ['PUT'] Hello in {} to {}".format(headers, body))

### Add more endpoints here ###
#! Client-Server
#? 1. submit-info/ - PUT
@app.route('/submit-info', methods=['PUT'])
def submit_info(headers, body) -> None:
    """
    Handle submission of user information: IP, port via PUT request.

    This route processes the submitted user information and prints it to the console.

    :param headers (str): The request headers or user identifier.
    :param body (str): The request body containing user information.
    """
    global tracker      # TODO: Change this to your tracker obj
    ip, port = body.split(':')
    peer = {'ip': ip, 'port': port}
    tracker.register_peer(peer)
    print("[SampleApp] New peer joined: {}".format(peer))

#? 2. add-list/ - POST
@app.route('/add-list', methods=['POST'])
def add_list(headers, body) -> dict:
    """
    Handle adding an item to a list via POST request.

    This route processes the item to be added and prints it to the console.

    :param headers (str): The request headers or user identifier.
    :param body (str): The request body containing the item to add.
    """
    # print("[SampleApp] ['POST'] Add list in {} to {}".format(headers, body))
    global tracker      # TODO: Change this to your tracker obj
    try:
        # Assume JSON body: [{"ip": "192.168.1.2", "port": 9000}, ...]
        import json
        new_peers = json.loads(body)

        added = 0
        for peer in new_peers:
            tracker.register_peer(peer)
            added += 1

        print("[SampleApp] Added {} new peers via /add-list/".format(added))
        print("[SampleApp] Updated tracker: {}".format(tracker))
        return {"status": "success", "added": added}

    except Exception as e:
        print(f"[SampleApp] ['POST'] /add-list error: {e}")
        return {"status": "error", "message": str(e)}

#? 3. get-list/ - GET
@app.route('/get-list', methods=['GET'])
def get_list(headers, body) -> list:
    """
    Handle tracking list of peers via GET request.

    This route processes the request to retrieve a list and prints it to the console.

    :param headers (str): The request headers or user identifier.
    :param body (str): The request body containing any parameters for retrieval.
    """
    global tracker      # TODO: Change this to your tracker obj
    peers = tracker.get_peers()
    print("[SampleApp] Current list of peers: {}".format(peers))
    return peers

#? 4. connect/peer/ - POST
@app.route('/connect/peer', methods=['POST'])
def connect_peer(headers, body) -> None:
    """
    Handle connecting to a peer via POST request.

    This route processes the connection request and prints it to the console.

    :param headers (str): The request headers or user identifier.
    :param body (str): The request body containing peer connection details.
    """
    print("[SampleApp] Connecting to peer: {}".format(body))

#! P2P
#? 1. broadcast-peer/ - POST
@app.route('/broadcast-peer', methods=['POST'])
def broadcast_peer(headers, body) -> None:
    """
    Handle broadcasting peer information via POST request.

    This route processes the broadcast request and prints it to the console.

    :param headers (str): The request headers or user identifier.
    :param body (str): The request body containing peer information to broadcast.
    """
    print("[SampleApp] Broadcasting message to all peers: {}".format(body))
    NetworkManager.broadcast(body)

#? 2. send-peer/ - PUT
@app.route('/send-peer', methods=['PUT'])
def send_peer(headers, body) -> None:
    """
    Handle message exchanging between peers via PUT request.

    This route processes the send request and prints it to the console.

    :param headers (str): The request headers or user identifier.
    :param body (str): The request body containing peer information to send.
    """
    print("[SampleApp] Sending message directly to a peer: {}".format(body))
    NetworkManager.send_to_peer(body)

if __name__ == "__main__":
    # Parse command-line arguments to configure server IP and port
    parser = argparse.ArgumentParser(prog='Backend', description='', epilog='Beckend daemon')
    parser.add_argument('--server-ip', default='0.0.0.0')
    parser.add_argument('--server-port', type=int, default=PORT)
    #! For network layer
    parser.add_argument('--mode', choices=['cs', 'p2p'], default='cs',
                        help='Network mode: cs (Client-Server), p2p (Peer-to-Peer).')
 
    args = parser.parse_args()
    ip = args.server_ip
    port = args.server_port
    mode = args.mode
    
    #! Initialize network manager based on mode
    network = NetworkManager(mode=mode, ip=ip, port=port)
    network.setup_network()

    # Prepare and launch the RESTful application
    app.prepare_address(ip, port)
    app.run()