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

def get_redis_conn():
	import os
	import redis
	import urlparse

	redis_url = os.environ.get('REDISCLOUD_URL', 'redis://localhost:6379')
	url = urlparse.urlparse(redis_url)
	print "$$$URL: ", url
	redisConn = redis.StrictRedis(host=url.hostname, port=url.port, password=url.password)
	return redisConn
	

def populate_redis_eod_today(datasource, tickerList):
	import redis
	import datetime
	redisConn = get_redis_conn()
	redisConn.set('eod_latest', datetime.date.today())
	populate_redis_eod(redisConn, tickerList, datasource, startdate = datetime.date.today(), 
			  enddate = datetime.date.today(), popFirstElement=True)
	print ("Successfully populated eod data for: ", datetime.date.today()) 


def populate_redis_eod_history(datasource, tickerList):
	import redis
	import datetime
	redisConn = get_redis_conn()
	if redisConn.get('history') is None:
		populate_redis_eod(redisConn, tickerList, datasource, startdate = "2012/01/01", 
			  enddate=(datetime.date.today() - datetime.timedelta(days=1)), popFirstElement=False)
		print "successfully populated history..."
	else:
		print "History is already populated..."

def populate_redis_eod(redisConn, tickerList, datasource, startdate, enddate, popFirstElement):
	from Quandl import Quandl
	import json
	import pandas
	import redis

	#### Based on data source shift the EOD pricing source...
	if datasource == 'EOD':
			DICT = EOD_DICT
	else:
			DICT = WIKI_DICT

	for ticker in range(len(tickerList)):

		for key in DICT:
			try:
				my_data  = Quandl.get(
					datasource +"/" + tickerList[ticker], returns="pandas", 
					column=DICT[key], sort_order="asc", authtoken="L5A6rmU9FGvyss9F7Eym",  
					trim_start = startdate, trim_end = enddate)
				if not my_data.empty:
					json_data = json.loads(my_data.to_json()) 
					json_data_list = list(sorted(json_data[key].items()))
					for x in range(len(json_data_list)):
						dl = list(json_data_list[x])
						### Store data in the sorted sets...
						redisConn.zadd(tickerList[ticker]+':'+key, dl[0], dl[1])
					### Please note on daily basis pop the oldest data so that TS size is always 3 years
					if popFirstElement:
						redisConn.zremrangebyrank(tickerList[ticker]+':'+key, 0, 0)
					print redisConn.zrange(tickerList[ticker]+':'+key, 0, -1)
			except Exception,e: 
				print str(e)
				pass
		print "populated EOD time series: ", tickerList[ticker]
	### Set history flag to true...
	redisConn.set('history', "TRUE")
	status = "successfully populated redis store...."
	return status
