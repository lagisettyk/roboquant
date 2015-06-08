from rq import Queue
import redis
from update_redis_ds import populate_redis_eod_history, populate_redis_eod_today
import time
import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from utils import util


tickerList = util.getTickerList()

'''
def test_simple_strategy():
	# Tell RQ what Redis connection to use
	redis_conn = get_redis_conn()
	q = Queue(connection=redis_conn)  # no args implies the default queue
	import dateutil.parser
	yourdate = dateutil.parser.parse('2012-01-01T08:00:00.000Z')
	yourdate2 = dateutil.parser.parse('2014-12-31T08:00:00.000Z')
	job = q.enqueue(xiQuantStrategyUtil.run_strategy_redis, 20, "NFLX", 100000, yourdate, yourdate2)
	while (job.result is None):
		print job.result
		time.sleep(1)
	
	print job.result.getSeries("upper")   # => 889

test_simple_strategy()
'''


def get_redis_conn():
	return util.get_redis_conn()

sched = BlockingScheduler()

#@sched.scheduled_job('interval', minutes=45)
#@sched.scheduled_job('date')
def timed_job():
	print('This job is run immideately...')
	# Tell RQ what Redis connection to use
	redis_conn = get_redis_conn()
	print('This job is run immideately...$$$$$$$$$$$$$')
	q = Queue(connection=redis_conn)  # no args implies the default queue
	job = q.enqueue(populate_redis_eod_history, "EOD", tickerList)
	print job.result   # => None
	time.sleep(600)
	print job.result   # => 889

@sched.scheduled_job('date')
#@sched.scheduled_job('cron', day_of_week='mon-fri', hour=17)
def scheduled_job():
	print('This job is run every weekday at 7pm.')
	redis_conn = get_redis_conn()
	q = Queue(connection=redis_conn)
	job = q.enqueue(populate_redis_eod_today, "EOD", tickerList)
	print job.result   # => None
	time.sleep(10)
	print job.result   # => 889


sched.start()


