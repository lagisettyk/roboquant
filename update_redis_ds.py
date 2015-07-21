from utils import util
import datetime
#from time import calendar.timegm
import dateutil.parser
from Quandl import Quandl
import redis
import os
import calendar

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

def populate_redis_eod_today_raw(datasource, tickerList):

	redisConn = util.get_redis_conn()
	populate_redis_eod_raw(redisConn, tickerList, datasource, startdate=datetime.date.today(), 
			  enddate = datetime.date.today())
	### set last available data date in the data store...
	redisConn.set('eod_latest', datetime.date.today())

	logger.info("Successfully populated eod data for: " + datetime.date.today().strftime("%B %d, %Y")) 

def populate_redis_eod_raw(redisConn, tickerList, datasource, startdate, enddate):
	import math

	for ticker in range(len(tickerList)):
		if redisConn.get('history') is not None:
			#### Let's get the last date available for this ticker and set it to start date
			### this allows to catch-up EOD data in case certain days EOD feed was not successfully populated...
			seconds = calendar.timegm(datetime.date.today().timetuple())
			seconds2 = calendar.timegm(dateutil.parser.parse(histStartDate).timetuple())
			redis_data = redisConn.zrevrangebyscore(tickerList[ticker] +":EODRAW", int(seconds), int(seconds2), 0, -1, True)
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
					#### Check for NaN's if so do not insert NAN values....
					dateStr = daily_data[0]
					Open = daily_data[1]
					High = daily_data[2]
					Low = daily_data[3]
					Close = daily_data[4]
					Volume = daily_data[5]
					AdjClose = daily_data[11] #### Adjusted close
					Dividend = daily_data[6]
					Split = daily_data[7]

					if (not math.isnan(Open)) and (not math.isnan(High)) and (not math.isnan(Low)) and (not math.isnan(Close)) and (not math.isnan(Volume)):
						redisConn.zadd(tickerList[ticker] +":EODRAW", calendar.timegm(dateStr.timetuple()), 
							str(Open) + "|" + str(High) + "|" + str(Low) + "|" + str(Close) 
					 			+ "|" + str(Volume) +"|"+str(AdjClose) +"|" + str(Dividend) +"|" + str(Split))
		except Exception,e: 
			logger.debug(tickerList[ticker] +": " + str(e))
			pass
		logger.info("populated EOD time series: " + tickerList[ticker] + " " + startdate.strftime("%B %d, %Y") + " : " + enddate.strftime("%B %d, %Y"))	
	redisConn.set('history', "TRUE")
	status = "successfully populated redis store...."
	return status

	

