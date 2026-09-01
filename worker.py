#!/usr/bin/env python3
"""Run a simple RQ worker for the project's default queue.

Usage: REDIS_URL=redis://... python3 worker.py
Or run via `rq worker` if preferred.
"""
import os
from redis import Redis
from rq import Worker, Queue, Connection

redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
listen = ['default']

conn = Redis.from_url(redis_url, decode_responses=True)

if __name__ == '__main__':
    with Connection(conn):
        worker = Worker(list(map(Queue, listen)))
        worker.work()
