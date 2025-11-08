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
daemon.httpadapter
~~~~~~~~~~~~~~~~~

This module provides a http adapter object to manage and persist 
http settings (headers, bodies). The adapter supports both
raw URL paths and RESTful route definitions, and integrates with
Request and Response objects to handle client-server communication.
"""

from .request import Request
from .response import Response
from .dictionary import CaseInsensitiveDict
def get_encoding_from_headers(headers):
        """
         Extracts encoding from Content-Type header.
        :param headers (dict): Response headers.
        :rtype str: Encoding (default 'utf-8').
        """
        content_type = headers.get('Content-Type', '')
        if 'charset=' in content_type:
            return content_type.split('charset=')[1].split(';')[0]
        return 'utf-8'
def extract_cookies(req, resp):
        """
        Build cookies from the :class:`Request <Request>` headers.

        :param req:(Request) The :class:`Request <Request>` object.
        :param resp: (Response) The res:class:`Response <Response>` object.
        :rtype: cookies - A dictionary of cookie key-value pairs.
        """
        cookies = CaseInsensitiveDict()
        if hasattr(req, 'headers') and req.headers:
            cookie_header = req.headers.get('Cookie', '')
            if cookie_header:
                for pair in cookie_header.split(';'):
                    pair = pair.strip()
                    if '=' in pair:
                        key, value = pair.split('=', 1)
                        cookies[key] = value

        
        return cookies

class HttpAdapter:
    """
    A mutable :class:`HTTP adapter <HTTP adapter>` for managing client connections
    and routing requests.

    The `HttpAdapter` class encapsulates the logic for receiving HTTP requests,
    dispatching them to appropriate route handlers, and constructing responses.
    It supports RESTful routing via hooks and integrates with :class:`Request <Request>` 
    and :class:`Response <Response>` objects for full request lifecycle management.

    Attributes:
        ip (str): IP address of the client.
        port (int): Port number of the client.
        conn (socket): Active socket connection.
        connaddr (tuple): Address of the connected client.
        routes (dict): Mapping of route paths to handler functions.
        request (Request): Request object for parsing incoming data.
        response (Response): Response object for building and sending replies.
    """

    __attrs__ = [
        "ip",
        "port",
        "conn",
        "connaddr",
        "routes",
        "request",
        "response",
    ]

    def __init__(self, ip, port, conn, connaddr, routes):
        """
        Initialize a new HttpAdapter instance.

        :param ip (str): IP address of the client.
        :param port (int): Port number of the client.
        :param conn (socket): Active socket connection.
        :param connaddr (tuple): Address of the connected client.
        :param routes (dict): Mapping of route paths to handler functions.
        """

        #: IP address.
        self.ip = ip
        #: Port.
        self.port = port
        #: Connection
        self.conn = conn
        #: Conndection address
        self.connaddr = connaddr
        #: Routes
        self.routes = routes
        #: Request
        self.request = Request()
        #: Response
        self.response = Response()

    def handle_client(self, conn, addr, routes):
        """
        Handle an incoming client connection.

        This method reads the request from the socket, prepares the request object,
        invokes the appropriate route handler if available, builds the response,
        and sends it back to the client.

        :param conn (socket): The client socket connection.
        :param addr (tuple): The client's address.
        :param routes (dict): The route mapping for dispatching requests.
        """

        # Connection handler.
        self.conn = conn        
        # Connection address.
        self.connaddr = addr
        # Request handler
        req = self.request
        # Response handler
        resp = self.response

        # Handle the request
        msg = conn.recv(1024).decode()
        req.prepare(msg, routes)

        #7/11 check routes
        #if not routes:
        #    print("[Error]: Routes map is empty.")

        # check cookie
        if req.path == '/index.html' and req.method == 'GET':
            print("CHECK COOKIE")
            if req.cookies and req.cookies.get('auth') == 'true':
                # Phục vụ index.html
                resp.status_code = 200
                resp.reason = "OK"
                resp.headers["Content-Type"] = "text/html"
                resp._content = b"<h1>Auth=true</h1>"
                req.path = '/index.html'  # Chuyển hướng nội bộ
                response = resp.build_response(req)
            else:
                # 401 Unauthorized
                resp.status_code = 401
                resp.reason = 'Unauthorized'
                resp.headers['Content-Type'] = 'text/html'
                resp._content = b'<h1>401 Unauthorized.</h1>'
                req.path ="/unauthorized.html"
                response = resp.build_response(req)
            conn.sendall(response)
            conn.close()
            return
        # Handle request hook
        if req.hook:
            print("[HttpAdapter] hook in route-path METHOD {} PATH {}".format(req.hook._route_path,req.hook._route_methods))
            return_value = req.hook(req.headers, req.body)
            
        body = req.body or ""
        form = {}
        for pair in body.split("&"):
            if "=" in pair:
                key, value = pair.split("=", 1)
                form[key] = value

        print(f"[HttpAdapter] Debug: Form data - username={form.get('username')}, password={form.get('password')}")  # Thêm debug
        # Handle /login POST
        
        if req.path == "/login.html" and req.method == "POST":
            print("[HttpAdapter] check login post")
            username = form.get("username", "")
            password = form.get("password", "")

            if username == "admin" and password == "password":
                resp.status_code = 200
                resp.reason = "OK"
                resp.headers["Content-Type"] = "text/html"
                resp.headers["Set-Cookie"] = "auth=true"
                resp._content = b"<h1>Login success</h1>"
                req.path = "/index.html"
            else:
                resp.status_code = 401
                resp.reason = "Unauthorized"
                resp.headers["Content-Type"] = "text/html"
                resp.headers["Set-Cookie"] = "auth=false"
                resp._content = b"<h1>401 Unauthorized</h1>"
                req.path ="/unauthorized.html"


            conn.sendall(resp.build_response(req))
            conn.close()
            return
            #
            # TODO: handle for App hook here
            #
        
        response = resp.build_response(req)

        #print(response)
        conn.sendall(response)
        conn.close()

    @property
    def extract_cookies(self):
        extract_cookies( self.request, self.response)

    def build_response(self, req, resp):
        """Builds a :class:`Response <Response>` object 

        :param req: The :class:`Request <Request>` used to generate the response.
        :param resp: The  response object.
        :rtype: Response
        """
        response = Response()

        # Set encoding.
        response.encoding = get_encoding_from_headers(response.headers)
        response.raw = resp
        response.reason = response.raw.reason

        if isinstance(req.url, bytes):
            response.url = req.url.decode("utf-8")
        else:
            response.url = req.url

        # Add new cookies from the server.
        response.cookies = extract_cookies(self)

        # Give the Response some context.
        response.request = req
        response.connection = self

        return response

    # def get_connection(self, url, proxies=None):
        # """Returns a url connection for the given URL. 

        # :param url: The URL to connect to.
        # :param proxies: (optional) A Requests-style dictionary of proxies used on this request.
        # :rtype: int
        # """

        # proxy = select_proxy(url, proxies)

        # if proxy:
            # proxy = prepend_scheme_if_needed(proxy, "http")
            # proxy_url = parse_url(proxy)
            # if not proxy_url.host:
                # raise InvalidProxyURL(
                    # "Please check proxy URL. It is malformed "
                    # "and could be missing the host."
                # )
            # proxy_manager = self.proxy_manager_for(proxy)
            # conn = proxy_manager.connection_from_url(url)
        # else:
            # # Only scheme should be lower case
            # parsed = urlparse(url)
            # url = parsed.geturl()
            # conn = self.poolmanager.connection_from_url(url)

        # return conn


    def add_headers(self, request):
        """
        Add headers to the request.

        This method is intended to be overridden by subclasses to inject
        custom headers. It does nothing by default.

        
        :param request: :class:`Request <Request>` to add headers to.
        """
        pass
    
    def build_proxy_headers(self, proxy):
        """Returns a dictionary of the headers to add to any request sent
        through a proxy. 

        :class:`HttpAdapter <HttpAdapter>`.

        :param proxy: The url of the proxy being used for this request.
        :rtype: dict
        """
        headers = {}
        #
        # TODO: build your authentication here
        #       username, password =...
        # we provide dummy auth here
        #
        import base64
        username, password = ("user1", "password")
        if username:
            auth_str = f"{username}:{password}"
            encoded = base64.b64encode(auth_str.encode()).decode()
            headers["Proxy-Authorization"] = f"Basic {encoded}"

    # Thêm headers khác nếu cần
        headers["Proxy-Connection"] = "Keep-Alive"

        return headers