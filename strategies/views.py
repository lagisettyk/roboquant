from django.shortcuts import render
from django.http import HttpResponse



# Create your views here.
def index(request):
	context_dict = {}
	response = render(request, 'strategies/index.html', context_dict)
	return response	

def about(request):
	context_dict = {'aboutmessage': "About xiQaunt under development"}
	return render(request, 'strategies/about.html', context_dict)

def display_hichart(request):
	print ">>>>> entered display_hichart"
	context_dict = {'hichart': "Simple-HiChart-Example"}
	return render(request, 'strategies/histock_example.html', context_dict)

def display_matplotlib(request):
	print ">>>>> entered display_matplotlib"
	context_dict = {'matplotlibmessage': "Simple-Matplotlib"}
	return render(request, 'strategies/Simple-Matplotlib.html', context_dict)

def display_backtest(request):
	print ">>>>> entered display_backtest"
	context_dict = {'backtestmessage': "display_backtest"}
	return render(request, 'strategies/backtest.html', context_dict)

def display_portfolio(request):
	print ">>>>> entered display_backtest"
	context_dict = {'backtestmessage': "display_portfolio"}
	return render(request, 'strategies/backtestPortfolio.html', context_dict)


def hichart_quandl(request):
	from Quandl import Quandl
	import json

	if request.method == 'GET':
		ticker = request.GET['Ticker']

	myAAPL_data  = Quandl.get("WIKI/"+ticker, returns="pandas", column="11", 
	  authtoken="L5A6rmU9FGvyss9F7Eym", trim_start='2005/01/01')
    
	data = json.loads(myAAPL_data.to_json()) # convert to JSON object...
	#### Below logic is quite imp as
	# this is transforming pandas dataframe to the High charts input structure
	data_list = list(sorted(data['Adj. Close'].items()))
	highcharts_data = []
	for x in range(len(data_list)):
		dl = list(data_list[x])
		dl[0] = int(dl[0])
		highcharts_data.append(dl)

    ### This is important to note json.dumps() convert python data structure to JSON form
	return HttpResponse(json.dumps(highcharts_data), content_type='application/json')

def highchart_dataformat(redisConn, sortedset):

	redisTS = redisConn.zrange(sortedset, 0, -1, False, True)
	hichart_data = []
	for x in range(len(redisTS)):
		hichart_data.append([int(redisTS[x][1]), float(redisTS[x][0])])
	return hichart_data


def hichart_redis(request):
	import redis
	import json
	import urlparse
	from django.conf import settings
	from utils import util

    # Intialize redis store.....
	redisConn = util.get_redis_conn(settings.REDIS_URL)
	if request.method == 'GET':
		ticker = request.GET['Ticker']
	
	highcharts_data = highchart_dataformat(redisConn, ticker+':Adj_Close')

    ### This is important to note json.dumps() convert python data structure to JSON form
	return HttpResponse(json.dumps(highcharts_data), content_type='application/json')
	


def backtest(request):
	import redis
	import json
	import urlparse
	from django.conf import settings
	from rq import Queue
	import time
	import dateutil.parser
	from utils import util
	from xiQuant_strategies import xiQuantStrategyUtil

    # Intialize redis store.....
	#url = urlparse.urlparse(settings.REDIS_URL)
	#print "$$$URL: ", url
	#redisConn = redis.StrictRedis(host=url.hostname, port=url.port, password=url.password)
	redisConn = util.get_redis_conn(settings.REDIS_URL)
	if request.method == 'GET':
		ticker = request.GET['Ticker']
		amount = request.GET['amount']
		stdate = request.GET['stdate']
		enddate = request.GET['enddate']
		strategy = request.GET['strategy']

    
	start_date = dateutil.parser.parse(stdate)
	end_date = dateutil.parser.parse(enddate)

	q = Queue(connection=redisConn)  # no args implies the default queue
	if strategy == 'BB_Spread_strategy':
		job = q.enqueue(xiQuantStrategyUtil.run_strategy_redis, 20, ticker, int(amount), start_date, end_date)
	else:
		job = q.enqueue(xiQuantStrategyUtil.run_strategy_TN, 20, ticker, int(amount), start_date, end_date)
	#job = q.enqueue(xiQuantStrategyUtil.run_strategy_redis, 20, ticker, int(amount), start_date, end_date)
	sleep = True
	while(sleep):
		time.sleep(1)
		if job.get_status() == 'failed' or job.get_status()=='finished':
			sleep = False

	results = {
		"seriesData":job.result.getPortfolioResult(),
		"flagData": job.result.getTradeDetails(),
		"upper": job.result.getSeries("upper"), 
		"middle": job.result.getSeries("middle"),
		"lower": job.result.getSeries("lower"),
		"price": job.result.getAdjCloseSeries(ticker),
		"volume": job.result.getAdjVolSeries(ticker),
		"macd": job.result.getMACD(),
		"adx": job.result.getADX(),
		"dmiplus": job.result.getDMIPlus(),
		"dmiminus": job.result.getDMIMinus(),
		"rsi": job.result.getSeries("RSI"),
		"emafast": job.result.getSeries("EMA Fast"),
		"emaslow": job.result.getSeries("EMA Slow"),
		"emasignal": job.result.getSeries("EMA Signal"),
		"cashflow_3days": xiQuantStrategyUtil.redis_build_moneyflow(ticker, start_date, end_date),
		"volsma5days": xiQuantStrategyUtil.redis_build_volume_sma_ndays(ticker, 5, start_date, end_date) ### 5days...
		}
	
    ### This is important to note json.dumps() convert python data structure to JSON form
	return HttpResponse(json.dumps(results), content_type='application/json')

