import pyalgotrade.broker 
from time import mktime
from pyalgotrade.barfeed import membf
from pyalgotrade.technical import ma
from utils import util
import BB_spread
import datetime
import json



import copy_reg
import types
def _pickle_method(method):
    """
    Author: Steven Bethard (author of argparse)
    http://bytes.com/topic/python/answers/552476-why-cant-you-pickle-instancemethods
    """
    func_name = method.im_func.__name__
    obj = method.im_self
    cls = method.im_class
    cls_name = ''
    if func_name.startswith('__') and not func_name.endswith('__'):
        cls_name = cls.__name__.lstrip('_')
    if cls_name:
        func_name = '_' + cls_name + func_name
    return _unpickle_method, (func_name, obj, cls)


def _unpickle_method(func_name, obj, cls):
    """
    Author: Steven Bethard
    http://bytes.com/topic/python/answers/552476-why-cant-you-pickle-instancemethods
    """
    for cls in cls.mro():
        try:
            func = cls.__dict__[func_name]
        except KeyError:
            pass
        else:
            return func.__get__(obj, cls)
            #break

copy_reg.pickle(types.MethodType, _pickle_method, _unpickle_method)


class StrategyResults(object):
    """Class responsible for extracting results of a strategy execution.
    """

    def __init__(self, strat, instList, returnsAnalyzer, plotAllInstruments=True, plotBuySell=True, plotPortfolio=True):
        self.__dateTimes = set()

        self.__plotAllInstruments = plotAllInstruments
        self.__plotBuySell = plotBuySell
        self.__plotPortfolio = plotPortfolio
        strat.getBarsProcessedEvent().subscribe(self.__onBarsProcessed)
        strat.getBroker().getOrderUpdatedEvent().subscribe(self.__onOrderEvent)
        self.__instLit = instList
        self.__portfolioValues = []
        self.__tradeDetails = []
        self.__instrumentDetails = []
        self.__MACD = []
        self.__ADX = []
        self.__DMIPlus = []
        self.__DMIMinus = []
        self.__AdjPrices = None
        self.__AdjVolume = None
        self.__additionalDataSeries = {}
        strat.attachAnalyzer(returnsAnalyzer)
        self.__returnsAnalyzer = returnsAnalyzer
        self.__AdjPrices = dict.fromkeys(instList) ### Initialize the dictionary object...
        self.__AdjVolume = dict.fromkeys(instList)

    def __onBarsProcessed(self, strat, bars):
        dateTime = bars.getDateTime()
        self.__dateTimes.add(dateTime)
        seconds = mktime(bars.getDateTime().timetuple())
        dtInMilliSeconds = int(seconds * 1000)
    
        ### Populate AdjClose Price series of instruments....
        #if self.__AdjPrices is None and self.__AdjVolume is None:
         #   self.__AdjPrices = dict.fromkeys(bars.getInstruments()) ### Initialize the dictionary object...
         #   self.__AdjVolume = dict.fromkeys(bars.getInstruments())


        for instrument in bars.getInstruments():
            #### try block to make sure we handle instruments mis-alignment..
            try :
                adj_Close_Series = self.__AdjPrices[instrument]
                adj_Vol_Series = self.__AdjVolume[instrument]
                if adj_Close_Series is None and adj_Vol_Series is None:
                    adj_Close_Series = [] ### Initialize the value list...
                    adj_Vol_Series = [] ### Initialize the value list...
                bar_val = bars.getBar(instrument)
               
                #### Please note we are already populating them with adjusted values so we do not need to set to true...
                adjPrice_val = [dtInMilliSeconds, bar_val.getOpen(), bar_val.getHigh(), \
                        bar_val.getLow(), bar_val.getAdjClose()]
                adj_Close_Series.append(adjPrice_val)
                self.__AdjPrices[instrument] = adj_Close_Series
                ### Populate volume series... as points to display in highchart as columns
                ##### Color green indicates Close higher then open and red indicates lower
                
                if bar_val.getAdjClose() >  bar_val.getOpen():
                    color_value = '#009933'
                else:
                    color_value = '#CC3300' 
                volume = bar_val.getVolume()
                volpoint = {'color':color_value, 'x':dtInMilliSeconds, 'y':volume}
                #adj_Vol_Series.append([dtInMilliSeconds, bar_val.getVolume()])
                adj_Vol_Series.append(volpoint) 
                self.__AdjVolume[instrument] =  adj_Vol_Series
            except :
                pass
        
        # Plot portfolio value and all other signals...
        if self.__plotPortfolio:
            self.__portfolioValues.append([dtInMilliSeconds, strat.getBroker().getEquity()])
            if strat.getMACD() is not None:
                self.__MACD.append([dtInMilliSeconds, strat.getMACD()[-1]])
            if strat.getADX() is not None:
                self.__ADX.append([dtInMilliSeconds, strat.getADX()[-1]])
            if strat.getDMIPlus() is not None:
                self.__DMIPlus.append([dtInMilliSeconds, strat.getDMIPlus()[-1]])
            if strat.getDMIMinus() is not None:
                self.__DMIMinus.append([dtInMilliSeconds, strat.getDMIMinus()[-1]])
            
        if self.__plotAllInstruments:
            for instrument in bars.getInstruments():
                instrument_shares = [int(seconds * 1000), strat.getBroker().getShares(instrument)]
                self.__instrumentDetails.append(instrument_shares)

    def __onOrderEvent(self, broker_, orderEvent):
        order = orderEvent.getOrder()
        if self.__plotBuySell and orderEvent.getEventType() in (pyalgotrade.broker.OrderEvent.Type.PARTIALLY_FILLED, pyalgotrade.broker.OrderEvent.Type.FILLED): #and order.getInstrument() == self.__instrument:
            action = order.getAction()
            execInfo = orderEvent.getEventInfo()
            if action in [pyalgotrade.broker.Order.Action.BUY, pyalgotrade.broker.Order.Action.BUY_TO_COVER]:
                #self.getSeries("Buy", BuyMarker).addValue(execInfo.getDateTime(), execInfo.getPrice())
                #print "BUY: ", execInfo.getDateTime(), execInfo.getPrice()
                seconds = mktime(execInfo.getDateTime().timetuple())
                if action == pyalgotrade.broker.Order.Action.BUY:
                    val = {'x':int(seconds * 1000), 'title': 'B', 'text': 'Bought: ' + str(order.getInstrument()) +'  Shares: ' + str(order.getQuantity()) + " Price " +  str(execInfo.getPrice())}
                else:
                    val = {'x':int(seconds * 1000), 'title': 'CB', 'text': 'Cover Buy: ' + str(order.getInstrument()) +'  Shares: ' + str(order.getQuantity()) + " Price " +  str(execInfo.getPrice())}

                #val = {'x':int(seconds * 1000), 'title': 'B', 'text': 'Bought: ' + str(order.getInstrument()) +'  Shares: ' + str(order.getQuantity()) + " Price " +  str(execInfo.getPrice())}
                self.__tradeDetails.append(val)
            elif action in [pyalgotrade.broker.Order.Action.SELL, pyalgotrade.broker.Order.Action.SELL_SHORT]:
                #self.getSeries("Sell", SellMarker).addValue(execInfo.getDateTime(), execInfo.getPrice())
                #print "SELL: ", execInfo.getDateTime(), execInfo.getPrice()
                seconds = mktime(execInfo.getDateTime().timetuple())
                if action == pyalgotrade.broker.Order.Action.SELL:
                    val = {'x':int(seconds * 1000), 'title': 'S', 'text': 'SOLD:' + str(order.getInstrument()) +' Shares:' + str(order.getQuantity()) + " Price " +  str(execInfo.getPrice())}
                else:
                    val = {'x':int(seconds * 1000), 'title': 'SS', 'text': 'Short SELL:' + str(order.getInstrument()) +' Shares:' + str(order.getQuantity()) + " Price " +  str(execInfo.getPrice())}

                #val = {'x':int(seconds * 1000), 'title': 'S', 'text': 'SOLD:' + str(order.getInstrument()) +' Shares:' + str(order.getQuantity()) + " Price " +  str(execInfo.getPrice())}
                self.__tradeDetails.append(val)

    def getAdjCloseSeries(self, instrument):
        return self.__AdjPrices[instrument]

    def getAdjVolSeries(self, instrument):
        return self.__AdjVolume[instrument]

    def addSeries(self, name, series):
        #### please note need to figure out elegant way of pickling dictionary items...
        self.__additionalDataSeries[name] = series

    def getSeries(self, name):
        dataseries = []
        dateList = list(self.__dateTimes)
        dateList.sort()
        seq_data = self.__additionalDataSeries[name]
        for x in range(len(dateList)):
            dt =  dateList[x]
            sec = mktime(dt.timetuple())
            val = [int(sec * 1000), seq_data.getValueAbsolute(x)]
            dataseries.append(val)
        return dataseries

    def getPortfolioResult(self):
        return self.__portfolioValues

    def getMACD(self):
        return self.__MACD

    def getADX(self):
        return self.__ADX

    def getDMIPlus(self):
        return self.__DMIPlus

    def getDMIMinus(self):
        return self.__DMIMinus

    def getInstrumentDetails(self):
        return self.__instrumentDetails 

    def getTradeDetails(self):
        return self.__tradeDetails

    def getDateTimes(self):
        return self.__dateTimes 

    def getCumulativeReturns(self):
        returns = self.__returnsAnalyzer.getCumulativeReturns()
        dataseries = []
        dateList = list(self.__dateTimes)
        dateList.sort()
        for x in range(len(dateList)):
            dt =  dateList[x]
            sec = mktime(dt.timetuple())
            val = [int(sec * 1000), returns.getValueAbsolute(x)]
            dataseries.append(val)
        return dataseries

    def getReturns(self):
        returns = self.__returnsAnalyzer.getReturns()
        dataseries = []
        dateList = list(self.__dateTimes)
        dateList.sort()
        for x in range(len(dateList)):
            dt =  dateList[x]
            sec = mktime(dt.timetuple())
            val = [int(sec * 1000), returns.getValueAbsolute(x)]
            dataseries.append(val)
        return dataseries

