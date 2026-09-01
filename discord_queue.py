import os
import json
from typing import Optional

from redis import Redis
from rq import Queue

REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
_redis = Redis.from_url(REDIS_URL, decode_responses=True)
_queue = Queue('default', connection=_redis)

# Cache TTL for Discord check results (seconds)
CACHE_TTL = int(os.environ.get('DISCORD_CACHE_TTL', 24 * 3600))


def _key(username: str) -> str:
    return f"discord:{username.lower()}"


def cache_result(username: str, available: bool, reason: str) -> None:
    payload = {'available': bool(available), 'reason': reason}
    _redis.set(_key(username), json.dumps(payload), ex=CACHE_TTL)


def get_cached(username: str) -> Optional[dict]:
    v = _redis.get(_key(username))
    if not v:
        return None
    try:
        return json.loads(v)
    except Exception:
        return None


def enqueue_check(username: str):
    # Enqueue a check job that will call `check_and_cache` in this module.
    # We return the job id for tracking if callers want it.
    job = _queue.enqueue(check_and_cache, username)
    return job.id


def check_and_cache(username: str):
    # Worker-executed function: perform the Discord check and cache the result.
    try:
        # Import inside function to avoid heavy imports in web process
        from . import discord_check
    except Exception:
        import discord_check

    ok, reason = discord_check.check_discord_username(username, headless=True)
    cache_result(username, ok, reason)
    return {'available': ok, 'reason': reason}
