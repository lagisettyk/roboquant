import os

import redis
import urlparse
from rq import Worker, Queue, Connection

import sys

#sys.path.append('/home/parallels/Code/heroku-envbased/roboquant/strategies')
#print sys.path

listen = ['high', 'default', 'low']

redis_url = os.getenv('REDISCLOUD_URL', 'redis://localhost:6379')

url = urlparse.urlparse(redis_url)

#conn = redis.from_url(redis_url)

conn = redis.StrictRedis(host=url.hostname, port=url.port, password=url.password)

if __name__ == '__main__':
    with Connection(conn):
        worker = Worker(map(Queue, listen))
        worker.work()