class Feed(membf.BarFeed):
    def __init__(self, frequency, maxLen=1024):
        membf.BarFeed.__init__(self, frequency, maxLen)

    def barsHaveAdjClose(self):
        return True

    def loadBars(self, instrument, bars):
        self.addBarsFromSequence(instrument, bars)

def redis_listoflists_to_dict(redis_list):
    list_values, list_keys = zip(*redis_list)
    return dict(zip(list_keys, list_values))

def redis_build_feed_EOD(ticker, stdate, enddate):
    from pyalgotrade.bar import BasicBar, Frequency

    feed = Feed(Frequency.DAY, 1024)
    return add_feeds_EOD_redis(feed, ticker, stdate, enddate)



def add_feeds_EOD_redis( feed, ticker, stdate, enddate):
    import datetime
    from time import mktime
    from pyalgotrade.utils import dt
    from pyalgotrade.bar import BasicBar, Frequency

    seconds = mktime(stdate.timetuple())
    seconds2 = mktime(enddate.timetuple())

    data_dict = {}
    try:
        redisConn = util.get_redis_conn()
        ### added EOD as data source
        ticker_data = redisConn.zrangebyscore(ticker + ":EOD", int(seconds), int(seconds2), 0, -1, True)
        #ticker_data = redisConn.zrangebyscore(ticker + ":EOD_UnAdj", int(seconds), int(seconds2), 0, -1, True)
        data_dict = redis_listoflists_to_dict(ticker_data)
    except Exception,e:
        print str(e)
        pass

    bd = [] ##### initialize bar data.....
    for key in data_dict:
        dateTime = dt.timestamp_to_datetime(key)
        data = data_dict[key].split("|") ### split pipe delimted values
        bar = BasicBar(dateTime, 
            float(data[0]) , float(data[1]), float(data[2]), float(data[3]), float(data[4]), float(data[3]), Frequency.DAY)
            #float(data[0]) , float(data[1]), float(data[2]), float(data[3]), float(data[5]), float(data[4]), Frequency.DAY)
        bd.append(bar)
    #feed = Feed(Frequency.DAY, 1024)
    feed.loadBars(ticker, bd)
    return feed

