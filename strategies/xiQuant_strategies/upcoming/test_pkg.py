import sys
 
sys.path.append('/home/parallels/Code/heroku-envbased/roboquant')
#print sys.path
import datetime
#from time import calendar.timegm
import xiQuantStrategyUtil
from pyalgotrade.technical import ma
from utils import util
import csv
import operator
import calendar
import time
import os

#import 

def redis_build_CSV_EOD(ticker, stdate, enddate):
    import datetime
    from pyalgotrade.utils import dt
    from pyalgotrade.bar import BasicBar, Frequency
    import csv
    import collections

    seconds = calendar.timegm(stdate.timetuple())
    seconds2 = calendar.timegm(enddate.timetuple())

    data_dict = {}
    ordered_data_dict = None
    try:
        redisConn = util.get_redis_conn()
        ### added EOD as data source
        ticker_data = redisConn.zrangebyscore(ticker + ":EODRAW", int(seconds), int(seconds2), 0, -1, True)
        data_dict = xiQuantStrategyUtil.redis_listoflists_to_dict(ticker_data)
        ordered_data_dict = collections.OrderedDict(sorted(data_dict.items(), reverse=False))
    except Exception,e:
        print str(e)
        pass

    bd = [] ##### initialize bar data.....
    if ordered_data_dict is not None:
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
            dataList.append(float("{0:.2f}".format(float(data[5]))))
            dataList.append(float("{0:.2f}".format(float(data[6]))))
            dataList.append(float("{0:.2f}".format(float(data[7]))))
            bd.append(dataList)

        with open(ticker+'_EODRAW.csv', 'w') as fp:
            writer = csv.writer(fp, delimiter=',')
            header = ["Ticker", "Date", "Open", "High", "Low", "Close", "Volume", "AdjClose", "Dividend", "Split"]
            writer.writerow(header)
            writer.writerows(bd)


def periodAnalysis(runName, fileName, stdate, enddate, slidingRange, cutOff):

    analysisResults = []
    slidingWindow = 30
    analysisStartDate = stdate
    while analysisStartDate < enddate:
        analysisEndDate = analysisStartDate + datetime.timedelta(days=slidingRange)
        if analysisEndDate > enddate:
            analysisEndDate = enddate
        #print "++++++++++++++======= date range: ", analysisStartDate, analysisEndDate
        port_results = xiQuantStrategyUtil.run_master_strategy(100000, fileName, analysisStartDate, analysisEndDate, filterAction='both', rank=cutOff)
        src = os.path.join(os.path.dirname(__file__), 'results.csv')
        long_trades = 0.0
        short_trades = 0.0
        long_winning = 0.0
        short_winning = 0.0
        total_trades = 0.0
        total_winning = 0.0
        with open(src, 'rU') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['Trade-Type'] == 'LONG':
                    long_trades += 1.0
                    if float(row['Actual-PorL']) > 0.0:
                        long_winning +=1.0
                elif row['Trade-Type'] == 'SHORT':
                    short_trades += 1.0
                    if float(row['Actual-PorL']) > 0.0:
                        short_winning +=1

            analysisRow = []
            total_trades = long_trades + short_trades
            total_winning = long_winning + short_winning
            #print "####$$$$$$$$$$$$$$$$$$$$$$++++++==========: ", total_trades, total_winning, long_trades, short_trades
            dt1 = analysisStartDate.strftime('%m/%d/%Y')
            dt2 = analysisEndDate.strftime('%m/%d/%Y')
            analysisRow.append(str(dt1)+'--'+str(dt2))
            analysisRow.append(total_trades)
            analysisRow.append(total_winning)
            if total_trades !=0.0:
                analysisRow.append((total_winning/total_trades) * 100.0)
            analysisRow.append(long_trades)
            analysisRow.append(long_winning)
            if long_trades != 0.0:
                analysisRow.append((long_winning/long_trades) * 100.0)
            analysisRow.append(short_trades)
            analysisRow.append(short_winning)
            if short_trades != 0.0:
                analysisRow.append((short_winning/short_trades) * 100.0)
            analysisResults.append(analysisRow)
            
        analysisStartDate = analysisStartDate + datetime.timedelta(days=slidingWindow) ### end of while loop...

    with open(runName + '__rank-'+ str(cutOff)+'__' + str(slidingRange) + '__' + 'period_analysis.csv', 'w') as fp:
        writer = csv.writer(fp, delimiter=',')
        header = ["Period", "# of trades", "winning trades", "winning percent", "# of long trades", "long winning trades", "long winning percent", "# of short trades", "short winning trades", "short winning percent"]
        writer.writerow(header)
        writer.writerows(analysisResults)

    print "Successfully processed analyzing results..."


