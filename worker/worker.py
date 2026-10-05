import redis
import psycopg2
import json
import time
import os

# Connect to Redis - Railway requires authentication
redis_url = os.getenv('REDIS_URL')
redis_host = os.getenv('REDIS_HOST', 'redis')

if redis_url:
    # Use REDIS_URL (includes password)
    r = redis.Redis.from_url(redis_url, decode_responses=False)
else:
    # Fallback for local development
    r = redis.Redis(host=redis_host, port=6379, db=0)


def get_db_connection():
    database_url = os.getenv('DATABASE_URL')

    if database_url:
        # psycopg2 >= 2.8 supports direct URL connection
        return psycopg2.connect(database_url)

    # Fallback to individual environment variables
    return psycopg2.connect(
        host=os.getenv('PGHOST', os.getenv('DB_HOST', 'db')),
        database=os.getenv('PGDATABASE', 'votes'),
        user=os.getenv('PGUSER', 'postgres'),
        password=os.getenv('PGPASSWORD', 'postgres'),
        port=int(os.getenv('PGPORT', '5432'))
    )


def connect_with_retry(attempts=30, delay=2):
    """Wait for Postgres to accept connections instead of sleeping a fixed time."""
    for attempt in range(1, attempts + 1):
        try:
            return get_db_connection()
        except psycopg2.OperationalError as e:
            print(f"[DB] Not ready (attempt {attempt}/{attempts}): {e}")
            time.sleep(delay)
    raise RuntimeError("Could not connect to PostgreSQL")


def create_table(conn):
    with conn.cursor() as cur:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS votes (
                id VARCHAR(255) PRIMARY KEY,
                vote VARCHAR(255) NOT NULL
            )
        ''')
    conn.commit()


def save_vote(conn, voter_id, vote):
    # Insert or update vote (one vote per voter, last choice wins)
    with conn.cursor() as cur:
        cur.execute('''
            INSERT INTO votes (id, vote)
            VALUES (%s, %s)
            ON CONFLICT (id)
            DO UPDATE SET vote = EXCLUDED.vote
        ''', (voter_id, vote))
    conn.commit()


def process_votes(conn):
    while True:
        # Get vote from Redis queue
        try:
            data = r.blpop('votes', timeout=5)
        except redis.RedisError as e:
            print(f"[Redis] Error: {e}")
            time.sleep(1)
            continue

        if not data:
            continue

        vote_data = json.loads(data[1])
        voter_id = vote_data['voter_id']
        vote = vote_data['vote']

        # Store in Postgres, reconnecting once if the connection dropped
        try:
            save_vote(conn, voter_id, vote)
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
            print(f"[DB] Connection lost ({e}), reconnecting...")
            conn = connect_with_retry()
            save_vote(conn, voter_id, vote)

        print(f"Processed vote: {voter_id} -> {vote}")


if __name__ == '__main__':
    print("Worker starting...")

    conn = connect_with_retry()
    create_table(conn)
    print("Database ready!")

    process_votes(conn)
