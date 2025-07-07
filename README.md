# hack·star

Get started:

```sh
❯ python -m venv venv
❯ . ./venv/bin/activate
❯ pip install -r requirements.txt
❯ python -m gunicorn --bind 0.0.0.0:8000 hackstar:app
```

Use `docker` or `podman`:

```sh
podman run -it --rm -p 127.0.0.1:8000:8000 ghcr.io/...:main
```

A `docker-compose.yml` with reverse proxy and HTTPS with valid TLS vertificate:

```yml
services:
  hackstar:
    image: ghcr.io/...:main
    restart: always
    volumes:
      - /....db:/app/hack-star.db
    networks:
      - hackstar

  caddy:
    image: docker.io/library/caddy:2-alpine
    command: caddy reverse-proxy --to hackstar:8000 --from star.hacky.day
    ports:
      - 80:80
      - 443:443
    restart: always
    networks:
      - hackstar

networks:
  hackstar:
```
