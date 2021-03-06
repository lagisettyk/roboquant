### Redis related Utility functions...
import redis
import os
import urlparse
import logging
import logging.handlers
import csv
import dateutil.parser
import StringIO
import datetime

redis_url=os.getenv('REDISCLOUD_URL', 'redis://localhost:6379')
url = urlparse.urlparse(redis_url)
pool = redis.ConnectionPool(host=url.hostname, port=url.port, password=url.password, db=0)
tickerList = []
Log = None


def get_redis_conn(redis_url=os.getenv('REDISCLOUD_URL', 'redis://localhost:6379')):
	#url = urlparse.urlparse(redis_url)
	#print "$$$URL: ", url
	#return redis.StrictRedis(host=url.hostname, port=url.port, password=url.password)
	return redis.StrictRedis(connection_pool=pool)

def get_redis_conn_nopool(redis_url=os.getenv('REDISCLOUD_URL', 'redis://localhost:6379')):
	url = urlparse.urlparse(redis_url)
	#print "$$$URL: ", url
	return redis.StrictRedis(host=url.hostname, port=url.port, password=url.password)
	#return redis.StrictRedis(connection_pool=pool)


def make_fake_csv(data):
    """Returns a populdated fake csv file object """
    fake_csv = StringIO.StringIO()
    fake_writer = csv.writer(fake_csv, delimiter=',')
    fake_writer.writerows(data) ########## data is nothing but list of lists....
    fake_csv.seek(0)
    return fake_csv

def getCurrentDir():
	return os.path.dirname(__file__)  # get current directory

def getRelativePath(filename):
	return os.path.join(getCurrentDir(), filename)  # get current directory

def getTickerListWithSPY():
	tickerListWithSPY = ['AAPL', 'AMZN', 'FDX', 'MA', 'NFLX', 'OCR', 'GD','NXPI', 'CVS', 'UNP', 'GILD', 'VRX', 'XLF','GOOG', 'CF', 'URI', 'CP', 'WHR', 'IWM', 'UNH', 'VIAB', 'FLT', \
	 'ODFL', 'ALL', 'V', 'SPY']

	return tickerListWithSPY


def getTickerList(strategy):

	if (len(tickerList) == 0):
		if strategy == 'CBOE-r100':
			file_tickerlist = getRelativePath('cboesymbol.csv')
		if strategy == 'SP-500':
			file_tickerlist = getRelativePath('SP500.csv')
		if strategy == 'CBOE-r1000':
			file_tickerlist = getRelativePath('cboesymbol_1000.csv')
		if strategy == 'CBOE-ALL':
			file_tickerlist = getRelativePath('cboesymbol_master.csv')
		if strategy == 'Abhi-26':
			file_tickerlist = getRelativePath('Abhi_26.csv')
		if strategy == 'SP-100':
			file_tickerlist = getRelativePath('SP100.csv')
		if strategy == 'CUSTOM-RANK5':
			file_tickerlist = getRelativePath('CUSTOM-RANK5.csv')
		if strategy == 'FTSE-100':
			file_tickerlist = getRelativePath('FTSE-100.csv')
		if strategy == 'HKG-100':
			file_tickerlist = getRelativePath('HKG-100.csv')
		if strategy == 'xiQuant-100':
			file_tickerlist = getRelativePath('xiQuant100.csv')
		if strategy == 'xiQuant-99':
			file_tickerlist = getRelativePath('xiQuant99.csv')
		if strategy == 'SMA20-CUSTOMUNIV':
			file_tickerlist = getRelativePath('SMA20-CUSTOMUNIV.csv')
		if strategy == 'xiQuant-50':
			file_tickerlist = getRelativePath('xiQuant50.csv')
		if strategy == 'xiQuantXXX-2014':
			file_tickerlist = getRelativePath('xiQuantXXX-2014.csv')
		if strategy == 'xiQuantXXX-2009':
			file_tickerlist = getRelativePath('xiQuantXXX-2009.csv')
		if strategy == 'xiQuantXXX-2009':
			file_tickerlist = getRelativePath('xiQuantXXX-2009.csv')
		if strategy == 'xiQuantXXX-2013-2014':
			file_tickerlist = getRelativePath('xiQuantXXX-2013-2014.csv')
		if strategy == 'xiQuantCBOE-2013-2014':
			file_tickerlist = getRelativePath('xiQuantCBOE-2013-2014.csv')
		with open(file_tickerlist, 'rU') as csvfile:
			reader = csv.DictReader(csvfile)
			for row in reader:
				tickerList.append(row['Stock Symbol'])
		### Make sure file is explicitly closed even though with statement it was causing problems...
		csvfile.close()

	return tickerList
	
def getMasterTickerList():

	file_tickerlist = getRelativePath('cboesymbol_master.csv')
	tickerList = []
	logger = getLogger()
	with open(file_tickerlist, 'rU') as csvfile:
		reader = csv.DictReader(csvfile)
		for row in reader:
			#logger.info(row['Stock Symbol'])
			tickerList.append(row['Stock Symbol'])

	return tickerList

def getRedisEffectiveDates(startdate, enddate):
	return  (startdate - datetime.timedelta(days=1)), (enddate + datetime.timedelta(days=1))
    


def getLogger(name='default.log'):

	if Log == None:
		print ("Initializing logger....")
		logger = logging.getLogger("xiQuant")
		logger.setLevel(logging.INFO)
		module_dir = os.path.dirname(__file__)
		file_BB_Spread = os.path.join(module_dir, name)
		handler = logging.handlers.RotatingFileHandler(
	             file_BB_Spread, maxBytes=1024 * 1024, backupCount=4)
		handler.setLevel(logging.INFO)
		formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
		handler.setFormatter(formatter)
		logger.addHandler(handler)

	    #### Also enable logging to console...
		console = logging.StreamHandler()
		console.setLevel(logging.INFO)
		console.setFormatter(formatter)
		logger.addHandler(console)

		return logger

Log = getLogger()

	