import sys
 
sys.path.append('/home/parallels/Code/heroku-envbased/roboquant')
#print sys.path
import datetime
from time import mktime
import xiQuantStrategyUtil


import dateutil.parser
stdate = dateutil.parser.parse('2012-01-01T08:00:00.000Z')
#stdate = dateutil.parser.parse('2014-12-23T08:00:00.000Z')
enddate = dateutil.parser.parse('2014-12-31T08:00:00.000Z')

print stdate, enddate

#results_sma_3days = xiQuantStrategyUtil.redis_build_sma_3days("NFLX", stdate, enddate)
#print results_sma_3days

#results_moneyflow = xiQuantStrategyUtil.redis_build_moneyflow("NFLX", stdate, enddate)
#print results_moneyflow

#results_moneyflow_percent = xiQuantStrategyUtil.redis_build_moneyflow_percent("NFLX", stdate, enddate)
#print results_moneyflow_percent

#results_momentum_list = xiQuantStrategyUtil.tickersRankByMoneyFlowPercent(enddate)
#print results_momentum_list

results = xiQuantStrategyUtil.run_strategy_redis(20, "NFLX", 100000, stdate, enddate)
print results.getPortfolioResult()
#print results.getSeries("middle")
#print results.getSeries("upper")
#print results.getSeries("lower")
#print results.getAdjCloseSeries("NFLX")
#print results.getInstrumentDetails()
#print results.getTradeDetails()
#print results.getCumulativeReturns()
#print results.getSeries("macd")


