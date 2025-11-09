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

PORT = 8000  # Default port

app = WeApRous()

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
@app.routes('/submit-info', methods=['PUT'])
def submit_info(headers, body):
    """
    Handle submission of user information: IP, port via PUT request.

    This route processes the submitted user information and prints it to the console.

    :param headers (str): The request headers or user identifier.
    :param body (str): The request body containing user information.
    """
    print("[SampleApp - C/S] ['PUT'] Submit info in {} to {}".format(headers, body))

#? 2. add-list/ - POST
@app.routes('/add-list', methods=['POST'])
def add_list(headers, body):
    """
    Handle adding an item to a list via POST request.

    This route processes the item to be added and prints it to the console.

    :param headers (str): The request headers or user identifier.
    :param body (str): The request body containing the item to add.
    """
    print("[SampleApp - C/S] ['POST'] Add list in {} to {}".format(headers, body))

#? 3. get-list/ - GET
@app.routes('/get-list', methods = ['GET'])
def get_list(headers, body):
    """
    Handle tracking list of peers via GET request.

    This route processes the request to retrieve a list and prints it to the console.

    :param headers (str): The request headers or user identifier.
    :param body (str): The request body containing any parameters for retrieval.
    """
    print("[SampleApp - C/S] ['GET'] Get peer list in {} to {}".format(headers, body))

#? 4. connect/peer/ - POST
@app.routes('/connect/peer', methods=['POST'])
def connect_peer(headers, body):
    """
    Handle connecting to a peer via POST request.

    This route processes the connection request and prints it to the console.

    :param headers (str): The request headers or user identifier.
    :param body (str): The request body containing peer connection details.
    """
    print("[SampleApp - C/S] ['POST'] Connect peer in {} to {}".format(headers, body))

#! P2P
#? 1. broadcast-peer/ - POST
@app.routes('/broadcast-peer', methods=['POST'])
def broadcast_peer(headers, body):
    """
    Handle broadcasting peer information via POST request.

    This route processes the broadcast request and prints it to the console.

    :param headers (str): The request headers or user identifier.
    :param body (str): The request body containing peer information to broadcast.
    """
    print("[SampleApp - P2P] ['POST'] Broadcast peer in {} to {}".format(headers, body))

#? 2. send-peer/ - PUT
@app.routes('/send-peer', method = ['PUT'])
def send_peer(headers, body):
    """
    Handle message exchanging between peers via PUT request.

    This route processes the send request and prints it to the console.

    :param headers (str): The request headers or user identifier.
    :param body (str): The request body containing peer information to send.
    """
    print("[SampleApp - P2P] ['PUT'] Send peer in {} to {}".format(headers, body))

if __name__ == "__main__":
    # Parse command-line arguments to configure server IP and port
    parser = argparse.ArgumentParser(prog='Backend', description='', epilog='Beckend daemon')
    parser.add_argument('--server-ip', default='0.0.0.0')
    parser.add_argument('--server-port', type=int, default=PORT)
    #! For network layer
    parser.add_argument('--mode', choices=['cs', 'p2p'], default='cs',
                        help='Network mode: cs (Client-Server) or p2p (Peer-to-Peer).')
 
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