import dateutil.parser
#stdate = dateutil.parser.parse('2007-06-30')
stdate = dateutil.parser.parse('2005-06-30')
#stdate = dateutil.parser.parse('2015-08-01')
#stdate = dateutil.parser.parse('2010-01-01')
enddate = dateutil.parser.parse('2014-12-30')
#enddate = dateutil.parser.parse('2014-12-31')
#date1 = dateutil.parser.parse('2014-10-28T08:00:00.000Z')
#date2 = dateutil.parser.parse('2014-11-10T08:00:00.000Z')
specdate1 = dateutil.parser.parse(' 2014-04-02')
specdate3 = dateutil.parser.parse(' 2014-04-03')
specdate2 = dateutil.parser.parse(' 2014-04-04')

#periodAnalysis('results-combined-SEP12-2015','MasterOrders-COMBINED-SEP12-2015.csv', stdate, enddate, 360, 20)

#datetime.datetime.combine(datetime.date(2011, 01, 01), datetime.time(10, 23)) ### example for combining date and time...
#timestamp = time.mktime(specdate.timetuple())

#print calendar.timegm(specdate1.timetuple()), calendar.timegm(specdate2.timetuple()), calendar.timegm(specdate3.timetuple())

'''
#tickerList = util.getTickerList('SP-500')
tickerList = ['SPY', 'QQQ', 'WHR', 'IWM']
for ticker in tickerList:
    redis_build_CSV_EOD(ticker, stdate, enddate)
    print "Successfuly exported EODRAW data: ", ticker
'''


#print stdate, enddate

#print int(calendar.timegm(enddate.timetuple()))*1000

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

#results_cf_tn = xiQuantStrategyUtil.cashflow_timeseries_percentChange("MA", stdate, enddate)
#print results_cf_tn

#results_earnings_cal = xiQuantStrategyUtil.getEarningsCal("GOOGL")
#print results_earnings_cal



#results_5Day_SMA_Volume = xiQuantStrategyUtil.redis_build_volume_sma_ndays("NFLX", 5, stdate, enddate)
#print results_5Day_SMA_Volume

#results_momentum_list = xiQuantStrategyUtil.tickersRankByMoneyFlowPercent(enddate)
#print results_momentum_list

'''
results_momentum_list, results_CFCount = xiQuantStrategyUtil.topNMomentumTickerList(stdate, enddate, 100)
print len(results_momentum_list.keys())
print results_CFCount
with open('tickersRankByCashFlow.csv', 'w') as fp:
    writer = csv.writer(fp, delimiter=',')
    writer.writerows(results_CFCount) 
'''

#results_moneyflow_percent = xiQuantStrategyUtil.cashflow_timeseries_percentChange("AAPL", stdate, enddate)
#print results_moneyflow_percent




#results = xiQuantStrategyUtil.run_strategy_redis(20, "GOOGL", 100000, stdate, enddate, filterCriteria=10000, indicators=True)
#print results.getSeries("middle")
#print results.getSeries("upper")
#print results.getSeries("lower")
#print results.getSeries("RSI")
#print results.getSeries("EMA Fast")
#print results.getMACD()
#print results.getADX()
#print results

#print results.getPortfolioResult()
#print results.getOrdersFilteredByMomentumRank(filterCriteria=3000)
#print results.getOrders()
#print results.getMACD()
#print results.getADX()
#print results.getAdjCloseSeries("SPY_adjusted")
#print results.getSeries("middle")
#print results.getSeries("upper")
#print results.getSeries("lower")


