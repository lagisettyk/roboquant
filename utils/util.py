### Redis related Utility functions...
import redis
import os
import urlparse
import logging
import logging.handlers
import csv
import dateutil.parser

def getCurrentDir():
	return os.path.dirname(__file__)  # get current directory

def getRelativePath(filename):
	return os.path.join(getCurrentDir(), filename)  # get current directory

def getTickerList():

	#tickerList = ['AAPL', 'NFLX', 'GOOGL', 'FDX']
	tickerList = ['AAPL', 'AMZN', 'FDX', 'MA', 'NFLX', 'OCR', 'GD','NXPI', 'CVS', 'UNP', 'GILD', 'VRX', 'ACT', 'XLF','GOOGL', 'CF', 'URI', 'CP', 'WHR', 'IWM', 'UNH', 'VIAB', 'FLT', \
	 'ODFL', 'ALL', 'V']

	'''
	file_tickerlist = getRelativePath('cboesymbol.csv')
	tickerList = []
	logger = getLogger()
	with open(file_tickerlist, 'rU') as csvfile:
		reader = csv.DictReader(csvfile)
		for row in reader:
			logger.info(row['Stock Symbol'])
			tickerList.append(row['Stock Symbol'])
	'''
	return tickerList


def get_redis_conn(redis_url=os.getenv('REDISCLOUD_URL', 'redis://localhost:6379')):
	url = urlparse.urlparse(redis_url)
	#print "$$$URL: ", url
	return redis.StrictRedis(host=url.hostname, port=url.port, password=url.password)

def getLogger(name='default.log'):
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



	