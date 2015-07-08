from utils import util
import datetime
from time import mktime
import dateutil.parser
from Quandl import Quandl
import redis
import os

import sys
sys.path.append(os.path.dirname(__file__)+'/strategies')

#print sys.path

from xiQuant_strategies import xiQuantStrategyUtil

### Initialize global...
histStartDate = '2005-01-01'
#logger = util.getLogger('Quandl.log')
logger = util.Log

#########Redis Commands for reference purpose...
# Min Score in a given ZSET: ZRANGEBYSCORE myset -inf +inf WITHSCORES LIMIT 0 1
# redisConn.zrangebyscore(ticker, int(seconds), int(seconds2), 0, -1, True)
# Max Score in a given ZSET: ZREVRANGEBYSCORE myset +inf -inf WITHSCORES LIMIT 0 1
### Below dictionaries are for just reference purpose....

EOD_DICT = {
	'Adj_Open':    "8",
    'Adj_High':    "9",
    'Adj_Low':     "10",
    'Adj_Close':   "11",
    'Adj_Volume':  "12",
}
WIKI_DICT = {
	'Adj. Open':    "8",
    'Adj. High':    "9",
    'Adj. Low':     "10",
    'Adj. Close':   "11",
    'Adj. Volume':  "12",
}
	

def populate_redis_eod_today(datasource, tickerList):

	redisConn = util.get_redis_conn()
	populate_redis_eod(redisConn, tickerList, datasource, startdate=datetime.date.today(), 
			  enddate = datetime.date.today())
	### set last available data date in the data store...
	redisConn.set('eod_latest', datetime.date.today())

	logger.info("Successfully populated eod data for: " + datetime.date.today().strftime("%B %d, %Y")) 


def populate_redis_eod_history(datasource, tickerList):

	redisConn = util.get_redis_conn()
	if redisConn.get('history') is None:
		populate_redis_eod(redisConn, tickerList, datasource, startdate=dateutil.parser.parse(histStartDate), 
			  enddate=(datetime.date.today() - datetime.timedelta(days=1)))
		logger.info("successfully populated history...")
	else:
		logger.info("History is already populated...")

def populate_redis_eod(redisConn, tickerList, datasource, startdate, enddate):

	for ticker in range(len(tickerList)):
		if redisConn.get('history') is not None:
			#### Let's get the last date available for this ticker and set it to start date
			### this allows to catch-up EOD data in case certain days EOD feed was not successfully populated...
			seconds = mktime(datetime.date.today().timetuple())
			seconds2 = mktime(dateutil.parser.parse(histStartDate).timetuple())
			redis_data = redisConn.zrevrangebyscore(tickerList[ticker] +":EOD", int(seconds), int(seconds2), 0, -1, True)
			if len(redis_data) > 0:
				list_values, list_keys = zip(*redis_data) ### Returns max score in the data store
				startdate = datetime.datetime.fromtimestamp(list_keys[0]) ### convert max score to date range...
			else:
				### New ticker populate entire history.... set start date to historical start date
				startdate = dateutil.parser.parse(histStartDate)
		try:
			mkt_data  = Quandl.get(
				datasource +"/" + tickerList[ticker], returns="numpy", sort_order="asc", authtoken="L5A6rmU9FGvyss9F7Eym",  
				trim_start = startdate, trim_end = enddate)
			if mkt_data.size > 0:
				for daily_data in mkt_data:
					redisConn.zadd(tickerList[ticker] +":EOD", mktime(daily_data[0].timetuple()), 
					str(daily_data[8]) + "|" + str(daily_data[9]) + "|" + str(daily_data[10]) + "|" + str(daily_data[11]) + "|" + str(daily_data[12]))
		except Exception,e: 
			logger.debug(tickerList[ticker] +": " + str(e))
			pass
		logger.info("populated EOD time series: " + tickerList[ticker] + " " + startdate.strftime("%B %d, %Y") + " : " + enddate.strftime("%B %d, %Y"))	
	redisConn.set('history', "TRUE")
	status = "successfully populated redis store...."
	return status

def populate_redis_moneyflow(redisConn, tickerList, startdate, enddate):

	for ticker in range(len(tickerList)):
		moneyflowList = xiQuantStrategyUtil.cashflow_timeseries_TN(tickerList[ticker], startdate, enddate)
		print "Currently processing ticker: ", ticker
		for k in range(len(moneyflowList)):
			if moneyflowList[k][1] is not None:
				try:
					redisConn.zadd("cashflow:"+str(moneyflowList[k][0]), float(moneyflowList[k][1]), tickerList[ticker])
				except Exception,e: 
					logger.debug(tickerList[ticker] +": cashflow data issue" + str(e))
					pass
	status = "successfully populated redis store with cashflow data..."
	return status

def populate_redis_moneyflow_history(tickerList):
	redisConn = util.get_redis_conn()
	return populate_redis_moneyflow(redisConn, tickerList, startdate=dateutil.parser.parse(histStartDate), 
		                                                  enddate=(datetime.date.today() - datetime.timedelta(days=1)))



	