'''
feed = xiQuantStrategyUtil.redis_build_feed_EOD_RAW("AAPL", stdate, enddate)
bars = feed.getBarSeries("AAPL")
bars = [bar for bar in bars if date1.replace(tzinfo=None) <= bar.getDateTime() <= date2.replace(tzinfo=None)]
bars.sort(key=lambda bar: bar.getDateTime(), reverse=True)
for bar in bars:
    print bar.getDividend(), bar.getSplit(), bar.getOpen(), bar.getHigh(), bar.getVolume(), bar.getClose(), bar.getDateTime()

print "++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"

k = 0
splitdataList = []
dividendList = []
for bar in bars:
    splitdata = bar.getSplit()
    dividend = bar.getDividend()
    if splitdata != 1.0:
        splitdataList.append(bar.getSplit())
    if dividend != 0.0:
        adjFactor = (bar.getClose() + bar.getDividend()) / bar.getClose()
        dividendList.append(adjFactor)
    #### Special case.... end date / analysis date nothing to do..
    if (k==0):
        #bar = BasicBar(bar.getDateTime(), bar.getOpen() , bar.getHigh(), bar.getLow(), bar.getClose(), bar.getVolume(), bar.getClose(), Frequency.DAY)
        #bars.append(bar)
        print bar.getOpen(), bar.getHigh(), bar.getVolume(), bar.getClose(), bar.getDateTime()
    else:
        #### Adjust OHLC & Volume data for split adjustments and dividend adjustments
        Open = bar.getOpen()
        High = bar.getHigh()
        Low  = bar.getLow()
        Close = bar.getClose()
        Volume = bar.getVolume()
        ### adjust data for splits
        for split in splitdataList:
            Open = Open / split
            High = High / split
            Low  = Low / split
            Close = Close /split
            Volume = Volume * split

        ### adjust data for dividends
        for adjFactor in dividendList:
            Open = Open / adjFactor
            High = High / adjFactor
            Low  = Low / adjFactor
            Close = Close / adjFactor
            Volume = Volume * adjFactor

        #bar = BasicBar(bar.getDateTime(),  Open , High, Low, Close, Volume, Close, Frequency.DAY)
        #bars.append(bar)
        print Open, High, Volume, Close, bar.getDateTime()
    k +=1
'''

'''
dataRows = []
#tickerList = util.getTickerList('Abhi-26')
tickerList = ['AGN']
for ticker in tickerList:
    results = xiQuantStrategyUtil.run_strategy_redis(20, ticker, 100000, stdate, enddate, filterCriteria=10, indicators=False)
    #results = xiQuantStrategyUtil.run_strategy_redis(20, "GOOGL", 100000, stdate, enddate, filterCriteria=100, indicators=False)
    #results = xiQuantStrategyUtil.run_strategy_TN(20, ticker, 100000, stdate, enddate, filterCriteria=10000, indicators=False)
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
    #writer.writeheader()
    for row in reader:
        row["stopPrice"] = round(float(row["stopPrice"]),2)
        writer.writerow(row)


fake_csv.seek(0)
port_results = xiQuantStrategyUtil.run_master_strategy(100000, fake_csv, stdate, enddate)
print port_results.getPortfolioResult()
'''

'''
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
'''

#results = xiQuantStrategyUtil.run_strategy_redis(20, 'AAPL', 100000, stdate, enddate, filterCriteria=10000, indicators=False)
#print results

#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_SP-500-BASELINE.csv', stdate, enddate, filterAction='both', rank=1)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_SP-500-recent.csv', stdate, enddate, filterAction='both', rank=5)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Short_SP-500-recent.csv', stdate, enddate, filterAction='both', rank=100)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_CBOE-ALL-BASELINE.csv', stdate, enddate, filterAction='both', rank=10000)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Long_SP-500-recent.csv', stdate, enddate, filterAction='both', rank=50)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_SP-500_Final.csv', stdate, enddate, filterAction='both', rank=10000)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_SP-500_Modified.csv', stdate, enddate, filterAction='both', rank=20)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_SP-500_Aug6-2015.csv', stdate, enddate, filterAction='both', rank=20)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_Asif_SP-500.csv', stdate, enddate, filterAction='both', rank=10000)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_Latest_SP-500.csv', stdate, enddate, filterAction='both', rank=100)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_CFA_SP-500.csv', stdate, enddate, filterAction='both', rank=20)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_Mod_SP-500.csv', stdate, enddate, filterAction='both', rank=20)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_RSI-CF-SP-500.csv', stdate, enddate, filterAction='both', rank=20)

