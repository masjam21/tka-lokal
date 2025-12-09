import os

import redis
from rq import Worker, Queue, Connection
from dotenv import load_dotenv

load_dotenv(".env")


redis_url = os.environ.get("REDISTOGO_URL", "redis://localhost:6379")
#redis_pool = redis.ConnectionPool.from_url(redis_url) #kode tambahan
#conn = redis.Redis(connection_pool=redis_pool) #kode tambahan

listen = ["default"]

conn = redis.from_url(redis_url) || code asli

#kode tambahan optimalisasi
#

if __name__ == "__main__":
    with Connection(conn):
        worker = Worker(list(map(Queue, listen)))
        worker.work() 