def redis_build_volume_sma_ndays(ticker, nDays, stdate, enddate):
    import datetime
    from time import mktime
    from pyalgotrade.utils import dt

    seconds = mktime(stdate.timetuple())
    seconds2 = mktime(enddate.timetuple())
    data_dict = {}
    try:
        redisConn = util.get_redis_conn()
        ticker_data = redisConn.zrangebyscore(ticker + ":EOD", int(seconds), int(seconds2), 0, -1, True)
        data_dict = redis_listoflists_to_dict(ticker_data)
    except Exception,e:
        print str(e)
        pass

    #### Compute sma_ndays 
    #### Avg(Close_Price * volume) over n days...
    sma_ndays = [] ##### initialize bar data.....
    keys = sorted(data_dict.keys())
    i = 0 
    j = nDays
    while j < len(keys):
        data_point = []
        Avg = 0
        timestamp = keys[j-1]
        avg_list = keys[i:j]
        for key in avg_list:
            data = data_dict[key].split("|")
            Avg += float(float(data[4]))

        seconds = mktime(datetime.datetime.fromtimestamp(timestamp).timetuple())
        data_point.append(int(seconds)*1000)
        data_point.append(Avg/nDays)
        sma_ndays.append(data_point)
        i +=1
        j +=1
    return sma_ndays

