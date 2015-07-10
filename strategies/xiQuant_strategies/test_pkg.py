import sys
 
sys.path.append('/home/parallels/Code/heroku-envbased/roboquant')
#print sys.path
import datetime
from time import mktime
import xiQuantStrategyUtil
from pyalgotrade.technical import ma
from utils import util
import csv
import operator


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
#stdate = dateutil.parser.parse('2005-01-01')
stdate = dateutil.parser.parse('2005-06-30T08:00:00.000Z')
enddate = dateutil.parser.parse('2014-12-31T08:00:00.000Z')
#enddate = dateutil.parser.parse(' 2011-06-29')

#datetime.datetime.combine(datetime.date(2011, 01, 01), datetime.time(10, 23)) ### example for combining date and time...


#redis_build_CSV_EOD("FDX", stdate, enddate)

print stdate, enddate

#print int(mktime(enddate.timetuple()))*1000

#util.Log.info("Got logger handle...")
#util.Log.info("Testing...")
#util.Log.info("Testing...")
#util.Log.info("Testing...")

#dateTime = dateutil.parser.parse('2011-04-20T08:00:00.000Z')
#print "$$$Calender: ", xiQuantStrategyUtil.isEarnings("AAPL", dateTime, False)




#results_sma_3days = xiQuantStrategyUtil.redis_build_sma_3days("MA", stdate, enddate)
#print results_sma_3days

#results_moneyflow = xiQuantStrategyUtil.redis_build_moneyflow("MA", stdate, enddate)
#print results_moneyflow

#results_cf_tn = xiQuantStrategyUtil.cashflow_timeseries_TN("MA", stdate, enddate)
#print results_cf_tn

#results_earnings_cal = xiQuantStrategyUtil.getEarningsCal("GOOGL")
#print results_earnings_cal

#results_moneyflow_percent = xiQuantStrategyUtil.redis_build_moneyflow_percent("NFLX", stdate, enddate)
#print results_moneyflow_percent

#results_5Day_SMA_Volume = xiQuantStrategyUtil.redis_build_volume_sma_ndays("NFLX", 5, stdate, enddate)
#print results_5Day_SMA_Volume

#results_momentum_list = xiQuantStrategyUtil.tickersRankByMoneyFlowPercent(enddate)
#print results_momentum_list

#results_momentum_list = xiQuantStrategyUtil.tickersRankByMoneyFlow(enddate)
#print results_momentum_list
#results = xiQuantStrategyUtil.run_strategy_redis(20, "GOOGL", 100000, stdate, enddate, filterCriteria=5000, indicators=False)
#print results

#results = xiQuantStrategyUtil.run_strategy_redis(20, "NFLX", 100000, stdate, enddate)
#results = xiQuantStrategyUtil.run_strategy_TN(20, "GOOGL", 100000, stdate, enddate)
#print results.getPortfolioResult()
#print results.getOrdersFilteredByMomentumRank(filterCriteria=3000)
#print results.getOrders()

dataRows = []
#tickerList = util.getTickerList('Abhi-26')
tickerList = ['GOOGL']
for ticker in tickerList:
    results = xiQuantStrategyUtil.run_strategy_redis(20, ticker, 100000, stdate, enddate, filterCriteria=20, indicators=False)
    #results = xiQuantStrategyUtil.run_strategy_redis(20, "GOOGL", 100000, stdate, enddate, filterCriteria=100, indicators=False)
    #results = xiQuantStrategyUtil.run_strategy_TN(20, "NFLX", 100000, stdate, enddate, filterCriteria=10000, indicators=False)
    #results = xiQuantStrategyUtil.run_strategy_TN(20, ticker, 100000, stdate, enddate)
    print results
    orders = results
    #orders = results.getOrdersFilteredByMomentumRank(filterCriteria=1000)
    #orders = results.getOrdersFilteredByRules()
    for key, value in orders.iteritems():
        row = []
        row.append(key)
        row.append(value[0][0])
        row.append(value[0][1])
        row.append(value[0][2])
        row.append(value[0][3])
        dataRows.append(row)

print dataRows
dataRows.sort(key = operator.itemgetter(0, 4))

fake_csv = util.make_fake_csv(dataRows)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, fake_csv, datasource='TN')
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, fake_csv, datasource='REDIS')
#print port_results.getPortfolioResult()
#print port_results.getCumulativeReturns() #### to do how to populate more than 3 years


#### read fake_csv as csv file....
reader = csv.DictReader(fake_csv, fieldnames=["timeSinceEpoch", "symbol", "action", "stopPrice", "rank"])
with open('MasterOrders.csv', 'w') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=["timeSinceEpoch", "symbol", "action", "stopPrice", "rank"])
    writer.writeheader()
    for row in reader:
        print row
        writer.writerow(row)


fake_csv.seek(0)
port_results = xiQuantStrategyUtil.run_master_strategy(100000, fake_csv, datasource='REDIS')
print port_results.getPortfolioResult()



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




