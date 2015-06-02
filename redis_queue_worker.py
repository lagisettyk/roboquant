#import redis
from rq import Worker, Queue, Connection
from utils import util

#import sys
#sys.path.append('/home/parallels/Code/heroku-envbased/roboquant/strategies')
#print sys.path

listen = ['high', 'default', 'low']
conn = util.get_redis_conn()

if __name__ == '__main__':
    with Connection(conn):
        worker = Worker(map(Queue, listen))
        worker.work()
