from rq import Queue
import redis
from update_redis_ds import populate_redis_eod_history, populate_redis_eod_today
import time
import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from utils import util
import dateutil.parser

#import sys
#sys.path.append('/home/parallels/Code/heroku-envbased/roboquant/strategies')
#print sys.path

#from xiQuant_strategies import xiQuantStrategyUtil

#tickerList = util.getTickerListWithSPY()
tickerList = util.getTickerList()

'''
def test_parallel_strategy():
	import shutil

	# Tell RQ what Redis connection to use
	redis_conn = util.get_redis_conn()
	q = Queue(connection=redis_conn)  # no args implies the default queue
	import dateutil.parser
	yourdate = dateutil.parser.parse('2005-01-01T08:00:00.000Z')
	yourdate2 = dateutil.parser.parse('2014-12-31T08:00:00.000Z')

	jobList = []

	for ticker in tickerList:
		#job = q.enqueue(xiQuantStrategyUtil.run_strategy_redis, 20, ticker, 100000, yourdate, yourdate2)
		jobList.append(q.enqueue(xiQuantStrategyUtil.run_strategy_redis, 20, ticker, 100000, yourdate, yourdate2))

	#### Wait in loop until all of them are successfull
	jobID = 1
	for job in jobList:
		print "Currently processing job id: ", jobID
		while (job.result is None):
			time.sleep(1)
		jobID +=1

	print  "Successfully processed...."

	########### Merge files to create master file #############
	curDir = util.getCurrentDir()
	dest = curDir+"/orders/"+'MasterOrder.csv'
	for ticker in tickerList:
		src = curDir+"/orders/"+'orders_'+ticker+".csv"
		with open(src, 'rb') as fsrc:
			with open(dest, 'a') as fdest:
				shutil.copyfileobj(fsrc, fdest, 50000)
				print "Copied file: ", src

	print  "Successfully merged files...."


def process_Options_History():

	redis_conn = util.get_redis_conn()
	q = Queue(connection=redis_conn)  # no args implies the default queue
	dt = dateutil.parser.parse('2013-11-01T08:00:00.000Z')
	jobList = []
	jobID = []

	print "Initializing options filter processing"

	while dt <= dateutil.parser.parse('2013-11-30T08:00:00.000Z'):

		#try:

		dtStr = dt.strftime('%Y%m%d')
		currentDir = util.getCurrentDir()

		inputfilepath = currentDir + '/options/'
		inputfile = inputfilepath + 'L3_options_'+ dtStr +'.csv'

		outputfilepath = currentDir + '/filteredoptions/'
		outputfile = outputfilepath +'filteredOptions_'+ dtStr + '.csv'

		jobList.append(q.enqueue(xiQuantStrategyUtil.processOptionsFile, inputfile, outputfile))
		jobID.append(inputfile)
		print "Added to queue JOB ID: ", inputfile
		#xiQuantStrategyUtil.processOptionsFile(inputfile, outputfile)

		if dt.date().weekday() == 4 :
			dt = dt + datetime.timedelta(days=3)
		else:
			dt = dt + datetime.timedelta(days=1)
		#except :
			#pass #### Files are missing due to holidays...

	#### Wait in loop until all of them are successfull
	i = 0
	for job in jobList:
		print "Currently processing file: ", jobID[i]
		while (job.result is None):
			time.sleep(1)
		i +=1

	print  "Successfully processed...."

	
test_parallel_strategy()
#process_Options_History()

'''

def get_redis_conn():
	return util.get_redis_conn()

sched = BlockingScheduler()

#@sched.scheduled_job('interval', minutes=45)
@sched.scheduled_job('date')
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

#@sched.scheduled_job('date')
@sched.scheduled_job('cron', day_of_week='mon-fri', hour=17)
def scheduled_job():
	print('This job is run every weekday at 7pm.')
	redis_conn = get_redis_conn()
	q = Queue(connection=redis_conn)
	job = q.enqueue(populate_redis_eod_today, "EOD", tickerList)
	print job.result   # => None
	time.sleep(10)
	print job.result   # => 889


sched.start()


