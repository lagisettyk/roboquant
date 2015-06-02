from utils import util

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
	import redis
	import datetime
	redisConn = util.get_redis_conn()
	redisConn.set('eod_latest', datetime.date.today())
	populate_redis_eod(redisConn, tickerList, datasource, startdate = datetime.date.today(), 
			  enddate = datetime.date.today(), popFirstElement=True)
	print ("Successfully populated eod data for: ", datetime.date.today()) 


def populate_redis_eod_history(datasource, tickerList):
	import redis
	import datetime
	redisConn = util.get_redis_conn()
	if redisConn.get('history') is None:
		populate_redis_eod(redisConn, tickerList, datasource, startdate = "2005/01/01", 
			  enddate=(datetime.date.today() - datetime.timedelta(days=1)), popFirstElement=False)
		print "successfully populated history..."
	else:
		print "History is already populated..."

def populate_redis_eod(redisConn, tickerList, datasource, startdate, enddate, popFirstElement):
	from Quandl import Quandl
	from time import mktime

	#### Based on data source shift the EOD pricing source...
	if datasource == 'EOD':
			DICT = EOD_DICT
	else:
			DICT = WIKI_DICT

	for ticker in range(len(tickerList)):
		try:
			mkt_data  = Quandl.get(
				datasource +"/" + tickerList[ticker], returns="numpy", sort_order="asc", authtoken="L5A6rmU9FGvyss9F7Eym",  
				trim_start = startdate, trim_end = enddate)

			if mkt_data.size > 0:
				for daily_data in mkt_data:
					redisConn.zadd(tickerList[ticker], mktime(daily_data[0].timetuple()), 
						str(daily_data[8]) + "|" + str(daily_data[9]) + "|" + str(daily_data[10]) + "|" + str(daily_data[11]) + "|" + str(daily_data[12]))
				if popFirstElement:
					redisConn.zremrangebyrank(tickerList[ticker], 0, 0)
				#print redisConn.zrange(tickerList[ticker], 0, -1)
		except Exception,e: 
			print str(e)
			pass
		print "populated EOD time series: ", tickerList[ticker]	
	redisConn.set('history', "TRUE")
	status = "successfully populated redis store...."
	return status



