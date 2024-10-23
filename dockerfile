FROM python:3.11.10-slim-bookworm AS build
WORKDIR /app
COPY . .
RUN mkdir pip && pip install -r requirements.txt -t /app/pip

FROM debian:bookworm-slim AS prod
WORKDIR /app
RUN apt update && apt install -y python3 && apt clean && rm -rf /var/lib/apt/lists/*
COPY --from=build /app/* .
ENTRYPOINT [ "python3", "/app/main.py" ]

