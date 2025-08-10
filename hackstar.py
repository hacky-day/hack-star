import asyncio
import logging
import multiprocessing
import os
import random
import sqlite3
import subprocess
import time

from flask import Flask, g, request, redirect, send_from_directory, render_template
from shazamio import Shazam
from yt_dlp import YoutubeDL

DATABASE = os.environ.get("HACKSTAR_DATABASE", "db/hackstar.db")
DATA_DIR = os.environ.get("HACKSTAR_DATA_DIR", "data")

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
logging.getLogger("symphonia_bundle_mp3.demuxer").setLevel(logging.ERROR)

__SQL_CREATE = [
    """
    CREATE TABLE IF NOT EXISTS version(
        version unsigned int primary key
    )""",
    """
    CREATE TABLE IF NOT EXISTS song(
        id unsigned int primary key,
        title varchar(255),
        artist varchar(255),
        release_date unsigned int,
        cover varchar(255)
    )""",
    """
    CREATE TABLE IF NOT EXISTS game(
        id unsigned int not null,
        song_id unsigned int,
        PRIMARY KEY (id, song_id),
        FOREIGN KEY (song_id) REFERENCES song(id) ON DELETE CASCADE
    )""",
    """
    CREATE TABLE IF NOT EXISTS job_url(
        song_id unsigned int,
        url varchar(255) NOT NULL,
        output text NOT NULL,
        state varchar(16) NOT NULL,
        FOREIGN KEY (song_id) REFERENCES song(id) ON DELETE CASCADE
    )""",
    """
    CREATE TABLE IF NOT EXISTS job_file(
        song_id unsigned int,
        filename varchar(255) NOT NULL,
        state varchar(16) NOT NULL,
        FOREIGN KEY (song_id) REFERENCES song(id) ON DELETE CASCADE
    )""",
]


def db_init():
    con = sqlite3.connect(DATABASE)
    cur = con.cursor()
    for create_table in __SQL_CREATE:
        cur.execute(create_table)
    # Insert database version
    data = list(cur.execute("select version from version"))
    if not data:
        cur.execute("insert into version values(?)", (0,))
        con.commit()
    con.close()


async def shazam(audio_file):
    shazam = Shazam()
    out = await shazam.recognize(audio_file)
    track = out["track"]

    title = track["title"]
    logger.info("Track title: %s", title)

    release_date = track.get("releasedate")
    if release_date:
        release_date = int(release_date[-4:])
    else:
        metadata = track.get("sections", [{}])[0].get("metadata")
        for data in metadata:
            if data["title"] == "Released":
                release_date = int(data["text"])
    logger.info("Release date: %s", release_date)

    cover = track.get("images", {}).get("coverart")
    logger.info("Cover art: %s", cover)

    artist_id = int(track["artists"][0]["adamid"])
    about_artist = await shazam.artist_about(artist_id)
    artist = about_artist["data"][0]["attributes"]["name"]
    logger.info("Artist: %s", artist)

    return title, artist, release_date, cover