def simulatepotfolio(redisURL, amount, strategy, startdate, enddate, filterRank):
	import redis
	import json
	import urlparse
	from django.conf import settings
	from rq import Queue
	import time
	import dateutil.parser
	from utils import util
	from xiQuant_strategies import xiQuantStrategyUtil
	

	tickerList = util.getTickerList(strategy)

	redisConn = util.get_redis_conn(redisURL)
	q = Queue(connection=redisConn, default_timeout=15000)  # no args implies the default queue

	jobList = []
	for ticker in tickerList:
		jobList.append(q.enqueue(xiQuantStrategyUtil.run_strategy_redis, 20, ticker, int(amount), startdate, enddate, filterRank, indicators=False, result_ttl=3000))
		#jobList.append(q.enqueue(xiQuantStrategyUtil.run_strategy_redis, 20, ticker, int(amount), startdate, enddate,  filterRank, indicators=False))

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

	########### Iterate master orders file.... #############
	dataRows = []
	for k in range(len(master_orders)):
		for key, value in master_orders[k].iteritems():
			row = []
			row.append(key)
			row.append(value[0][0])
			row.append(value[0][1])
			row.append(value[0][2])
			dataRows.append(row)

	fake_csv = util.make_fake_csv(dataRows)
	print  "Successfully created master_orders fake_csv file...."

	############### Run the master order for computing portfolio#########
	jobPortfolio = q.enqueue(xiQuantStrategyUtil.run_master_strategy,int(amount), fake_csv)

	sleep = True
	while(sleep):
		time.sleep(1)
		if jobPortfolio.get_status() == 'failed' or jobPortfolio.get_status()=='finished':
			sleep = False

	print  "Successfully simulated portfolio"

	return jobPortfolio.result


def backtestPortfolio(request):
	import redis
	import json
	import urlparse
	from django.conf import settings
	from rq import Queue
	from rq.job import Job
	import time
	import dateutil.parser
	from utils import util
	from xiQuant_strategies import xiQuantStrategyUtil
	#import shutil
	import csv

	if request.method == 'GET':
		#ticker = request.GET['Ticker']
		jobid = request.GET['jobid']
		amount = request.GET['amount']
		stdate = request.GET['stdate']
		enddate = request.GET['enddate']
		strategy = request.GET['strategy']
		filterRank = request.GET['rank']


	start_date = dateutil.parser.parse(stdate)
	end_date = dateutil.parser.parse(enddate)

	redisConn = util.get_redis_conn(settings.REDIS_URL)
	#redisConn = util.get_redis_conn_nopool(settings.REDIS_URL)
	
	if jobid == 'NEW':
		q = Queue(connection=redisConn, default_timeout=15000)  # no args implies the default queue
		#q = Queue(connection=redisConn)  # no args implies the default queue
		jobPortfolio = q.enqueue(simulatepotfolio, settings.REDIS_URL, int(amount), strategy, start_date, end_date, int(filterRank))

		print  "Successfully submitted portfolio simulation..."
		### Return just job id by kicking of redis job....
		results = {
		"jobstatus": jobPortfolio.id
		}
		### Return just job id....
		return HttpResponse(json.dumps(results), content_type='application/json')
	else:
		print "$$$$$$$$$$$ ################# polling request received...."
		jobPortfolio = Job.fetch(jobid, connection=redisConn)

		if jobPortfolio.get_status() == 'failed' or jobPortfolio.get_status()=='finished':
			results = {
			"jobstatus": "SUCCESS",
			"seriesData":jobPortfolio.result.getPortfolioResult(),
			"flagData": jobPortfolio.result.getTradeDetails(),
			"cumulativereturns": jobPortfolio.result.getCumulativeReturns()
			}
			### This is important to note json.dumps() convert python data structure to JSON form
			return HttpResponse(json.dumps(results), content_type='application/json')
		else:
			results = {
			"jobstatus": jobid
			}
			### Return just job id....
			return HttpResponse(json.dumps(results), content_type='application/json')


	
def simple(request):
	import random
	import datetime

	from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
	from matplotlib.figure import Figure
	from matplotlib.dates import DateFormatter

	fig=Figure()
	ax=fig.add_subplot(111)
	x=[]
	y=[]
	now=datetime.datetime.now()
	delta=datetime.timedelta(days=1)
	for i in range(10):
		x.append(now)
		now+=delta
		y.append(random.randint(0, 1000))
	ax.plot_date(x, y, '-')
	ax.xaxis.set_major_formatter(DateFormatter('%Y-%m-%d'))
	fig.autofmt_xdate()
	canvas = FigureCanvas(fig)
	response = HttpResponse(content_type='image/png')
	canvas.print_png(response)
	return response
