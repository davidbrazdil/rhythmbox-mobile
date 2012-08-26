function websocket_connect() {
	if (window.ws) {
		ws_console("closing connection");
		window.ws.onmessage = null;
		window.ws.close();
	}

	address = "ws://" + location.hostname + ":32910/";
	ws_console("connecting to " + address);

	window.ws = new ReconnectingWebSocket(address);
	window.ws.onopen = function(e) { ws_console("connected"); };
	window.ws.onmessage = websocket_onMessage;
	window.ws.onclose = function(e) { ws_console("connection closed"); };
	window.ws.onerror = function(e) { ws_console_error(e.data); };
}

function websocket_onMessage(e) {
	var json_data = JSON.parse(e.data);

	// ws_console(json_data["notification-type"] + " message");

	switch(json_data["notification-type"]) {
		case "playback-update":
			playback_update(json_data["artist"], json_data["album"], json_data["title"], json_data["playing"]);
			break;
		default:
			console.error("WebSocket unknown message");
	}
}

function ws_console(text) {
	console_writeln("WebSocket: " + text);
}

function ws_console_error(text) {
	console_error("WebSocket: " + text);
}

