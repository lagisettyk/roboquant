import sys
 
sys.path.append('/home/parallels/Code/heroku-envbased/roboquant')
#print sys.path
import datetime
from time import mktime
import xiQuantStrategyUtil
from pyalgotrade.technical import ma
from utils import util


def redis_build_CSV_EOD(ticker, stdate, enddate):
    import datetime
    from time import mktime
    from pyalgotrade.utils import dt
    from pyalgotrade.bar import BasicBar, Frequency
    import csv
    import collections

    seconds = mktime(stdate.timetuple())
    seconds2 = mktime(enddate.timetuple())

    data_dict = {}
    try:
        redisConn = util.get_redis_conn()
        ### added EOD as data source
        ticker_data = redisConn.zrangebyscore(ticker + ":EOD", int(seconds), int(seconds2), 0, -1, True)
        #ticker_data = redisConn.zrangebyscore(ticker + ":EOD_UnAdj", int(seconds), int(seconds2), 0, -1, True)
        data_dict = xiQuantStrategyUtil.redis_listoflists_to_dict(ticker_data)
        ordered_data_dict = collections.OrderedDict(sorted(data_dict.items(), reverse=False))
    except Exception,e:
        print str(e)
        pass

    bd = [] ##### initialize bar data.....
    for key in ordered_data_dict:
        dateTime = dt.timestamp_to_datetime(key).strftime('%m/%d/%Y')
        data = data_dict[key].split("|") ### split pipe delimted values
        dataList = []
        dataList.append(ticker)
        dataList.append(str(dateTime))
        dataList.append(float("{0:.2f}".format(float(data[0]))))
        dataList.append(float("{0:.2f}".format(float(data[1]))))
        dataList.append(float("{0:.2f}".format(float(data[2]))))
        dataList.append(float("{0:.2f}".format(float(data[3]))))
        dataList.append(float("{0:.2f}".format(float(data[4]))))
        bd.append(dataList)

    with open(ticker+'.csv', 'w') as fp:
    	a = csv.writer(fp, delimiter=',')
    	a.writerows(bd)


import dateutil.parser
stdate = dateutil.parser.parse('2009-01-01T08:00:00.000Z')
#stdate = dateutil.parser.parse('2014-12-23T08:00:00.000Z')
enddate = dateutil.parser.parse('2015-06-05T08:00:00.000Z')

#redis_build_CSV_EOD("FDX", stdate, enddate)

print stdate, enddate




#results_sma_3days = xiQuantStrategyUtil.redis_build_sma_3days("NFLX", stdate, enddate)
#print results_sma_3days

#results_moneyflow = xiQuantStrategyUtil.redis_build_moneyflow("NFLX", stdate, enddate)
#print results_moneyflow

#results_moneyflow_percent = xiQuantStrategyUtil.redis_build_moneyflow_percent("NFLX", stdate, enddate)
#print results_moneyflow_percent

#results_momentum_list = xiQuantStrategyUtil.tickersRankByMoneyFlowPercent(enddate)
#print results_momentum_list

results = xiQuantStrategyUtil.run_strategy_TN(20, "AAPL", 100000, stdate, enddate)
print results.getPortfolioResult()
#print results.getMACD()
#print results.getADX()
#print results.getDMIPlus()
#print results.getDMIMinus()
#print results.getSeries("middle")
#print results.getSeries("upper")
#print results.getSeries("lower")
#print results.getAdjCloseSeries("NFLX")
#print results.getAdjVolSeries("NFLX")
#print results.getInstrumentDetails()
#print results.getTradeDetails()
#print results.getCumulativeReturns()
#print results.getSeries("EMA Signal")


