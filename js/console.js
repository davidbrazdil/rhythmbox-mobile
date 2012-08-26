function console_clear() {
	$("#debug-console").html("");
}

function console_writeln(text) {
	$("#debug-console").append(text + "</br>");
}

function console_error(text) {
	$("#debug-console").append("<span class='debug-console-error'>" + text + "</span></br>");
}

$(function() {
	console_clear();
});

