"use strict";

// https://plainjs.com/javascript/ajax/send-ajax-get-and-post-requests-47/
function postAjax(url, data, success, fail) {
	var params = typeof data == 'string' ? data : Object.keys(data).map(
		function(k){ return encodeURIComponent(k) + '=' + encodeURIComponent(data[k]) }
	).join('&');

	var xhr = window.XMLHttpRequest ? new XMLHttpRequest() : new ActiveXObject("Microsoft.XMLHTTP");
	xhr.open('POST', url);
	xhr.onreadystatechange = function() {
		if (xhr.readyState>3 && xhr.status==200) { success(xhr.responseText); }
		else if (xhr.readyState>3 && xhr.status==400) { fail(xhr.responseText); }
	};
	xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
	xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
	xhr.send(params);
	return xhr;
}
function getAjax(url, success) {
	var xhr = window.XMLHttpRequest ? new XMLHttpRequest() : new ActiveXObject('Microsoft.XMLHTTP');
	xhr.open('GET', url);
	xhr.onreadystatechange = function() {
		if (xhr.readyState>3 && xhr.status==200) success(xhr.responseText);
	};
	xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
	xhr.send();
	return xhr;
}

function setSynced() {
	let indicator = document.getElementById("pad-status-indicator");
	if (indicator.classList.contains('no')) {
		// do not overwrite the 'Diverged' state
		return;
	}
	indicator.classList.remove('warn');
	indicator.classList.add('yes');
	let text = document.getElementById("pad-status-text");
	text.textContent = 'Synced';
}
function setChanged() {
	let indicator = document.getElementById("pad-status-indicator");
	if (indicator.classList.contains('no')) {
		// do not overwrite the 'Diverged' state
		return;
	}
	indicator.classList.remove('yes');
	indicator.classList.add('warn');
	let text = document.getElementById("pad-status-text");
	text.textContent = 'Changed';
}
function setDiverged() {
	let indicator = document.getElementById("pad-status-indicator");
	indicator.classList.remove('yes');
	indicator.classList.remove('warn');
	indicator.classList.add('no');
	let text = document.getElementById("pad-status-text");
	text.textContent = 'Diverged! Please reload.';
}

function applyResponse(response) {
	presence = JSON.parse(response);
	let obrounds = document.querySelectorAll('#presence .obround');
	for (let i = 0; i < presence.length; i++) {
		let name = presence[i][0];
		let present = presence[i][1];
		obrounds[i].getElementsByClassName("presence-name")[0].innerHTML = name;
		let circle = obrounds[i].getElementsByClassName("presence-indicator")[0];
		circle.classList.remove("spinner");
		if (present) {
			if (i == presence.length - 1) {
				obrounds[i].style.display = "";
			}
			circle.classList.remove("no");
			circle.classList.add("yes");
		} else {
			if (i == presence.length - 1) {
				obrounds[i].style.display = "none";
			}
			circle.classList.remove("yes");
			circle.classList.add("no");
		}
	}
}

function getPresence(url) {
	let obrounds = document.querySelectorAll('#presence .obround');
	for (let i = 0; i < obrounds.length; i++) {
		let circle = obrounds[i].getElementsByClassName("presence-indicator")[0];
		circle.classList.remove("yes");
		circle.classList.remove("no");
		circle.classList.add("spinner");
	}

	getAjax(url, applyResponse);
}

document.addEventListener("DOMContentLoaded", function() {
	let pad = document.getElementById("pad");
	pad.addEventListener('input', function() {
		setChanged();
	});

	let submitPad = document.getElementById("submit-pad");
	//TODO: tap
	submitPad.addEventListener('click', function() {
		PAD_VERSION ++;
		postAjax('/submit_pad', {
			version: PAD_VERSION - 1,
			content: pad.value
		}, function(){
			setSynced();
		}, function() {
			PAD_VERSION --;
			setDiverged();
		});
	});

	let updatePresenceButton = document.getElementById("update-presence");
	updatePresenceButton.addEventListener('click', function() {
		getPresence('/update_presence')
	});
	getPresence('/get_presence')
});

window.addEventListener('beforeunload', function (e) {
	let indicator = document.getElementById("pad-status-indicator");
	if (indicator.classList.contains('yes')) {
		// don't prompt the user if the content is synced
		return;
	}
	// show a prompt
	e.preventDefault();
	e.returnValue = '';
});