def redis_build_sma_3days(ticker, stdate, enddate):
    import datetime
    from time import mktime
    from pyalgotrade.utils import dt

    seconds = mktime(stdate.timetuple())
    seconds2 = mktime(enddate.timetuple())
    data_dict = {}
    try:
        redisConn = util.get_redis_conn()
        ticker_data = redisConn.zrangebyscore(ticker + ":EOD", int(seconds), int(seconds2), 0, -1, True)
        data_dict = redis_listoflists_to_dict(ticker_data)
    except Exception,e:
        print str(e)
        pass

    #### Compute sma_3days 
    #### Avg(Close_Price * volume) over 3 days...
    sma_3days = [] ##### initialize bar data.....
    keys = sorted(data_dict.keys())
    i = 0 
    j = 3
    while j < len(keys):
        data_point = []
        Avg = 0
        timestamp = keys[j-1]
        avg_list = keys[i:j]
        for key in avg_list:
            data = data_dict[key].split("|")
            Avg += float(data[3]) * float(data[4])
        data_point.append(timestamp)
        data_point.append(Avg/3.0)
        sma_3days.append(data_point)
        i +=1
        j +=1
    return sma_3days

def redis_build_moneyflow(ticker, stdate, enddate):
    moneyflow = []
    sma_3days = redis_build_sma_3days(ticker, stdate, enddate)
    for x in range(len(sma_3days)-1):
        data_point = []
        ### Add first data point null that way cashflow can align with other charts...
        if x==0:
            firstDay = []
            sec_fd = mktime(datetime.datetime.fromtimestamp(sma_3days[0][0]).timetuple())
            firstDay.append(int(sec_fd)*1000)
            firstDay.append(None)
            moneyflow.append(firstDay)
        seconds = mktime(datetime.datetime.fromtimestamp(sma_3days[x+1][0]).timetuple())
        data_point.append(int(seconds)*1000) ### datetime in milliseconds...
        data_point.append(sma_3days[x+1][1] - sma_3days[x][1])
        moneyflow.append(data_point)
    return moneyflow

def redis_build_moneyflow_percent(ticker, stdate, enddate):
    moneyflow = []
    sma_3days = redis_build_sma_3days(ticker, stdate, enddate)
    for x in range(len(sma_3days)-1):
        data_point = []
        ### Add first data point null that way cashflow can align with other charts...
        if x==0:
            firstDay = []
            sec_fd = seconds = mktime(datetime.datetime.fromtimestamp(sma_3days[0][0]).timetuple())
            firstDay.append(int(sec_fd)*1000)
            firstDay.append(None)
            moneyflow.append(firstDay)

        seconds = mktime(datetime.datetime.fromtimestamp(sma_3days[x+1][0]).timetuple())
        data_point.append(int(seconds)*1000)### datetime in milliseconds...
        diff = sma_3days[x+1][1] - sma_3days[x][1]
        data_point.append(diff/sma_3days[x][1] * 100)
        moneyflow.append(data_point)
    return moneyflow

def tickersRankByMoneyFlowPercent(date):
    import collections

    momentum_rank = {}
    tickerList = util.getTickerList()
    for x in range(len(tickerList)):
        moneyflow = redis_build_moneyflow_percent(tickerList[x], (date - datetime.timedelta(days=10)), date)
        if len(moneyflow) > 1:
            data_point = moneyflow[len(moneyflow)-1]
            momentum_rank[data_point[1]] = tickerList[x]

    return collections.OrderedDict(sorted(momentum_rank.items(), reverse=True))

def build_feed_TN(ticker, stdate, enddate):
    from pyalgotrade.bar import BasicBar, Frequency

    feed = Feed(Frequency.DAY, 1024)
    return add_feeds_TN(feed, ticker, stdate, enddate)


