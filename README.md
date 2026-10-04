# 🐱 vs 🐶 Voting App

A small distributed voting app built from five containers: two web apps in different languages,
a background worker, a queue, and a database. It shows how microservices talk to each other
through Redis and PostgreSQL, and runs locally with Docker Compose or deployed on Railway.

## Architecture

```
            ┌──────────────┐        ┌─────────┐        ┌──────────────┐
  browser ─>│ vote (Flask) │─push──>│  Redis  │─pop───>│ worker (Py)  │
            │   :8082      │        │  queue  │        └──────┬───────┘
            └──────────────┘        └─────────┘               │ upsert
                                                              ▼
            ┌──────────────┐                          ┌──────────────┐
  browser ─>│ result (Node)│<────── SELECT ───────────│  PostgreSQL  │
            │   :8081      │                          └──────────────┘
            └──────────────┘
```

| Service | Stack | Role |
| --- | --- | --- |
| `vote` | Python · Flask | Voting page; pushes `{voter_id, vote}` onto a Redis list |
| `worker` | Python | Pops votes from Redis and upserts them into Postgres (one vote per voter, last choice wins) |
| `result` | Node.js · Express | Results page; reads the tally from Postgres via `/api/results` |
| `redis` | Redis | Queue between the vote app and the worker |
| `db` | PostgreSQL 15 | Persistent vote storage |

The front-end apps sit on a `front-tier` network; Redis and Postgres are only reachable on the
internal `back-tier` network.

## Run locally

Requires Docker Desktop.

```bash
cp .env.example .env      # then set your own POSTGRES_PASSWORD
docker compose up --build
```

- Vote: <http://localhost:8082>
- Results: <http://localhost:8081>

Each browser gets a `voter_id` cookie, so voting again changes your vote instead of adding one.

## Configuration

| Variable | Service | Default |
| --- | --- | --- |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | db (via `.env`) | `postgres` / `postgres` / `votes` |
| `DATABASE_URL` | worker, result | built from the values above in `docker-compose.yml` |
| `REDIS_URL` or `REDIS_HOST` | vote, worker | `redis` |
| `PORT` | vote, result | `80` |

## Deploying to Railway

Each folder (`vote/`, `result/`, `worker/`) deploys as its own Railway service from its
Dockerfile. Add the Redis and PostgreSQL plugins, then reference their `REDIS_URL` and
`DATABASE_URL` variables in the services. Railway sets `PORT` automatically.

## CI

`.github/workflows/ci.yml` builds every image on each push, starts the stack, casts three votes,
and checks that `/api/results` returns the right tally.
