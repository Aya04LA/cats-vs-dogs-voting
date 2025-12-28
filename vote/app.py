from flask import Flask, render_template, request, make_response
import redis
import os
import random
import json

app = Flask(__name__)

# --- Redis connection (Railway-compatible) ---
redis_url = os.getenv("REDIS_URL")
if not redis_url:
    raise RuntimeError("REDIS_URL is not set")

r = redis.Redis.from_url(
    redis_url,
    decode_responses=True
)

option_a = "Cats"
option_b = "Dogs"

@app.route('/', methods=['GET', 'POST'])
def vote():
    voter_id = request.cookies.get('voter_id')

    if request.method == 'POST':
        vote = request.form.get('vote')

        if not voter_id:
            voter_id = hex(random.getrandbits(64))[2:]

        data = json.dumps({'voter_id': voter_id, 'vote': vote})
        r.rpush('votes', data)

        resp = make_response(render_template(
            'vote.html',
            option_a=option_a,
            option_b=option_b,
            voted=True,
            vote=vote
        ))
        resp.set_cookie('voter_id', voter_id)
        return resp

    has_voted = voter_id is not None
    return render_template(
        'vote.html',
        option_a=option_a,
        option_b=option_b,
        voted=has_voted
    )

if __name__ == '__main__':
    redis_port = int(os.getenv('REDIS_PORT', 6379))
  # fallback for local testing
    app.run(host='0.0.0.0', port=port, debug=True)

