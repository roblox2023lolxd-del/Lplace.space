import os
import json
from typing import Optional

from redis import Redis
from rq import Queue

REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
try:
    _redis = Redis.from_url(REDIS_URL, decode_responses=True)
    _queue = Queue('default', connection=_redis)
except Exception:
    # If Redis is unavailable at import time (dev machines), create placeholders
    _redis = None
    _queue = None

# Cache TTL for Discord check results (seconds)
CACHE_TTL = int(os.environ.get('DISCORD_CACHE_TTL', 24 * 3600))


def _key(username: str) -> str:
    return f"discord:{username.lower()}"


def cache_result(username: str, available: bool, reason: str) -> None:
    payload = {'available': bool(available), 'reason': reason}
    try:
        if _redis:
            _redis.set(_key(username), json.dumps(payload), ex=CACHE_TTL)
    except Exception:
        # ignore cache failures
        return


def get_cached(username: str) -> Optional[dict]:
    if not _redis:
        return None
    try:
        v = _redis.get(_key(username))
    except Exception:
        return None
    if not v:
        return None
    try:
        return json.loads(v)
    except Exception:
        return None


def enqueue_check(username: str):
    # Enqueue a check job that will call `check_and_cache` in this module.
    # We return the job id for tracking if callers want it.
    if not _queue:
        # Fall back to running synchronously if Redis/RQ unavailable
        try:
            return check_and_cache(username)
        except Exception:
            return None
    try:
        job = _queue.enqueue(check_and_cache, username)
        return job.id
    except Exception:
        # Fall back to sync run on enqueue failure
        try:
            return check_and_cache(username)
        except Exception:
            return None


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
