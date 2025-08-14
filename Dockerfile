FROM alpine:latest AS unzipper

RUN apk add curl xz
RUN curl -f -o /ffmpeg-7.0.2-amd64-static.tar.xz https://radosgw.public.os.wwu.de/opencast-ffmpeg-static/ffmpeg-7.0.2-amd64-static.tar.xz
RUN tar xfv /ffmpeg-7.0.2-amd64-static.tar.xz


FROM python:3.13-slim
EXPOSE 8000

RUN pip install --no-cache-dir \
  flask \
  gunicorn \
  audioop-lts \
  shazamio \
  yt-dlp \
  && ln -s /usr/local/bin/yt-dlp /usr/bin/yt-dlp

COPY hackstar.py /app/hackstar.py
COPY static /app/static
COPY templates /app/templates
WORKDIR /app
RUN mkdir /app/data /app/db

COPY --from=unzipper /ffmpeg-7.0.2-amd64-static/ffmpeg /usr/bin/ffmpeg
COPY --from=unzipper /ffmpeg-7.0.2-amd64-static/ffprobe /usr/bin/ffprobe

CMD [ "gunicorn", "--bind", "0.0.0.0:8000", "hackstar:app" ]
