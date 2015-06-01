import pyalgotrade.broker 
from time import mktime
from pyalgotrade.barfeed import membf
import BB_spread

###########pickling/serialization .....
#### magic code for serializing instance methods....in python...

def _pickle_method(method):
    func_name = method.im_func.__name__
    obj = method.im_self
    cls = method.im_class
    return _unpickle_method, (func_name, obj, cls)

def _unpickle_method(func_name, obj, cls):
    for cls in cls.mro():
        try:
            func = cls.__dict__[func_name]
        except KeyError:
            pass
        else:
            break
        #return func.__get__(obj, cls)
import copy_reg
import types
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
            
            #print "Datetime, value: ", bars.getDateTime(), strat.getBroker().getEquity()

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

def redis_build_feed(ticker, stdate, enddate):

    import datetime
    import redis
    from time import mktime
    import urlparse
    import os
    from pyalgotrade.utils import dt
    from pyalgotrade.bar import BasicBar, Frequency


    seconds = mktime(stdate.timetuple())
    seconds2 = mktime(enddate.timetuple())

    redis_url = os.environ.get('REDISCLOUD_URL', 'redis://localhost:6379')
    url = urlparse.urlparse(redis_url)
    redisConn = redis.StrictRedis(host=url.hostname, port=url.port, password=url.password)
    redis_Adj_Open = redisConn.zrangebyscore(ticker+':Adj_Open', int(seconds*1000), int(seconds2*1000), 0, -1, True)
    redis_Adj_High = redisConn.zrangebyscore(ticker+':Adj_High', int(seconds*1000), int(seconds2*1000), 0, -1, True)
    redis_Adj_Low = redisConn.zrangebyscore(ticker+':Adj_Low', int(seconds*1000), int(seconds2*1000), 0, -1, True)
    redis_Adj_Close = redisConn.zrangebyscore(ticker+':Adj_Close', int(seconds*1000), int(seconds2*1000), 0, -1, True)
    redis_Adj_Volume = redisConn.zrangebyscore(ticker+':Adj_Volume', int(seconds*1000), int(seconds2*1000), 0, -1, True)

    #### Convert list of lists to dictionary to align keys...
    #### Please note we need to find better solution in the fuutre...
    #### Use adj_close as the master list of lists
    Adj_Open_dict = redis_listoflists_to_dict(redis_Adj_Open)
    Adj_High_dict = redis_listoflists_to_dict(redis_Adj_High)
    Adj_Low_dict = redis_listoflists_to_dict(redis_Adj_Low)
    Adj_Close_dict = redis_listoflists_to_dict(redis_Adj_Close)
    Adj_Volume_dict = redis_listoflists_to_dict(redis_Adj_Volume)
    

    bd = [] ##### initialize bar data.....
    for key in Adj_Close_dict:
        Adj_Close = float(Adj_Close_dict[key])
        dateTime = dt.timestamp_to_datetime(key/1000)

        if (key in Adj_Open_dict) and (key in Adj_Low_dict) \
            and (key in Adj_Volume_dict) and (key in Adj_High_dict):
            Adj_Open = float(Adj_Open_dict[key])
            Adj_High = float(Adj_High_dict[key])
            Adj_Low = float(Adj_Low_dict[key])
            Adj_Volume = float(Adj_Volume_dict[key])
        else:
            ##### Any of the missing keys set to adj_close....
            Adj_Open =  Adj_Close - 0.05
            Adj_High =  Adj_Close + 0.05
            Adj_Low  =  Adj_Close  - 0.05
            Adj_Volume = Adj_Close * 250000 ### Constant volume...
            #print "$$$$$####@@@@", Adj_Close, Adj_Open, Adj_High, Adj_Low, Adj_Volume, dateTime

        #print key, Adj_Close, Adj_Open, Adj_High, Adj_Low, Adj_Volume, dateTime  
        bar = BasicBar(dateTime, 
              Adj_Open , Adj_High, Adj_Low, Adj_Close, Adj_Volume, Adj_Close, Frequency.TRADE)
        bd.append(bar)

    feed = Feed(Frequency.DAY, 1024)
    feed.loadBars(ticker, bd)
    return feed

def run_strategy_redis(bBandsPeriod, instrument, startPortfolio, startdate, enddate):
    from pyalgotrade.stratanalyzer import returns

    # Download the bars
    feed = redis_build_feed(instrument, startdate, enddate)
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