def youtube_playlist_links(url):
    ydl_opts = {
        "extract_flat": "in_playlist",  # Extract video URLs only
        "quiet": True,  # Suppress output
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return [entry["url"] for entry in info.get("entries", [])]


def gen_hex_id(id: int) -> str:
    return hex(id)[2:]


def file_worker():
    con = sqlite3.connect(DATABASE)
    cur = con.cursor()
    while True:
        data = list(
            cur.execute(
                "select song_id, filename from job_file where state = 'waiting' limit 1"
            )
        )
        # no entry to process sleep for 5 seconds
        if not data:
            time.sleep(5)
            continue
        logger.debug("Processing file job: %s", data)
        song_id, filename = data[0]
        # Mark job_file as running
        cur.execute(
            "update job_file set state = 'running' where song_id = ?",
            (song_id,),
        )
        con.commit()

        # Convert file
        hex_id = gen_hex_id(song_id)
        command = [
            "ffmpeg",
            "-i",
            filename,
            "-movflags",
            "faststart",
            "-c:a",
            "aac",
            "-vn",
            f"{hex_id}.m4a",
        ]
        result = subprocess.run(
            command,
            text=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=DATA_DIR,
        )
        logger.debug("FFmpeg output: %s", result.stdout)

        # Get data from Shazam
        audio_file = f"{DATA_DIR}/{hex_id}.m4a"
        title, artist, release_date, cover = asyncio.run(shazam(audio_file))
        logger.info("Shazam result: %s by %s (%s)", title, artist, release_date)

        # Insert data in song create_table
        cur.execute(
            "update song set title = ?, artist = ?, release_date = ?, cover = ? where id = ?",
            (title, artist, release_date, cover, song_id),
        )
        con.commit()

        # mark job_url as finished
        cur.execute(
            "update job_file set state = 'finished' where song_id = ?",
            (song_id,),
        )
        con.commit()

        # remove temporary file
        os.remove(f"{DATA_DIR}/{filename}")


def download_worker():
    con = sqlite3.connect(DATABASE)
    cur = con.cursor()
    while True:
        data = list(
            cur.execute(
                "select song_id, url from job_url where state = 'waiting' limit 1"
            )
        )
        if not data:
            time.sleep(5)
            continue

        logger.info("Processing download job: %s", data)
        song_id, url = data[0]

        # Process job if one is waiting
        try:
            # Mark job_url as running
            cur.execute(
                "update job_url set state = 'downloading' where song_id = ?", (song_id,)
            )
            con.commit()

            # Download from YouTube
            hex_id = gen_hex_id(song_id)
            ydl_opts = {
                "format": "bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "aac",
                        "preferredquality": "128",
                    }
                ],
                "postprocessor_args": ["-movflags", "faststart"],
                "outtmpl": os.path.join(DATA_DIR, f"{hex_id}.%(ext)s"),
                "noplaylist": True,
                "quiet": True,
            }

            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            output = f"Downloaded {url} to {hex_id}.m4a"
            logger.debug("yt-dlp output: %s", output)
            cur.execute(
                "update job_url set state = 'running', output = ? where song_id = ?",
                (output, song_id),
            )
            con.commit()

            # Get data from Shazam
            audio_file = f"{DATA_DIR}/{hex_id}.m4a"
            title, artist, release_date, cover = asyncio.run(shazam(audio_file))
            logger.info("Shazam result: %s by %s (%s)", title, artist, release_date)

            # Insert data in song create_table
            cur.execute(
                "update song set title = ?, artist = ?, release_date = ?, cover = ? where id = ?",
                (title, artist, release_date, cover, song_id),
            )
            con.commit()

            # mark job_url as finished
            cur.execute(
                "update job_url set state = 'finished', output = ? where song_id = ?",
                (output, song_id),
            )
            con.commit()

        except Exception as e:
            print(f"Failed to process job {data}", e)
            cur.execute(
                "update job_url set state = 'failed', output = ? where song_id = ?",
                (str(e), song_id),
            )
            con.commit()

        time.sleep(0.1)


def app_init():
    db_init()
    logger.info("Starting worker processes")
    multiprocessing.Process(target=download_worker).start()
    multiprocessing.Process(target=file_worker).start()
    logger.info("Starting web application")
    return Flask(__name__)


app = app_init()


def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db


@app.teardown_appcontext
def close_connection(_):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/stats")
def stats():
    db = get_db()
    cursor = db.cursor()

    # Get total number of songs
    song_count = cursor.execute("SELECT COUNT(*) FROM song").fetchone()[0]

    # Get job statistics for URL jobs
    url_jobs = cursor.execute(
        "SELECT state, COUNT(*) FROM job_url GROUP BY state"
    ).fetchall()

    # Get job statistics for file jobs
    file_jobs = cursor.execute(
        "SELECT state, COUNT(*) FROM job_file GROUP BY state"
    ).fetchall()

    # Combine job statistics
    job_stats = {}
    for state, count in url_jobs:
        job_stats[state] = job_stats.get(state, 0) + count

    for state, count in file_jobs:
        job_stats[state] = job_stats.get(state, 0) + count

    cursor.close()

    # Prepare data for template
    stats_data = {
        "songs_count": song_count,
        "jobs": {
            "processed": job_stats.get("finished", 0),
            "running": job_stats.get("running", 0) + job_stats.get("downloading", 0),
            "failed": job_stats.get("failed", 0),
            "waiting": job_stats.get("waiting", 0),
        },
    }

    return render_template("stats.html", **stats_data)


