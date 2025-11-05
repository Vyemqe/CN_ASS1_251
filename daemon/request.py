#
# Copyright (C) 2025 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course.
#
# WeApRous release
#
# The authors hereby grant to Licensee personal permission to use
# and modify the Licensed Source Code for the sole purpose of studying
# while attending the course
#

"""
daemon.request
~~~~~~~~~~~~~~~~~

This module provides a Request object to manage and persist 
request settings (cookies, auth, proxies).
"""
from .dictionary import CaseInsensitiveDict
import base64           # prepare_auth
import json as _json    # prepare_body
from urllib.parse import urlencode
import uuid             # prepare_body > files
import mimetypes        # prepare_body

class Request():
    """The fully mutable "class" `Request <Request>` object,
    containing the exact bytes that will be sent to the server.

    Instances are generated from a "class" `Request <Request>` object, and
    should not be instantiated manually; doing so may produce undesirable
    effects.

    Usage::

      >>> import deamon.request
      >>> req = request.Request()
      ## Incoming message obtain aka. incoming_msg
      >>> r = req.prepare(incoming_msg)
      >>> r
      <Request>
    """
    __attrs__ = [
        "method",
        "url",
        "headers",
        "body",
        "reason",
        "cookies",
        "body",
        "routes",
        "hook",
    ]

    def __init__(self):
        #: HTTP verb to send to the server.
        self.method = None
        #: HTTP URL to send the request to.
        self.url = None
        #: dictionary of HTTP headers.
        self.headers = None
        #: HTTP path
        self.path = None        
        # The cookies set used to create Cookie header
        self.cookies = None
        #: request body to send to the server.
        self.body = None
        #: Routes
        self.routes = {}
        #: Hook point for routed mapped-path
        self.hook = None

    def extract_request_line(self, request):    # -> HTTP Request
        try:
            lines = request.splitlines()
            first_line = lines[0]
            method, path, version = first_line.split()

            if path == '/':
                path = '/index.html'
        except Exception:
            return None, None

        return method, path, version
             
    def prepare_headers(self, request):
        """Prepares the given HTTP headers."""
        lines = request.split('\r\n')
        headers = {}
        for line in lines[1:]:
            if ': ' in line:
                key, val = line.split(': ', 1)
                headers[key.lower()] = val
        return headers

    def prepare(self, request, routes=None):
        """Prepares the entire request with the given parameters."""
        # Split headers and msg body
        header_part, _, body_part = request.partition('\r\n\r\n')

        # Prepare the request line from the request header
        self.method, self.path, self.version = self.extract_request_line(request)
        print("[Request] {} path {} version {}".format(self.method, self.path, self.version))

        self.url = self.path
        # @bksysnet Preapring the webapp hook with WeApRous instance
        # The default behaviour with HTTP server is empty routed
        #
        # TODO manage the webapp hook in this mounting point
        original_headers = self.prepare_headers(request)
        self.headers = CaseInsensitiveDict(original_headers)
        # Msg body if any
        self.body = body_part

        #  TODO: implement the cookie function here
        #        by parsing the header            #
        # * Sample Cookie header
        # * Set-Cookie: session_id=abc123xyz; Expires=Wed, 21 Oct 2025 07:28:00 GMT; Path=/; HttpOnly
        cookies_header = self.headers.get('cookie', '')
        cookies = {}
        if cookies_header is not None:
            cookie_parts = cookies_header.split(';')
            for part in cookie_parts:
                if '=' in part:
                    key, val = part.strip().split('=', 1)
                    cookies[key.strip()] = val.strip()      # Remove trailing spaces if any
        self.cookies = cookies

        #! Hook mounting
        if routes is not None:
            self.routes = routes
            self.hook = routes.get((self.method, self.path))
            #
            # self.hook manipulation goes here
            # ...
            #
            # Try some common wildcard to return hook from routes: dict
            # Wildcard seems dangerous to be used for hook (Ngoc)
            hook = routes.get(('*', self.path))
            if hook is None:
                hook = routes.get((self.method, '*'))
            if hook is None:
                hook = routes.get(('*', '*'))
            if callable(hook):
                self.hook = hook
        return self

    def prepare_body(self, data, files, json=None):
        """
        Prepare request body from data/files/json and set appropriate Content-Type
        and Content-Length headers.
        - json (any): if provided --> JSON-serialized and Content-Type set
                      to application/json.
        - files (dict): if provided --> produce multipart/form-data. Each item
                        in files can be either:
                          - a bytes/str (file content) -> filename will be the field name
                          - a tuple (filename, content[, content_type])
        - data (dict): form fields for either x-www-form-urlencoded or multipart.
        """
        if self.headers is None:
            self.headers = CaseInsensitiveDict()
        #! JSON body
        if json is not None:
            # Convert json to JSON formatted string if necessary
            body_str = _json.dumps(json) if not isinstance(json, str) else json
            self.headers["Content-Type"] = "application/json"
            self.body = body_str
            self.prepare_content_length(self.body)
            return self
        #! Files: Multipart form-data
        files = files or {}         # In case of None dict
        data = data or {}           # In case of None dict
        if files:
            bound = uuid.uuid4().hex
            self.headers["Content-Type"] = "multipart/form-data; boundary={}".format(bound)
            # Build multipart body
            lines = []
            # Add form fields (general outline)
            for name, value in data.items():    # Extract key-val in data dict
                part = []
                part.append("--" + bound)
                part.append('Content-Disposition: form-data; name="{}"'.format(name))
                part.append("")     # empty line before the content
                part.append(value if isinstance(value, str) else str(value))
                lines.append("\r\n".join(part).encode("utf-8"))
            # Add files from now
            for field, fileval in files.items():
                if isinstance(fileval, tuple) and (len(fileval) >= 2 and len(fileval) <= 3):
                    filename = fileval[0]
                    content = fileval[1]
                    if len(fileval) == 3:
                        content_type = fileval[2]
                    else:
                        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
                else:   # Raw content
                    filename = getattr(fileval, "name", field)
                    content = fileval
                    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
                # Read content in bytes
                if isinstance(content, str):
                    content_bytes = content.encode("utf-8")
                elif isinstance(content, bytes):
                    content_bytes = content
                else:
                    try:
                        content_bytes = content.read()
                        if isinstance(content_bytes, str):
                            content_bytes = content.encode("utf-8")
                    except Exception:
                        content_bytes = str(content).encode("utf-8")
                
                header_lines = []
                header_lines.append("--" + bound)
                header_lines.append('Content-Disposition: form-data; name="{}"; filename="{}"'.format(field, filename))
                header_lines.append("Content-Type: {}".format(content_type))
                header_lines.append("")     # empty line before the content
                lines.append("\r\n".join(header_lines).encode("utf-8") + b"\r\n" + content_bytes)
            # Ending boundary
            lines.append(("--" + bound + "--").encode("utf-8"))
            # Join all parts with carriage return and newline feed
            body_bytes = b"\r\n".join(lines) + b"\r\n"
            self.body = body_bytes
        #! No files --> form-urlencoded
        elif data:
            encoded = urlencode(data)
            self.headers["Content-Type"] = "application/x-www-form-urlencoded"
            self.body = encoded
        #! No files and no data
        else:
            self.body = None
        self.prepare_content_length(self.body)
        return self

    def prepare_content_length(self, body):
        if self.headers is None:
            self.headers = CaseInsensitiveDict()
        if body is None:
            self.headers["Content-Length"] = "0"
            return self
        #
        # TODO prepare the request authentication
        #
	# self.auth = ...
        if isinstance(body, str):
            length = len(body.encode()) # str -> bytes
        else:
            # Try to convert to str and get length
            try:
                length = len(body)
            except Exception:
                length = len(str(body).encode())
        self.headers["Content-Length"] = str(length)
        return self

    def prepare_auth(self, auth, url=""):
        #
        # TODO prepare the request authentication
        #? Should store in self.headers["Authorization"]
	# self.auth = ...
        if self.headers is None:
            self.headers = CaseInsensitiveDict()
        if not auth:
            return self
        self.auth = auth
        #! Basic Authorization header
        #! Authorization: Basic <base64_credentials>
        # credentials = <username>:<password>
        if isinstance(auth, (tuple, list)) and len(auth) == 2:
            usr, pwd = auth
            # credentials = "{}:{}".format(usr, pwd)
            # # Encoding process
            # bytes_cred = credentials.encode()
            # b64_bytes_cred = base64.b64encode(bytes_cred)
            # b64_cred = b64_bytes_cred.decode()   # bytes -> str
            b64_str_cred = self.encoding_cred(usr, pwd)
            # Setting headers that follows the sample header
            self.headers["Authorization"] = "Basic {}".format(b64_str_cred)
            return self
        #! String authorization
        elif isinstance(auth, str):
            auth_str = auth.strip()
            if auth_str.lower().startswith("bearer "):
                self.headers["Authorization"] = auth_str
                return self
            if ":" in auth_str:
                usr, pwd = auth_str.split(":", 1)
                b64_str_cred = self.encoding_cred(usr, pwd)
                self.headers["Authorization"] = "Basic {}".format(b64_str_cred)
                return self
            # Otherwise, bearer authorization
            self.headers["Authorization"] = "Basic {}".format(auth_str)
            return self
        # Default: set str(auth)
        try:
            self.headers["Authorization"] = str(auth)
        except Exception:
            pass
        return self
    
    def prepare_cookies(self, cookies):
        self.headers["Cookie"] = cookies

    ### UTILITIES ###
    def encoding_cred(self, usr, pwd) -> str:
        credentials = "{}:{}".format(usr, pwd)
        bytes_cred = credentials.encode()
        b64_bytes_cred = base64.b64encode(bytes_cred)
        b64_str_cred = b64_bytes_cred.decode()   # bytes -> str
        return b64_str_cred