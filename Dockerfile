FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV PORT=8080
EXPOSE $PORT
WORKDIR /app

COPY requirements.txt ./
RUN uv pip install --system --compile-bytecode --only-binary=:all: -r requirements.txt

COPY app.py alto_utils.py download_utils.py image_utils.py metadata_utils.py ./
COPY templates ./templates
COPY static ./static

# Warm up caches
RUN python -c 'import flask, requests, matplotlib, PIL'

# set APP_ROOT
ENV APP_ROOT=/run/alto-viewer/app

CMD gunicorn --bind 0.0.0.0:${PORT} --workers 2 --timeout 120 app:app