#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_SP-100-KIRAN.csv', stdate, enddate, filterAction='both', rank=45)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_SP-100_Final.csv', stdate, enddate, filterAction='both', rank=20)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_Latest_SP-100.csv', stdate, enddate, filterAction='both', rank=10000)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_RSILEVEL_SP-100.csv', stdate, enddate, filterAction='both', rank=50)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_CFA_SP-100.csv', stdate, enddate, filterAction='both', rank=250)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_Short-CF-SP-100.csv', stdate, enddate, filterAction='both', rank=10000)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_RSI-CF-SP-100.csv', stdate, enddate, filterAction='both', rank=10000)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_SP-100.csv', stdate, enddate, filterAction='both', rank=10000)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_Mod_SP-100.csv', stdate, enddate, filterAction='both', rank=20)

#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_Abhi-26-BASELINE_INCLUDE3CHANGES.csv', stdate, enddate, filterAction='both', rank=5)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_Abhi-26-BB2-0-BASELINE.csv', stdate, enddate, filterAction='both', rank=10000)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Short_Abhi-26-BB1-5-BASELINE-1.csv', stdate, enddate, filterAction='both', rank=10000)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_Abhi-26-BB1-5-BASELINE.csv', stdate, enddate, filterAction='both', rank=20)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_Abhi-26-recent.csv', stdate, enddate, filterAction='both', rank=50)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Long_Abhi-26-BB1-5-BASELINE.csv', stdate, enddate, filterAction='both', rank=10000)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_Abhi-26-BASELINE_PLUS_Wick_Rel_To_Candle.csv', stdate, enddate, filterAction='both', rank=10000)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_Abhi-26-BASELINE_PLUS_Candle_Len_Check.csv', stdate, enddate, filterAction='both', rank=10000)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_Abhi-26-BASELINE_PLUS_MINUS_MFI.csv', stdate, enddate, filterAction='both', rank=10000)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_Abhi-26-BASELINE_PLUS_AVG.csv', stdate, enddate, filterAction='both', rank=10000)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_Abhi-26-BASELINE_PLUS_Price_Jump.csv', stdate, enddate, filterAction='both', rank=10000)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_Abhi-26-BASELINE_PLUS_Resistance_Or_Support.csv', stdate, enddate, filterAction='both', rank=10000)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_Abhi-26-BASELINE_PLUS_CF_CHECK.csv', stdate, enddate, filterAction='both', rank=50)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_Abhi-26_Volume.csv', stdate, enddate, filterAction='both', rank=10000)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_Abhi-26_Price_Jump.csv', stdate, enddate, filterAction='both', rank=10000)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_Abhi-26_WICK_REL_LEN_CUTOFF_FOR_TRADING.csv', stdate, enddate, filterAction='both', rank=10000)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_Abhi-26_NoIndicators.csv', stdate, enddate, filterAction='both', rank=10000)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_Abhi-26_Modified_Aug14-2015.csv', stdate, enddate, filterAction='both', rank=10000)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_Abhi-26_Aug14-2015.csv', stdate, enddate, filterAction='both', rank=10000)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_Abhi-26_modified_Aug13-2015.csv', stdate, enddate, filterAction='both', rank=100)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_Abhi-26_Aug13-2015.csv', stdate, enddate, filterAction='both', rank=10000)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_Abhi-26_Final2.csv', stdate, enddate, filterAction='both', rank=10000)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_Abhi-26_Final.csv', stdate, enddate, filterAction='both', rank=10000)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_Abhi-26_Modified_Aug6-2015.csv', stdate, enddate, filterAction='both', rank=50)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_Abhi-26_Aug6-2015.csv', stdate, enddate, filterAction='both', rank=100)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_Asif_Abhi-26.csv', stdate, enddate, filterAction='both', rank=10000)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_Latest_Abhi-26.csv', stdate, enddate, filterAction='both', rank=10000)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_RSILEVEL_Abhi-26.csv', stdate, enddate, filterAction='both', rank=10000)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_STRICT_Abhi-26.csv', stdate, enddate, filterAction='both', rank=100)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_CFA_Abhi-26.csv', stdate, enddate, filterAction='both', rank=100)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_Abhi-26.csv', stdate, enddate, filterAction='both', rank=100)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_Short-CF_Abhi-26.csv', stdate, enddate, filterAction='both', rank=50)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_RSI-CF-Abhi-26.csv', stdate, enddate, filterAction='both', rank=50)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_Mod_Abhi-26.csv', stdate, enddate, filterAction='both', rank=50)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_EMABreachMTM_Abhi-26.csv', stdate, enddate, filterAction='both', rank=10000)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_BBSMAxOver_Abhi-26.csv', stdate, enddate, filterAction='both', rank=10000)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_RSI_Abhi-26.csv', stdate, enddate, filterAction='both', rank=50)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_RSI75_Abhi-26.csv', stdate, enddate, filterAction='both', rank=50)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_RSIU75-L30-Abhi-26.csv', stdate, enddate, filterAction='both', rank=10000)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_RSIU75-L30-SP-500.csv', stdate, enddate, filterAction='sell', rank=10000)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_SP-500.csv', stdate, enddate, filterAction='both', rank=10000)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_CBOE-r1000.csv', stdate, enddate, filterAction='sell', rank=20)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_SP500_CBOE1000.csv', stdate, enddate, filterAction='both', rank=10000)
#print port_results.getPortfolioResult()
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_BBSMAXOverMTM_Both_Abhi-26-BASELINE.csv', stdate, enddate, filterAction='both', rank=10000)

