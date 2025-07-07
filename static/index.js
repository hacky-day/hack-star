const VALUE_MAP = {
	'issue': 1,
	'trivial-pull-request': 1,
	'pull-request': 3,
	'review': 1
}

function view(target) {
	for (const element of ['board', 'edit']) { 
		document.getElementById(element).style.display = target === element ? 'block' : 'none';
	}
}

function updateBoard() {
	fetch('/leaderboard')
	.then(response => response.json())
	.then(data => {
		const table = document.createElement('table');
		for (const [username, points] of Object.entries(data)) {
			const tr = document.createElement('tr');
			const td_user = document.createElement('td');
			td_user.innerText = username;
			const td_points = document.createElement('td');
			td_points.innerText = points;
			tr.appendChild(td_user);
			tr.appendChild(td_points);
			table.appendChild(tr);
		}
		const board = document.getElementById('board');
		const old_table = document.querySelector('#board > table');
		board.replaceChild(table, old_table);
	})
}

function add() {
	const username = document.getElementById('username');
	const type = document.getElementById('type');
	const link = document.getElementById('link');

	console.info(username.value, type.value, link.value);
	if (!link.value.startsWith('https://github.com/opencast/opencast-admin-interface/')) {
		alert('Invalid admin interface repository link!');
		return;
	}
	if (username.value && type.value && link.value) {
		const data = {
			'username': username.value,
			'link': link.value,
			'type': type.value,
			'points': VALUE_MAP[type.value]
		}
		console.debug(data);
		link.value = '';
		fetch('/add', {
			method: "POST",
			headers: { "Content-Type": "application/json", },
			body: JSON.stringify(data)
		})
		.then(updateData);
	}
}

function updateData() {
	fetch('/data')
	.then(response => response.json())
	.then(data => {
		const table = document.createElement('table');
		for (const row of data) {
			row[0] = new Date(row[0] * 1000).toISOString();
			row[2] = row[2].replace(/^https:\/\/github.com\/opencast\/opencast-admin-interface\//, '')
			const tr = document.createElement('tr');
			for (const cell of row) {
				const td = document.createElement('td');
				td.innerText = cell;
				tr.appendChild(td);
			}
			table.appendChild(tr);
		}
		const edit = document.getElementById('edit');
		const old_table = document.querySelector('#edit > table');
		edit.replaceChild(table, old_table);
	})
}

window.addEventListener('DOMContentLoaded',function () {
	updateBoard();
	window.setInterval(updateBoard, 5000);
	updateData();
	window.setInterval(updateData, 30000);
})
