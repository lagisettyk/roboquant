from rq import Queue
import redis
from update_redis_ds import populate_redis_eod_history, populate_redis_eod_today
import time
import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
import os
import urlparse
import sys



sched = BlockingScheduler()

def get_redis_conn():
	redis_url = os.getenv('REDISCLOUD_URL', 'redis://localhost:6379')
	print redis_url
	url = urlparse.urlparse(redis_url)
	print "$$$URL: ", url
	redisConn = redis.StrictRedis(host=url.hostname, port=url.port, password=url.password)
	return redisConn
'''
#@sched.scheduled_job('interval', minutes=1)
def test_simple_strategy():
	# Tell RQ what Redis connection to use
	redis_conn = get_redis_conn()
	q = Queue(connection=redis_conn)  # no args implies the default queue
	job = q.enqueue(simple_strategy.run_strategy_redis, "AAPL")
	#print job.result   # => None
	while (job.result is None):
		time.sleep(1)
	
	print job.result   # => 889

test_simple_strategy()

'''
@sched.scheduled_job('interval', minutes=45)
#@sched.scheduled_job('date')
def timed_job():
	print('This job is run immideately...')
	# Tell RQ what Redis connection to use
	redis_conn = get_redis_conn()
	q = Queue(connection=redis_conn)  # no args implies the default queue
	job = q.enqueue(populate_redis_eod_history, "WIKI", ['AAPL', 'MSFT', 'GS'])
	print job.result   # => None
	time.sleep(60)
	print job.result   # => 889


#@sched.scheduled_job('interval', minutes=1)
@sched.scheduled_job('cron', day_of_week='mon-fri', hour=17)
def scheduled_job():
	print('This job is run every weekday at 7pm.')
	redis_conn = get_redis_conn()
	q = Queue(connection=redis_conn)
	job = q.enqueue(populate_redis_eod_today, "WIKI", ['AAPL', 'MSFT', 'GS'])
	print job.result   # => None
	time.sleep(10)
	print job.result   # => 889


sched.start()