#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_BBSMAXOverMTM_Both_Abhi-26-SMA20-PD1.csv', stdate, enddate, filterAction='both', rank=50)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_BBSMAXOverMTM_Both_Abhi-26-SMA100-NOPSTL.csv', stdate, enddate, filterAction='both', rank=10000)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_BBSMAXOverMTM_Both_Abhi-26-SMA200-NOPSTL.csv', stdate, enddate, filterAction='both', rank=10000)

#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_BBSMAXOverMTM_Both_Abhi-26-SMA20-PSTL.csv', stdate, enddate, filterAction='both', rank=5)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_BBSMAXOverMTM_Both_Abhi-26-SMA100-PSTL.csv', stdate, enddate, filterAction='both', rank=5)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_BBSMAXOverMTM_Both_Abhi-26-SMA200-PSTL.csv', stdate, enddate, filterAction='both', rank=5)

#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_EMABreachMTM_Both_Abhi-26-EMA10-NOPSTL.csv', stdate, enddate, filterAction='both', rank=20)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_EMABreachMTM_Both_Abhi-26-EMA20-NOPSTL.csv', stdate, enddate, filterAction='both', rank=5)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_EMABreachMTM_Both_Abhi-26-EMA50-NOPSTL.csv', stdate, enddate, filterAction='both', rank=5)

#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_EMABreachMTM_Both_Abhi-26-EMA10-PSTL.csv', stdate, enddate, filterAction='both', rank=5)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_EMABreachMTM_Both_Abhi-26-EMA20-PSTL.csv', stdate, enddate, filterAction='both', rank=5)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_EMABreachMTM_Both_Abhi-26-EMA50-PSTL.csv', stdate, enddate, filterAction='both', rank=5)

#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders-COMBINED-SEP12-2015.csv', stdate, enddate, filterAction='both', rank=5)


#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_BBSMAXOverMTM_Both_Abhi-26-SMA20-BASELINE.csv', stdate, enddate, filterAction='both', rank=1)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_EMABreachMTM_Both_Abhi-26-EMA10-BASELINE.csv', stdate, enddate, filterAction='both', rank=10000)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_Abhi-26-BB2-0-BASELINE.csv', stdate, enddate, filterAction='both', rank=1)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_Abhi-26-BB1-5-BASELINE.csv', stdate, enddate, filterAction='both', rank=1)
#port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'MasterOrders_Both_Abhi-26-COMBINED-NOPSTL.csv', stdate, enddate, filterAction='both', rank=5)
#print port_results.getStrategiesOutput()

