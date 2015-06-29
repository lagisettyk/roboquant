from rq import Queue
import redis
from update_redis_ds import populate_redis_eod_history, populate_redis_eod_today
import time
import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from utils import util
import dateutil.parser


#tickerList = util.getTickerListWithSPY()
tickerList = util.getTickerList('CBOE-ALL')

def get_redis_conn():
	return util.get_redis_conn_nopool()

sched = BlockingScheduler()

#@sched.scheduled_job('interval', minutes=45)
#@sched.scheduled_job('date')
def timed_job():
	print('This job is run immideately...')
	# Tell RQ what Redis connection to use
	redis_conn = util.get_redis_conn()
	print('This job is run immideately...$$$$$$$$$$$$$')
	q = Queue(connection=redis_conn)  # no args implies the default queue
	job = q.enqueue(populate_redis_eod_history, "EOD", tickerList)
	print job.result   # => None
	time.sleep(600)
	print job.result   # => 889

#@sched.scheduled_job('date')
@sched.scheduled_job('cron', day_of_week='mon-fri', hour=17)
def scheduled_job():
	print('This job is run every weekday at 7pm.')
	redis_conn = util.get_redis_conn()
	q = Queue(connection=redis_conn)
	job = q.enqueue(populate_redis_eod_today, "EOD", tickerList)
	print job.result   # => None
	time.sleep(10)
	print job.result   # => 889


sched.start()


