import pyalgotrade.broker 
from time import mktime
from pyalgotrade.barfeed import membf
from utils import util
import BB_spread
import datetime


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

    def __init__(self, strat, returnsAnalyzer, plotAllInstruments=True, plotBuySell=True, plotPortfolio=True):
        self.__dateTimes = set()

        self.__plotAllInstruments = plotAllInstruments
        self.__plotBuySell = plotBuySell
        self.__plotPortfolio = plotPortfolio
        strat.getBarsProcessedEvent().subscribe(self.__onBarsProcessed)
        strat.getBroker().getOrderUpdatedEvent().subscribe(self.__onOrderEvent)
        self.__portfolioValues = []
        self.__tradeDetails = []
        self.__instrumentDetails = []
        self.__AdjPrices = None
        self.__additionalDataSeries = {}
        strat.attachAnalyzer(returnsAnalyzer)
        self.__returnsAnalyzer = returnsAnalyzer

    def __onBarsProcessed(self, strat, bars):
        dateTime = bars.getDateTime()
        self.__dateTimes.add(dateTime)
        seconds = mktime(bars.getDateTime().timetuple())

        ### Populate AdjClose Price series of instruments....
        if self.__AdjPrices is None:
            self.__AdjPrices = dict.fromkeys(bars.getInstruments()) ### Initialize the dictionary object...
        for instrument in bars.getInstruments():
            adj_Close_Series = self.__AdjPrices[instrument]
            if adj_Close_Series is None:
                adj_Close_Series = [] ### Initialize the value list...
            bar_val = bars.getBar(instrument)
            adjPrice_val = [int(seconds * 1000), bar_val.getAdjClose()]
            adj_Close_Series.append(adjPrice_val)
            self.__AdjPrices[instrument] = adj_Close_Series


        
        # Feed the portfolio evolution subplot.
        if self.__plotPortfolio:
            #self.__portfolioValues[bars.getDateTime()] = strat.getBroker().getEquity()
            val = [int(seconds * 1000), strat.getBroker().getEquity()]
            self.__portfolioValues.append(val)
            
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
                print "BUY: ", execInfo.getDateTime(), execInfo.getPrice()
                seconds = mktime(execInfo.getDateTime().timetuple())
                val = {'x':int(seconds * 1000), 'title': 'B', 'text': 'Bought: ' + str(order.getInstrument()) +'  #No: ' + str(order.getQuantity())}
                self.__tradeDetails.append(val)
            elif action in [pyalgotrade.broker.Order.Action.SELL, pyalgotrade.broker.Order.Action.SELL_SHORT]:
                #self.getSeries("Sell", SellMarker).addValue(execInfo.getDateTime(), execInfo.getPrice())
                print "SELL: ", execInfo.getDateTime(), execInfo.getPrice()
                seconds = mktime(execInfo.getDateTime().timetuple())
                val = {'x':int(seconds * 1000), 'title': 'S', 'text': 'SOLD:' + str(order.getInstrument()) +' #No:' + str(order.getQuantity())}
                self.__tradeDetails.append(val)

    def getAdjCloseSeries(self, instrument):
        return self.__AdjPrices[instrument]


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
    import datetime
    from time import mktime
    from pyalgotrade.utils import dt
    from pyalgotrade.bar import BasicBar, Frequency

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

    bd = [] ##### initialize bar data.....
    for key in data_dict:
        dateTime = dt.timestamp_to_datetime(key)
        data = data_dict[key].split("|") ### split pipe delimted values
        bar = BasicBar(dateTime, 
            float(data[0]) , float(data[1]), float(data[2]), float(data[3]), float(data[4]), float(data[3]), Frequency.DAY)
        bd.append(bar)
    feed = Feed(Frequency.DAY, 1024)
    feed.loadBars(ticker, bd)
    return feed

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
        data_point.append(sma_3days[x+1][0])
        data_point.append(sma_3days[x+1][1] - sma_3days[x][1])
        moneyflow.append(data_point)
    return moneyflow

def redis_build_moneyflow_percent(ticker, stdate, enddate):
    moneyflow = []
    sma_3days = redis_build_sma_3days(ticker, stdate, enddate)
    for x in range(len(sma_3days)-1):
        data_point = []
        data_point.append(sma_3days[x+1][0])
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
    
   
def run_strategy_redis(bBandsPeriod, instrument, startPortfolio, startdate, enddate):
    from pyalgotrade.stratanalyzer import returns

    # Download the bars
    feed = redis_build_feed_EOD(instrument, startdate, enddate)
    #feed = yahoofinance.build_feed([instrument], 2012, 2014, ".")

    strat = BB_spread.BBands(feed, instrument, bBandsPeriod, startPortfolio)

    # Attach a returns analyzers to the strategy.
    returnsAnalyzer = returns.Returns()
    results = StrategyResults(strat, returnsAnalyzer) 

    ###Initialize the bands to maxlength of 5000 for 10 years backtest..
    strat.getBollingerBands().getMiddleBand().setMaxLen(5000)
    strat.getBollingerBands().getUpperBand().setMaxLen(5000)
    strat.getBollingerBands().getLowerBand().setMaxLen(5000) 
    
    #### Add boilingerbands series....
    results.addSeries("upper", strat.getBollingerBands().getUpperBand())
    results.addSeries("middle", strat.getBollingerBands().getMiddleBand())
    results.addSeries("lower", strat.getBollingerBands().getLowerBand())
    strat.run()
    
    return results