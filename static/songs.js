// Audio player functionality
let currentAudio = null;
let currentPlayingSong = null;

function toggleDropdown(songId) {
  const dropdown = document.getElementById('dropdown-' + songId);
  const isVisible = dropdown.style.display === 'block';

  // Close all dropdowns first
  document.querySelectorAll('.dropdown-content').forEach(d => d.style.display = 'none');

  // Toggle current dropdown
  dropdown.style.display = isVisible ? 'none' : 'block';
}

// Close dropdowns when clicking outside
document.addEventListener('click', function (event) {
  if (!event.target.matches('.dropdown-btn')) {
    document.querySelectorAll('.dropdown-content').forEach(d => d.style.display = 'none');
  }
});

function playPauseSong(songId) {
  const audioUrl = '/song/' + songId;

  // If this song is already playing, pause it
  if (currentPlayingSong === songId && currentAudio && !currentAudio.paused) {
    currentAudio.pause();
    updatePlayButton(songId, false);
    return;
  }

  // Stop any currently playing song
  if (currentAudio) {
    currentAudio.pause();
    if (currentPlayingSong) {
      updatePlayButton(currentPlayingSong, false);
    }
  }

  // Create new audio element
  currentAudio = new Audio(audioUrl);
  currentPlayingSong = songId;

  currentAudio.addEventListener('loadstart', () => {
    updatePlayButton(songId, true);
  });

  currentAudio.addEventListener('ended', () => {
    updatePlayButton(songId, false);
    currentPlayingSong = null;
  });

  currentAudio.addEventListener('error', () => {
    alert('Error playing song');
    updatePlayButton(songId, false);
    currentPlayingSong = null;
  });

  currentAudio.play().catch(error => {
    console.error('Error playing audio:', error);
    alert('Error playing song');
    updatePlayButton(songId, false);
    currentPlayingSong = null;
  });
}

function updatePlayButton(songId, isPlaying) {
  const playOverlay = document.querySelector('#song-' + songId + ' .play-overlay');
  const playIcon = document.querySelector('#song-' + songId + ' .play-icon');

  if (playIcon) {
    playIcon.textContent = isPlaying ? '⏸' : '▶';
  }
}

function deleteSong(songId) {
  if (confirm('Are you sure you want to delete this song? This action cannot be undone.')) {
    fetch('/songs/' + songId + '/delete', {
      method: 'DELETE'
    }).then(response => {
      if (!response.ok) {
        alert('Error deleting song');
        return;
      }
      // Remove the song element from the DOM
      document.getElementById('song-' + songId).remove();

      // Stop audio if this song was playing
      if (currentPlayingSong === songId && currentAudio) {
        currentAudio.pause();
        currentPlayingSong = null;
      }

      // Update the songs count and show "no songs" message if all songs are deleted
      const remainingSongs = document.querySelectorAll('.song-item').length;
      if (remainingSongs === 0) {
        const songsContainer = document.getElementById('songs-container');
        if (songsContainer) {
          songsContainer.innerHTML = '<h2>Songs</h2><div class="no-songs"><p>No songs found in the database.</p><p><a href="/static/upload.html">Upload some songs →</a></p></div>';
        }
      }
    }).catch(error => {
      alert('Error deleting song: ' + error);
    });
  }
}