def add_feeds_TN(feed, ticker, stdate, enddate):
    import datetime
    from time import mktime
    from pyalgotrade.utils import dt
    from pyalgotrade.bar import BasicBar, Frequency
    import csv
    import dateutil.parser


    bd = [] ##### initialize bar data.....
    file_TN = util.getRelativePath(ticker+'_TN.csv')
    with open(file_TN, 'rU') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            dateTime = dateutil.parser.parse(row['Date'])
            bar = BasicBar(dateTime, 
                float(row['Open']) , float(row['High']), float(row['Low']), float(row['Close']), float(row['Volume']), float(row['Close']), Frequency.DAY)
            bd.append(bar)
    feed.loadBars(ticker, bd)
    return feed
    
   
def run_strategy_redis(bBandsPeriod, instrument, startPortfolio, startdate, enddate):
    from pyalgotrade.stratanalyzer import returns

    feed = redis_build_feed_EOD(instrument, startdate, enddate)
    #feed = build_feed_TN(instrument, startdate, enddate)
    #feed = yahoofinance.build_feed([instrument], 2012, 2014, ".")

    # Add the SPY bars, which are used to determine if the market is Bullish or Bearish
    # on a particular day.
    feed = add_feeds_EOD_redis(feed, 'SPY', startdate, enddate)

    strat = BB_spread.BBSpread(feed, instrument, bBandsPeriod, startPortfolio)

    instList = [instrument, 'SPY']

    # Attach a returns analyzers to the strategy.
    returnsAnalyzer = returns.Returns()
    results = StrategyResults(strat, instList, returnsAnalyzer)

    ###Initialize the bands to maxlength of 5000 for 10 years backtest..
    strat.getBollingerBands().getMiddleBand().setMaxLen(5000)
    strat.getBollingerBands().getUpperBand().setMaxLen(5000)
    strat.getBollingerBands().getLowerBand().setMaxLen(5000) 
    strat.getRSI().setMaxLen(5000)
    strat.getEMAFast().setMaxLen(5000)
    strat.getEMASlow().setMaxLen(5000)
    strat.getEMASignal().setMaxLen(5000)
    #### Add boilingerbands series....
    strat.run()
    #print "################: " , strat.getMACD()

    results.addSeries("upper", strat.getBollingerBands().getUpperBand())
    results.addSeries("middle", strat.getBollingerBands().getMiddleBand())
    results.addSeries("lower", strat.getBollingerBands().getLowerBand())
    results.addSeries("RSI", strat.getRSI())
    results.addSeries("EMA Fast", strat.getEMAFast())
    results.addSeries("EMA Slow", strat.getEMASlow())
    results.addSeries("EMA Signal", strat.getEMASignal())
    #results.addSeries("macd", strat.getMACD())
    
    return results

def run_strategy_TN(bBandsPeriod, instrument, startPortfolio, startdate, enddate):
    from pyalgotrade.stratanalyzer import returns

    #feed = redis_build_feed_EOD(instrument, startdate, enddate)
    feed = build_feed_TN(instrument, startdate, enddate)
    #feed = yahoofinance.build_feed([instrument], 2012, 2014, ".")

    # Add the SPY bars, which are used to determine if the market is Bullish or Bearish
    # on a particular day.
    feed = add_feeds_TN(feed, 'SPY', startdate, enddate)

    strat = BB_spread.BBSpread(feed, instrument, bBandsPeriod, startPortfolio)

    instList = [instrument, 'SPY']

    # Attach a returns analyzers to the strategy.
    returnsAnalyzer = returns.Returns()
    results = StrategyResults(strat, instList, returnsAnalyzer)

    ###Initialize the bands to maxlength of 5000 for 10 years backtest..
    strat.getBollingerBands().getMiddleBand().setMaxLen(5000)
    strat.getBollingerBands().getUpperBand().setMaxLen(5000)
    strat.getBollingerBands().getLowerBand().setMaxLen(5000) 
    strat.getRSI().setMaxLen(5000)
    strat.getEMAFast().setMaxLen(5000)
    strat.getEMASlow().setMaxLen(5000)
    strat.getEMASignal().setMaxLen(5000)
    #### Add boilingerbands series....
    strat.run()
    #print "################: " , strat.getMACD()

    results.addSeries("upper", strat.getBollingerBands().getUpperBand())
    results.addSeries("middle", strat.getBollingerBands().getMiddleBand())
    results.addSeries("lower", strat.getBollingerBands().getLowerBand())
    results.addSeries("RSI", strat.getRSI())
    results.addSeries("EMA Fast", strat.getEMAFast())
    results.addSeries("EMA Slow", strat.getEMASlow())
    results.addSeries("EMA Signal", strat.getEMASignal())
    #results.addSeries("macd", strat.getMACD())
    
    return results