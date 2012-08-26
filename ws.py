import ws4py.websocket

import threading
import struct
from base64 import b64encode
from hashlib import sha1
from mimetools import Message
from StringIO import StringIO

import SocketServer
import Queue

class WebSocketServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer): 
	allow_reuse_address = True 

	def __init__(self, address):
		SocketServer.TCPServer.__init__(self, address, WebSocketRequestHandler)
		self.address = address
		self.clients = []

	def serve_forever(self):
		print "WebSockets server running on http://localhost:" + str(self.address[1])
		SocketServer.TCPServer.serve_forever(self)

	def serve_forever_thread(self):
		t = threading.Thread(target=self.serve_forever)
		t.setDaemon(True) # don't hang on exit
		t.start()

	def send_all_clients(self, message):
		clients_alive = []
		for x in self.clients:
			try:
				x.send_message(message)
			except socket.error:
				print "ws://" + x.client_address[0] + " is dead"
			else:
				clients_alive += [x]
		self.clients = clients_alive

class WebSocketRequestHandler(SocketServer.StreamRequestHandler):
	magic = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
	messages = Queue.Queue()

	def setup(self):
		SocketServer.StreamRequestHandler.setup(self)
		self.handshake_done = False
		self.websocket = WebSocket(self.request)
		print "WebSockets connection from " + self.client_address[0]

	def handle(self):
		self.handshake()
		while True:
			msg = self.messages.get(True)
			data = msg.encode('utf-8')
			print "ws://" + self.client_address[0] + " - " + msg
			self.websocket.send(data)

	def send_message(self, message):
		self.messages.put(message, True)

	def handshake(self):
		data = self.request.recv(1024).strip()
		headers = Message(StringIO(data.split('\r\n', 1)[1]))
		if headers.get("Upgrade", None) != "websocket":
			return
		key = headers['Sec-WebSocket-Key']
		digest = b64encode(sha1(key + self.magic).hexdigest().decode('hex'))
		response = 'HTTP/1.1 101 Switching Protocols\r\n'
		response += 'Upgrade: websocket\r\n'
		response += 'Connection: Upgrade\r\n'
		response += 'Sec-WebSocket-Accept: %s\r\n\r\n' % digest
		self.handshake_done = self.request.send(response)
		self.server.clients += [self]
		print "WebSockets client " + self.client_address[0] + " handshaken"

class WebSocket(ws4py.websocket.WebSocket):
	def received_message(self, message):
		print message.data
