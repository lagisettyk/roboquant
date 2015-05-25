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

'''
#### Temporary purpose later need to move to models.....
def populate_redis_datastore(redisConn, tickerList, startdate):
	import Quandl
	import json

	for ticker in range(len(tickerList)):
		if redisConn.zcard(tickerList[ticker]+':Adj. Close') == 0:
			try:
				my_data  = Quandl.get(
					"WIKI/"+ tickerList[ticker], returns="pandas", 
					column="11", sort_order="asc", authtoken="L5A6rmU9FGvyss9F7Eym",  
					trim_start = startdate )
				if not my_data.empty:
					json_data = json.loads(my_data.to_json()) 
					json_data_list = list(sorted(json_data['Adj. Close'].items()))
					for x in range(len(json_data_list)):
						dl = list(json_data_list[x])
						### Store data in the sorted sets...
						redisConn.zadd(tickerList[ticker]+':Adj. Close', dl[0], dl[1])
					print redisConn.zrange(tickerList[ticker]+':Adj. Close', 0, -1)
			except Exception,e: 
				print str(e)
				pass

		print "populated time series: ", tickerList[ticker]+':Adj. Close'
		#sleep(0.20) # Sleep in between calls
'''

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

    # Intialize redis store.....
	url = urlparse.urlparse(settings.REDIS_URL)
	print "$$$URL: ", url
	redisConn = redis.StrictRedis(host=url.hostname, port=url.port, password=url.password)
	#redisConn = redis.Redis(host=url.hostname, port=url.port, password=url.password)

	####### This code needs to move to initialization of models sections...
	#tickerList = ["AAPL", "MSFT", "GS"]
	#populate_redis_datastore(redisConn, tickerList, "2005/01/01")
	###################################################################
     
	if request.method == 'GET':
		ticker = request.GET['Ticker']
	
	highcharts_data = highchart_dataformat(redisConn, ticker+':Adj. Close')

    ### This is important to note json.dumps() convert python data structure to JSON form
	return HttpResponse(json.dumps(highcharts_data), content_type='application/json')
	


def backtest(request):
	import redis
	import json
	import urlparse
	from django.conf import settings
	from rq import Queue
	from algotrade import simple_strategy
	import time
	import dateutil.parser

    # Intialize redis store.....
	url = urlparse.urlparse(settings.REDIS_URL)
	print "$$$URL: ", url
	redisConn = redis.StrictRedis(host=url.hostname, port=url.port, password=url.password)
	if request.method == 'GET':
		ticker = request.GET['Ticker']
		amount = request.GET['amount']
		stdate = request.GET['stdate']
		enddate = request.GET['enddate']

    
	start_date = dateutil.parser.parse(stdate)
	end_date = dateutil.parser.parse(enddate)

	print start_date, end_date

	q = Queue(connection=redisConn)  # no args implies the default queue
	job = q.enqueue(simple_strategy.run_strategy_redis, ticker, int(amount), start_date, end_date)
	while (job.result is None):
		time.sleep(1)
	'''
	flag_data = [{
                    'x' : 1336003200000,
                    'title' : 'H',
                    'text' : 'Euro Contained by Channel Resistance'
                }, {
                    'x' : 1355788800000,
                    'title' : 'G',
                    'text' : 'EURUSD: Bulls Clear Path to 1.50 Figure'
                }, {
                    'x' : 1361923200000,
                    'title' : 'F',
                    'text' : 'EURUSD: Rate Decision to End Standstill'
                }]


	results = {"seriesData":job.result, "flagData": flag_data }
	'''
	results = {"seriesData":job.result.getPortfolioResult(), "flagData": job.result.getTradeDetails() }
	
    ### This is important to note json.dumps() convert python data structure to JSON form
	#return HttpResponse(json.dumps(job.result), content_type='application/json')
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
