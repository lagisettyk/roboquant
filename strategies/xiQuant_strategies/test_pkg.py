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
#stdate = dateutil.parser.parse('2005-06-15')
stdate = dateutil.parser.parse('2005-06-30T08:00:00.000Z')
enddate = dateutil.parser.parse('2014-12-31T08:00:00.000Z')
#enddate = dateutil.parser.parse('2014-12-31')
#datetime.datetime.combine(datetime.date(2011, 01, 01), datetime.time(10, 23)) ### example for combining date and time...


#redis_build_CSV_EOD("FDX", stdate, enddate)

print stdate, enddate

#dateTime = dateutil.parser.parse('2011-04-20T08:00:00.000Z')
#print "$$$Calender: ", xiQuantStrategyUtil.isEarnings("AAPL", dateTime, False)




#results_sma_3days = xiQuantStrategyUtil.redis_build_sma_3days("NFLX", stdate, enddate)
#print results_sma_3days

#results_moneyflow = xiQuantStrategyUtil.redis_build_moneyflow_percent("NFLX", stdate, enddate)
#print results_moneyflow

#results_moneyflow_percent = xiQuantStrategyUtil.redis_build_moneyflow_percent("NFLX", stdate, enddate)
#print results_moneyflow_percent

#results_5Day_SMA_Volume = xiQuantStrategyUtil.redis_build_volume_sma_ndays("NFLX", 5, stdate, enddate)
#print results_5Day_SMA_Volume

#results_momentum_list = xiQuantStrategyUtil.tickersRankByMoneyFlowPercent(enddate)
#print results_momentum_list

#results = xiQuantStrategyUtil.run_strategy_TN(20, "NFLX", 100000, stdate, enddate)
#results = xiQuantStrategyUtil.run_strategy_redis(20, "MA", 100000, stdate, enddate)
#print results.getPortfolioResult()
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

port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrder.csv')
print port_results.getPortfolioResult()
#print port_results.getCumulativeReturns() #### to do how to populate more than 3 years


