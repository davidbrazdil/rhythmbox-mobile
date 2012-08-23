import BaseHTTPServer
import threading
import posixpath
import urllib
import os
import mimetypes
import cgi
import shutil
from StringIO import StringIO

from gi.repository import GObject, Peas
from gi.repository import RB

import gettext
gettext.install('rhythmbox', RB.locale_dir())

PORT = 4444

class RhythmboxMobile(GObject.Object, Peas.Activatable):
	__gtype_name = 'RhythmboxMobile'
	object = GObject.property(type=GObject.GObject)

	def __init__(self):
		GObject.Object.__init__(self)
			
	def do_activate(self):
		print "activating rhythmbox-mobile plugin"

		# print dir(self)
		# RB.find_plugin_data_file(self, "index.htm")

		shell = self.object
		db = shell.props.db
		model = RB.RhythmDBQueryModel.new_empty(db)
		self.source = GObject.new (PythonSource, shell=shell, name=_("Python Source"), query_model=model)
		self.source.setup()
		group = RB.DisplayPageGroup.get_by_id ("library")
		shell.append_display_page(self.source, group)
		
		self.httpd = HTTPServer(("", PORT), self)

		t = threading.Thread(target=self.httpd.serve_forever)
		t.setDaemon(True) # don't hang on exit
		t.start()

	def do_deactivate(self):
		print "deactivating rhythmbox-mobile plugin"

		self.source.delete_thyself()
		self.source = None

		self.httpd.shutdown()
		self.httpd.socket.close()
		self.httpd = None

class HTTPServer(BaseHTTPServer.HTTPServer): 
	allow_reuse_address = True 

	def __init__(self, address, plugin):
		BaseHTTPServer.HTTPServer.__init__(self, address, HTTPRequestHandler)
		self.plugin = plugin

class HTTPRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):

	extensions_map = mimetypes.types_map.copy()
	extensions_map.update({
		'': 'application/octet-stream', # Default
		'.py': 'text/plain',
		'.c': 'text/plain',
		'.h': 'text/plain',
	})

	def do_GET(self):
		"""Serve a GET request."""
		player = self.get_player()
		if (self.path == '/cmd?play-pause'):
			player.playpause(True)
			self.send_200()
		elif (self.path == '/cmd?prev'):
			player.do_previous()
			self.send_200()
		elif (self.path == '/cmd?next'):
			player.do_next()
			self.send_200()
		else:
			f = self.send_head()
			if f:
				self.copyfile(f, self.wfile)
				f.close()

	def do_HEAD(self):
		"""Serve a HEAD request."""
		f = self.send_head()
		if f:
			f.close()

	def send_200(self):
		self.send_response(200)
		self.end_headers()
		return None
	
	def send_404(self):
		self.send_error(404, "File not found")
		return None

	def send_head(self):
		"""Common code for GET and HEAD commands.
		
		This sends the response code and MIME headers.
		
		Return value is either a file object (which has to be copied
		to the outputfile by the caller unless the command was HEAD,
		and must be closed by the caller under all circumstances), or
		None, in which case the caller has nothing further to do.
		
		"""

		path = self.translate_path(self.path)
		f = None
		if os.path.isdir(path):
			for index in "index.html", "index.htm":
				index = os.path.join(path, index)
				if os.path.exists(index):
					path = index
					break
			else:
				return self.send_404()
		ctype = self.guess_type(path)
		if ctype.startswith('text/'):
			mode = 'r'
		else:
			mode = 'rb'
		try:
			f = open(path, mode)
		except IOError:
			return self.send_404()
		self.send_response(200)
		self.send_header("Content-type", ctype)
		self.end_headers()
		return f

	def translate_path(self, path):
		"""Translate a /-separated PATH to the local filename syntax.
		
		Components that mean special things to the local file system
		(e.g. drive or directory names) are ignored.  (XXX They should
		probably be diagnosed.)
		
		"""

		path = posixpath.normpath(urllib.unquote(path))
		words = path.split('/')
		words = filter(None, words)
		path = os.path.dirname(__file__)
		for word in words:
			drive, word = os.path.splitdrive(word)
			head, word = os.path.split(word)
			if word in (os.curdir, os.pardir): continue
			path = os.path.join(path, word)
		return path

	def copyfile(self, source, outputfile):
		"""Copy all data between two file objects.
		
		The SOURCE argument is a file object open for reading
		(or anything with a read() method) and the DESTINATION
		argument is a file object open for writing (or
		anything with a write() method).

		The only reason for overriding this would be to change
		the block size or perhaps to replace newlines by CRLF
		-- note however that this the default server uses this
		to copy binary data as well.
		
		"""
		shutil.copyfileobj(source, outputfile)

	def guess_type(self, path):
		"""Guess the type of a file.
		
		Argument is a PATH (a filename).
		
		Return value is a string of the form type/subtype,
		usable for a MIME Content-type header.
		
		The default implementation looks the file's extension
		up in the table self.extensions_map, using text/plain
		as a default; however it would be permissible (if
		slow) to look inside the data to make a better guess.
		
		"""

		base, ext = posixpath.splitext(path)
		if self.extensions_map.has_key(ext):
			return self.extensions_map[ext]
		ext = ext.lower()
		if self.extensions_map.has_key(ext):
			return self.extensions_map[ext]
		else:
			return self.extensions_map['']

	def get_path_and_query(self):
	        path = self.path

		i = path.rfind('?')
		if i >= 0:
			path, query = path[:i], path[i+1:]
		else:
			query = ''
		return path, query

	def get_player(self):
		return self.server.plugin.object.props.shell_player

class PythonSource(RB.Source):
	def __init__(self, **kwargs):
		super(PythonSource, self).__init__(kwargs)

	def setup(self):
		shell = self.props.shell
		songs = RB.EntryView(db=shell.props.db, shell_player=shell.props.shell_player, is_drag_source=False, is_drag_dest=False)
		songs.append_column(RB.EntryViewColumn.TITLE, True)
		songs.set_model(self.props.query_model)
		songs.show_all()
		self.pack_start(songs, expand=True, fill=True, padding=0)



GObject.type_register(PythonSource)
