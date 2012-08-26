import ws4py.websocket

import threading
import struct
import json

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

		self.album = None
		self.artist = None
		self.title = None
		self.playing = False

	def serve_forever(self):
		print "WebSockets server running on http://localhost:" + str(self.address[1])
		SocketServer.TCPServer.serve_forever(self)

	def serve_forever_thread(self):
		t = threading.Thread(target=self.serve_forever)
		t.setDaemon(True) # don't hang on exit
		t.start()

	def send_all_clients(self, message):
		for client in self.clients:
			if not client.finished:
				self.send_client(client, message)

	def send_client(self, client, message):
		client.send_message(message)

	def msg_playback_update(self):
		return json.dumps({
			"notification-type" : "playback-update",
			"playing" : self.playing,
			"artist" : self.artist,
			"album" : self.album,
			"title" : self.title
		})

	def update_playback_song(self, artist, album, title):
		self.artist = artist
		self.album = album
		self.title = title
		self.send_all_clients(self.msg_playback_update())

	def update_playback_playing(self, playing):
		self.playing = playing
		self.send_all_clients(self.msg_playback_update())

	def keep_updating_playback_status(self, client):
		self.send_client(client, self.msg_playback_update())
		# keep updating it every five seconds
		t = threading.Timer(5.0, self.keep_updating_playback_status, [client])
		t.start()

class WebSocketRequestHandler(SocketServer.StreamRequestHandler):
	magic = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
	messages = Queue.Queue()
	finished = False

	def setup(self):
		SocketServer.StreamRequestHandler.setup(self)
		self.handshake_done = False
		self.websocket = WebSocket(self.request)
		print "WebSockets connection from " + self.client_address[0]

	def finish(self):
		print "WebSockets closing " + self.client_address[0]
		self.finished = True
		SocketServer.StreamRequestHandler.finish(self)

	def handle(self):
		self.handshake()
		self.server.keep_updating_playback_status(self)
		while True:
			msg = self.messages.get(True)
			try:
				if self.ws_rfc:
					self.websocket.send(msg)
				else:
					self.request.sendall('\x00' + msg.encode('utf-8') + '\xff')
			except:
				return					

	def send_message(self, message):
		self.messages.put(message, True)

	def handshake(self):
		data = self.request.recv(1024)

		headers = Message(StringIO(data.split('\r\n', 1)[1]))
		body = data.split("\r\n\r\n")[1]

		upgrade = headers.get("Upgrade", "");
		if upgrade.lower() != "websocket":
			print "WebSockets client " + self.client_address[0] + " wrong Upgrade"
			return

		if headers.getheader('Sec-WebSocket-Key') != None:
			self.ws_rfc = True
			response = self.handshake_singleKey(headers)
		elif (headers.getheader('Sec-WebSocket-Key1') != None) and (headers.getheader('Sec-WebSocket-Key2') != None):
			self.ws_rfc = False
			response = self.handshake_twoKeys(headers, body)
		else:
			print "WebSockets client " + self.client_address[0] + " wrong structure"
			return

		self.handshake_done = self.request.sendall(response)
		self.server.clients += [self]
		print "WebSockets client " + self.client_address[0] + " handshaken"
		
	def handshake_singleKey(self, headers):
		key = headers.getheader('Sec-WebSocket-Key')
		digest = b64encode(sha1(key + self.magic).hexdigest().decode('hex'))
		response = 'HTTP/1.1 101 Switching Protocols\r\n'
		response += 'Upgrade: websocket\r\n'
		response += 'Connection: Upgrade\r\n'
		response += 'Sec-WebSocket-Accept: %s\r\n\r\n' % digest
		return response

	def handshake_getDigest(self, key1, key2, body):
		# Count spaces
		nums1 = key1.count(" ")
		nums2 = key2.count(" ")
		# Join digits in the key
		num1 = ''.join([x for x in key1 if x.isdigit()])
		num2 = ''.join([x for x in key2 if x.isdigit()])
		# Divide the digits by the num of spaces
		key1 = int(int(num1) / int(nums1))
		key2 = int(int(num2) / int(nums2))

		# Pack into Network byte ordered 32 bit ints
		import struct
		key1 = struct.pack("!I", key1)
		key2 = struct.pack("!I", key2)

		# Concat key1, key2, and the the body of the client handshake and take the md5 sum of it
		key = key1 + key2 + body
		import hashlib
		m = hashlib.md5()
		m.update(key)
		return m.digest()
	
	def handshake_twoKeys(self, headers, body):
		key1 = headers.getheader('Sec-WebSocket-Key1')
		key2 = headers.getheader('Sec-WebSocket-Key2')

		d = self.handshake_getDigest(key1, key2, body)

		response = "HTTP/1.1 101 WebSocket Protocol Handshake\r\n"
		response += "Upgrade: WebSocket\r\n"
		response += "Connection: Upgrade\r\n"
		response += "Sec-WebSocket-Origin: " + headers.getheader("Origin") + "\r\n"
		response += "Sec-WebSocket-Location: ws://" + headers.getheader("Host") + "/\r\n"
		response += "Sec-WebSocket-Protocol: " + headers.getheader("Sec-WebSocket-Protocol") + "\r\n"
		response += "\r\n"
		response += d

		return response

class WebSocket(ws4py.websocket.WebSocket):
	def received_message(self, message):
		print message.data
