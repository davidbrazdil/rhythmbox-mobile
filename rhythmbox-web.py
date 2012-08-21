import BaseHTTPServer
import threading

from gi.repository import GObject, Peas
from gi.repository import RB

import gettext
gettext.install('rhythmbox', RB.locale_dir())

PORT = 4444

class RhythmboxWeb(GObject.Object, Peas.Activatable):
	__gtype_name = 'RhythmboxWebPlugin'
	object = GObject.property(type=GObject.GObject)

	def __init__(self):
		GObject.Object.__init__(self)
			
	def do_activate(self):
		print "activating rhythmbox-web plugin"

		shell = self.object
		db = shell.props.db
		model = RB.RhythmDBQueryModel.new_empty(db)
		self.source = GObject.new (PythonSource, shell=shell, name=_("Python Source"), query_model=model)
		self.source.setup()
		group = RB.DisplayPageGroup.get_by_id ("library")
		shell.append_display_page(self.source, group)
		
		self.httpd = HTTPServer(("", PORT), HTTPRequestHandler)

		t = threading.Thread(target=self.httpd.serve_forever)
		t.setDaemon(True) # don't hang on exit
		t.start()

	def do_deactivate(self):
		print "deactivating rhythmbox-web plugin"

		self.source.delete_thyself()
		self.source = None

		self.httpd.shutdown()
		self.httpd.socket.close()
		self.httpd = None

class HTTPServer(BaseHTTPServer.HTTPServer): 
	allow_reuse_address = True 

class HTTPRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
	def do_GET(self):
		path, query = self.get_path_and_query()
		print "GET " + path
		return None

	def get_path_and_query(self):
	        path = self.path

		i = path.rfind('?')
		if i >= 0:
			path, query = path[:i], path[i+1:]
		else:
			query = ''
		return path, query

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