#upper, middle, lower, adjOHLCSeries = xiQuantStrategyUtil.computeIndicators('AAPL', 'BBands', stdate, enddate)
#print upper, adjOHLCSeries

#sma, adjOHLCSeries = xiQuantStrategyUtil.computeIndicators('AAPL', 'SMA-20', stdate, enddate)
#print sma, adjOHLCSeries

#ema, adjOHLCSeries = xiQuantStrategyUtil.computeIndicators('AAPL', 'EMA-10', stdate, enddate)
#print ema, adjOHLCSeries

'''
#tickerList = util.getTickerList('Abhi-26')
#tickerList = ['AAPL', 'GOOGL', 'MA', 'FDX', 'NFLX', 'AMZN']
#tickerList = ['GILD', 'GD', 'UNH', 'CVS', 'URI']
tickerList = ['AAPL']
for ticker in tickerList:
    try:
        results = xiQuantStrategyUtil.run_strategy_redis(20, ticker, 100000, stdate, enddate)
        #print results
        port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'orders.csv', stdate, enddate, filterAction='both', rank=10000)
        src = os.path.join(os.path.dirname(__file__), 'results.csv')
        dest = os.path.join(os.path.dirname(__file__), 'results_modified'+ticker+".csv")
        os.rename(src, dest)
    except Exception,e:
        print str(e)
        pass
'''

'''
#tickerList = util.getTickerList('Abhi-26')
#tickerList = ['AAPL', 'GOOGL', 'MA', 'FDX', 'NFLX', 'AMZN']
#tickerList = ['GILD', 'GD', 'UNH', 'CVS', 'URI']
tickerList = ['AAPL']
for ticker in tickerList:
    try:
        results = xiQuantStrategyUtil.run_strategy_BBSMAXOverMTM(20, ticker, 100000, stdate, enddate)
        port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'orders.csv', stdate, enddate, filterAction='both', rank=10000)
        src = os.path.join(os.path.dirname(__file__), 'results.csv')
        dest = os.path.join(os.path.dirname(__file__), 'results_BBSMAXOverMTM_'+ticker+".csv")
        os.rename(src, dest)
    except Exception,e:
        print str(e)
        pass
'''

'''
#tickerList = util.getTickerList('Abhi-26')
#tickerList = ['AAPL', 'GOOGL', 'MA', 'FDX', 'NFLX', 'AMZN']
#tickerList = ['GILD', 'GD', 'UNH', 'CVS', 'URI']
tickerList = ['AAPL']
for ticker in tickerList:
    try:
        results = xiQuantStrategyUtil.run_strategy_EMABreachMTM(20, ticker, 100000, stdate, enddate)
        port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'orders.csv', stdate, enddate, filterAction='both', rank=10000)
        src = os.path.join(os.path.dirname(__file__), 'results.csv')
        dest = os.path.join(os.path.dirname(__file__), 'results_EMABreachMTM_'+ticker+".csv")
        os.rename(src, dest)
    except Exception,e:
        print str(e)
        pass
'''

#tickerList = util.getTickerList('Abhi-26')
#tickerList = ['AAPL', 'GOOGL', 'MA', 'FDX', 'NFLX', 'AMZN']
#tickerList = ['GILD', 'GD', 'UNH', 'CVS', 'URI']
tickerList = ['WHR']
for ticker in tickerList:
    try:
        results = xiQuantStrategyUtil.run_strategy_EMATrend(20, ticker, 100000, stdate, enddate)
        #print results
        port_results = xiQuantStrategyUtil.run_master_strategy(100000, 'orders.csv', stdate, enddate, filterAction='both', rank=10000)
        src = os.path.join(os.path.dirname(__file__), 'results.csv')
        dest = os.path.join(os.path.dirname(__file__), 'results_EMATrend'+ticker+".csv")
        os.rename(src, dest)
    except Exception,e:
        print str(e)
        pass

