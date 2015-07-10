from rq import Queue
import redis
import time
import datetime
from utils import util
import dateutil.parser
import operator

import sys
sys.path.append('/home/parallels/Code/heroku-envbased/roboquant/strategies')
#print sys.path

from xiQuant_strategies import xiQuantStrategyUtil

tickerList = util.getTickerList('Abhi-26')

def test_parallel_strategy():
	import shutil

	# Tell RQ what Redis connection to use
	redis_conn = util.get_redis_conn()
	q = Queue(connection=redis_conn)  # no args implies the default queue
	import dateutil.parser
	yourdate = dateutil.parser.parse('2005-06-30T08:00:00.000Z')
	yourdate2 = dateutil.parser.parse('2014-12-31T08:00:00.000Z')

	jobList = []

	for ticker in tickerList:
		#jobList.append(q.enqueue(xiQuantStrategyUtil.run_strategy_TN, 20, ticker, 100000, yourdate, yourdate2))
		jobList.append(q.enqueue(xiQuantStrategyUtil.run_strategy_TN,20, ticker, 100000, yourdate, yourdate2, filterCriteria=10000, indicators=False))
		
	#### Wait in loop until all of them are successfull
	master_orders = [] #### populate master list of  orders dictionary...
	jobID = 1
	for job in jobList:
		try:
			print "Currently processing job id: ", jobID
			sleep = True
			while(sleep):
				time.sleep(1)
				if job.get_status() == 'failed' or job.get_status()=='finished':
					sleep = False
			if job.get_status() == 'finished' and any(job.result):
				master_orders.append(job.result)
				#master_orders.append(job.result.getOrdersFilteredByMomentumRank(filterCriteria=rank))
				#master_orders.append(job.result.getOrdersFilteredByRules())
			jobID +=1
		except Exception,e:
			print "Entered into exception block while processing:...", str(e)
			pass ### Make sure you move on with other job...

	print "successfully processed tickers"


	########### Iterate master orders file.... #############
	dataRows = []
	for k in range(len(master_orders)):
		for key, value in master_orders[k].iteritems():
			row = []
			row.append(key)
			row.append(value[0][0])
			row.append(value[0][1])
			row.append(value[0][2])
			row.append(value[0][3]) #### added for rank
			dataRows.append(row)

	######### before passing let's sort orders based on moneyness rank
	#####################################################################
	#sorted_datarows = sorted(dataRows, key = lambda x: (int(x[1]), int(x[3])))
	dataRows.sort(key = operator.itemgetter(0, 4))


	fake_csv = util.make_fake_csv(dataRows)
	print  "Successfully created master_orders fake_csv file...."

	############### Run the master order for computing portfolio#########
	jobPortfolio = q.enqueue(xiQuantStrategyUtil.run_master_strategy, 100000, fake_csv, datasource='TN')

	sleep = True
	while(sleep):
		time.sleep(1)
		if jobPortfolio.get_status() == 'failed' or jobPortfolio.get_status()=='finished':
			sleep = False

	print  "Successfully simulated portfolio"



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


