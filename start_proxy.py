# reverse_proxy.py
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
start_proxy
~~~~~~~~~~~~~~~~~

This module serves as the entry point for launching a proxy server using Python's socket framework.
It parses command-line arguments to configure the server's IP address and port, reads virtual host
definitions from a configuration file, and initializes the proxy server with routing information.

Requirements:
--------------
- socket: provide socket networking interface.
- threading: enables concurrent client handling via threads.
- argparse: parses command-line arguments for server configuration.
- re: used for regular expression matching in configuration parsing
- response: response utilities.
- httpadapter: the class for handling HTTP requests.
- urlparse: parses URLs to extract host and port information.
- daemon.create_proxy: initializes and starts the proxy server.

"""

# import socket
# import threading
import argparse
import re
from urllib.parse import urlparse
# from collections import defaultdict

from daemon import create_proxy

PROXY_PORT = 8080


def parse_virtual_hosts(config_file):
    """
    Parses virtual host blocks from a config file.

    :config_file (str): Path to the NGINX config file.
    :rtype list of dict: Each dict contains 'listen'and 'server_name'.
    """

    with open(config_file, 'r') as f:
        config_text = f.read()

    # Match each host block
    # host "<IP in here>" {<code block>}
    host_blocks = re.findall(r'host\s+"([^"]+)"\s*\{(.*?)\}', config_text, re.DOTALL)
    routes = {}
    # dist_policy_map = ""

    for host, block in host_blocks:
        # proxy_map = {}      # Dictionary {key: host, value: [proxy_pass]}

        # Find all proxy_pass entries
        proxy_passes = re.findall(r'proxy_pass\s+http://([^\s;]+);', block)
        # map = proxy_map.get(host,[])
        # map = map + proxy_passes
        # proxy_map[host] = map

        # Find dist_policy if any
        policy_match = re.search(r'dist_policy\s+([\w-]+)', block)
        # [\w-]: includes a-z, A-Z, 0-9, _ and -
        # +: one or more characters
        if policy_match:
            dist_policy_map = policy_match.group(1)
        else: #default policy is round_robin
            dist_policy_map = "round-robin"
            
        #
        # @bksysnet: Build the mapping and policy
        # TODO: this policy varies among scenarios 
        #       the default policy is provided with one proxy_pass
        #       In the multi alternatives of proxy_pass then
        #       the policy is applied to identify the highest matching
        #       proxy_pass
        #
        # if len(proxy_map.get(host,[])) == 1:    # In case of 1 proxy_pass
        #     routes[host] = (proxy_map.get(host,[])[0], dist_policy_map)
        # esle if:
        #         TODO:  apply further policy matching here
        #
        # else:
        #     routes[host] = (proxy_map.get(host,[]), dist_policy_map)
        if (len(proxy_passes) == 1):        # 1 proxy
            routes[host] = (proxy_passes[0], dist_policy_map)
        elif (len(proxy_passes) > 1):       # multiple proxies
            routes[host] = (proxy_passes, dist_policy_map)
        # print("Loaded virtual proxy routes:")
        # for host, (targets, policy) in routes.items():
        #     print("{} -> {}, policy: {}".format(host, targets, policy))
        print("{} {}".format(host, routes[host]))
    return routes

    # for key, value in routes.items():
    #     print(key, value)
    # return routes

### UTILITIES ###
# def build_balancer(routes: dict) -> dict:
#     """
#     Builds load balancer structures to track current backend index for each host.

#     :params routes (dict): dictionary mapping hostnames and location.
#     :rtype dict: mapping hostnames to their load balancer state.
#     """
#     balancer = {}
#     for host, (targets, policy) in routes.items():
#         if isinstance(targets, list) and policy == "round-robin":
#             balancer[host] = {
#                 'targets': targets,
#                 'index': 0,
#                 'policy': policy
#             }
#         else:
#             balancer[host] = {
#                 'targets': [targets],
#                 'index': 0,
#                 'policy': policy
#             }
#     return balancer

def get_next_backend(host, balancer):
    """
    Retrieves the next backend server for a given hostname based on the load balancing policy.

    :params host (str): The hostname for which to get the next backend.
    :params balancer (dict): The load balancer state for all hostnames.
    :rtype tuple: (backend_host, backend_port)
    """
    if host not in balancer:
        return None

    # entry = balancer[host]      # Get the balancer entry for the host
    # targets = entry['targets']
    # # curr_idx = entry['index'] # Don't need this, just update the actual index from entry, 
    #                             # or else you need curr_idx=entry['index'] after entry['index']+=1
    # policy = entry['policy']

    # if policy == "round-robin":
    #     backend = targets[entry['index']]
    #     entry['index'] = (entry['index'] + 1) % len(targets)  # Round-robin update
    # else:
    #     backend = targets[0]  # Default to first target if no policy matched
    # return backend
    targets, policy = balancer[host]    # tuple (target | [targets], policy)
    if isinstance(targets, list) and policy == "round-robin":
        index = getattr(get_next_backend, "index_map", {}).get(host, 0)
        backend = targets[index]
        newindex = (index + 1) % len(targets)  # Round-robin update
        if not hasattr(get_next_backend, "index_map"):
            get_next_backend.index_map = {}     # Custom attribute to store RR index per host
        get_next_backend.index_map[host] = newindex
        return backend
    else:
        return targets  # single target

if __name__ == "__main__":
    """
    Entry point for launching the proxy server.

    This block parses command-line arguments to determine the server's IP address
    and port. It then calls `create_backend(ip, port)` to start the RESTful
    application server.

    :arg --server-ip (str): IP address to bind the server (default: 127.0.0.1).
    :arg --server-port (int): Port number to bind the server (default: 9000).
    """

    parser = argparse.ArgumentParser(prog='Proxy', description='', epilog='Proxy daemon')
    parser.add_argument('--server-ip', default='0.0.0.0')
    parser.add_argument('--server-port', type=int, default=PROXY_PORT)
 
    args = parser.parse_args()
    ip = args.server_ip
    port = args.server_port

    #! 1. Parse config file
    routes = parse_virtual_hosts("config/proxy.conf")
    # #! 2. Build the balancer
    # balancer: dict = build_balancer(routes)
    #! 2. Pass to create_proxy
    create_proxy(ip, port, routes)
