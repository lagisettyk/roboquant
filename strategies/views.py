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
	#from algotrade import simple_strategy
	#from xiQuant_strategies import xiQuantStrategyUtil
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
	while (job.result is None):
		time.sleep(1)

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
		"cashflow_3days": xiQuantStrategyUtil.redis_build_moneyflow(ticker, start_date, end_date)
		}
	
    ### This is important to note json.dumps() convert python data structure to JSON form
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
