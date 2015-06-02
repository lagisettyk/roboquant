import sys
 
sys.path.append('/home/parallels/Code/heroku-envbased/roboquant')
print sys.path

#from algotrade import simple_strategy
#from xiQuant_strategies import xiQuantStrategyUtil

import datetime
from time import mktime
import xiQuantStrategyUtil

#import redis
#import urlparse
#import os
#from pyalgotrade.feed import memfeed
#from pyalgotrade.dataseries.bards import BarDataSeries
#from pyalgotrade.bar import BasicBar, Frequency
#from pyalgotrade.barfeed import membf


import dateutil.parser
yourdate = dateutil.parser.parse('2012-01-01T08:00:00.000Z')
yourdate2 = dateutil.parser.parse('2014-12-31T08:00:00.000Z')

print yourdate, yourdate2

results = xiQuantStrategyUtil.run_strategy_redis(20, "NFLX", 100000, yourdate, yourdate2)
#print results.getPortfolioResult()
print results.getSeries("middle")
print results.getSeries("upper")
print results.getSeries("lower")
print results.getAdjCloseSeries("NFLX")
#print results.getInstrumentDetails()
#print results.getTradeDetails()
#print results.getCumulativeReturns()


