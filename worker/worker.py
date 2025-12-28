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

import urllib.parse as up

def get_db_connection():
    # ... rest of your code stays the same
    database_url = os.getenv('DATABASE_URL')
    
    try:
        if database_url:
            # psycopg2 >= 2.8 supports direct URL connection
            return psycopg2.connect(database_url)
        else:
            # Fallback to individual environment variables
            host = os.getenv('PGHOST', os.getenv('DB_HOST', 'db'))
            dbname = os.getenv('PGDATABASE', 'votes')
            user = os.getenv('PGUSER', 'postgres')
            password = os.getenv('PGPASSWORD', 'postgres')
            port = int(os.getenv('PGPORT', '5432'))
            
            return psycopg2.connect(
                host=host,
                database=dbname,
                user=user,
                password=password,
                port=port
            )
    except Exception as e:
        # Only print if connection fails
        print(f"[DB ERROR] Failed to connect to PostgreSQL: {e}")
        raise

def create_table():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS votes (
            id VARCHAR(255) PRIMARY KEY,
            vote VARCHAR(255) NOT NULL
        )
    ''')
    conn.commit()
    cur.close()
    conn.close()

def process_votes():
    while True:
        try:
            # Get vote from Redis queue
            data = r.blpop('votes', timeout=5)
            
            if data:
                vote_data = json.loads(data[1])
                voter_id = vote_data['voter_id']
                vote = vote_data['vote']
                
                # Store in Postgres
                conn = get_db_connection()
                cur = conn.cursor()
                
                # Insert or update vote
                cur.execute('''
                    INSERT INTO votes (id, vote) 
                    VALUES (%s, %s)
                    ON CONFLICT (id) 
                    DO UPDATE SET vote = EXCLUDED.vote
                ''', (voter_id, vote))
                
                conn.commit()
                cur.close()
                conn.close()
                
                print(f"Processed vote: {voter_id} -> {vote}")
        
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(1)

if __name__ == '__main__':
    print("Worker starting...")
    
    # Wait for database to be ready
    time.sleep(5)
    
    # Create table
    create_table()
    print("Database ready!")
    
    # Start processing votes
    process_votes()