@app.route("/songs")
def songs():
    db = get_db()
    cursor = db.cursor()

    # Get all songs with their job status using JOIN
    songs_query = """
        SELECT s.id, s.title, s.artist, s.release_date, s.cover, 
               f.state as file_state, f.filename, 
               u.state as url_state, u.url
        FROM song s
        LEFT OUTER JOIN job_url u ON s.id = u.song_id
        LEFT OUTER JOIN job_file f ON s.id = f.song_id
        ORDER BY s.artist, s.title DESC
    """
    songs = cursor.execute(songs_query).fetchall()

    # Process the results
    songs_with_status = []
    for song in songs:
        (
            song_id,
            title,
            artist,
            release_date,
            cover,
            file_state,
            filename,
            url_state,
            url,
        ) = song

        # Determine import status and source
        import_status = url_state or file_state
        import_source = url or filename

        songs_with_status.append(
            {
                "hex_id": gen_hex_id(song_id),
                "title": title or "Unknown Title",
                "artist": artist or "Unknown Artist",
                "release_date": release_date or "Unknown",
                "cover": cover,
                "import_status": import_status or "unknown",
                "import_source": import_source or "unknown",
            }
        )

    cursor.close()
    return render_template("songs.html", songs=songs_with_status)


@app.route("/songs/<song_id>/delete", methods=["DELETE"])
def delete_song(song_id):
    # Convert hex_id back to integer for database operations
    song_int_id = int(song_id, 16)

    db = get_db()
    cursor = db.cursor()

    try:
        # Delete the song record (this will cascade to related job records)
        cursor.execute("DELETE FROM song WHERE id = ?", (song_int_id,))

        # Remove the audio file if it exists
        audio_file = f"{DATA_DIR}/{song_id}.m4a"
        if os.path.exists(audio_file):
            os.remove(audio_file)

        db.commit()
        logger.info(f"Deleted song {song_int_id}")

    except Exception as e:
        logger.error(f"Error deleting song {song_int_id}: {e}")
        db.rollback()

    cursor.close()
    return "deleted"


@app.route("/upload")
@app.route("/end")
def serve_template():
    page = request.path.lstrip("/") + ".html"
    return render_template(page)


@app.route("/upload", methods=["POST"])
def upload():
    url = request.form.get("url")
    playlist = request.form.get("playlist")

    urls = youtube_playlist_links(url) if playlist else [url] if url else []

    db = get_db()
    cursor = db.cursor()

    # potentially import uploaded files
    for key in request.files:
        file_list = request.files.getlist(key)
        for file in file_list:
            if not file.filename:
                continue
            logger.info("Adding file: %s", file.filename)
            song_id = random.randint(100000000, 999999999)
            hex_id = gen_hex_id(song_id)
            cursor.execute("insert into song (id) values (?)", (song_id,))
            db.commit()  # TODO: Handle primary key violation

            filename = f"{hex_id}.tmp"
            file.save(os.path.join(DATA_DIR, filename))
            cursor.execute(
                "insert into job_file values (?, ?, ?)",
                (song_id, filename, "waiting"),
            )
            db.commit()

    for url in urls:
        logger.info("Adding URL: %s", url)

        song_id = random.randint(100000000, 999999999)
        cursor.execute("insert into song (id) values (?)", (song_id,))
        db.commit()  # TODO: Handle primary key violation

        cursor.execute(
            "insert into job_url values (?, ?, ?, ?)", (song_id, url, "", "waiting")
        )
        db.commit()

    cursor.close()

    return redirect("/upload", code=302)


@app.route("/song/<song_id>")
def song(song_id):
    return send_from_directory(DATA_DIR, f"{song_id}.m4a", mimetype="audio/x-m4a")


@app.route("/game")
def new_game():
    db = get_db()
    cursor = db.cursor()

    game_id = random.randint(100000000, 999999999)
    cursor.execute("insert into game values (?, ?)", (game_id, None))
    db.commit()  # TODO: Handle primary key violation

    return redirect(f"/game/{game_id}", code=302)


@app.route("/game/<game_id>")
def next_song(game_id):
    db = get_db()
    cur = db.cursor()
    data = cur.execute(
        """
        select * from song s
        where not exists(
            select song_id from game
            where id = ?
            and song_id = s.id)
        and s.title not null
        order by random()
        limit 1""",
        (game_id,),
    )
    songs = list(data)
    if not songs:
        return redirect("/end", code=302)
    song = songs[0]
    song_id, title, artist, release_date, cover = song
    hex_id = hex(song_id)[2:]
    # mark song as listened
    cur.execute("insert into game values (?, ?)", (game_id, song_id))
    db.commit()
    return render_template(
        "player.html",
        game_id=game_id,
        song_id=hex_id,
        title=title,
        artist=artist,
        release_date=release_date,
        cover=cover,
    )


if __name__ == "__main__":
    app.run(debug=True, port=8000)
