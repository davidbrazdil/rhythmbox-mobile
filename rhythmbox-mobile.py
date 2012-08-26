import http
import ws

from gi.repository import GObject, Peas
from gi.repository import RB

import gettext
gettext.install('rhythmbox', RB.locale_dir())

PORT_HTTP = 8888
PORT_WS = 32910

class RhythmboxMobile(GObject.Object, Peas.Activatable):
	__gtype_name = 'RhythmboxMobile'
	object = GObject.property(type=GObject.GObject)

	def __init__(self):
		GObject.Object.__init__(self)
			
	def do_activate(self):
		print "activating rhythmbox-mobile plugin"

		shell = self.object
		db = shell.props.db
		model = RB.RhythmDBQueryModel.new_empty(db)
		self.source = GObject.new (PythonSource, shell=shell, name=_("Python Source"), query_model=model)
		self.source.setup()
		group = RB.DisplayPageGroup.get_by_id ("library")
		shell.append_display_page(self.source, group)
		
		# Launch the WebSockets server
		self.ws = ws.WebSocketServer(("", PORT_WS))
		self.ws.serve_forever_thread()

		# Launch the HTTP server
		self.http = http.HTTPServer(("", PORT_HTTP), self)
		self.http.serve_forever_thread()

		# Connect to player notifications
		shell.props.shell_player.connect("playing-song-changed", self.handler_song_changed)

	def do_deactivate(self):
		print "deactivating rhythmbox-mobile plugin"

		self.source.delete_thyself()
		self.source = None

		self.http.shutdown()
		self.http.socket.close()
		self.http = None

	def handler_song_changed(self, player, entry):
		self.ws.send_all_clients("Song changed")

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
