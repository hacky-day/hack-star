function play() {
  document.querySelector('audio').play();
  document.getElementById('play').style.display = 'none';
  document.getElementById('playbtn').style.display = 'none';
  document.getElementById('questionmark').style.display = 'inline-flex';
  document.getElementById('reveal').style.display = 'block';
}
function reveal() {
  document.getElementById('questionmark').style.display = 'none';
  document.getElementById('reveal').style.display = 'none';
  document.getElementById('coverart').style.display = 'inline-flex';
  document.getElementById('metadata').style.display = 'block';
}
function next() {
  window.location.reload();
}
