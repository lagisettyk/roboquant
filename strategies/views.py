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

def hichart_quandl(request):
	from Quandl import Quandl
	import json
	myAAPL_data  = Quandl.get("WIKI/AAPL", returns="pandas", column="11", 
	  authtoken="L5A6rmU9FGvyss9F7Eym", trim_start='2006/06/15', trim_end='2007/06/15')
    
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
	
