import pyalgotrade.broker 
from time import mktime
from pyalgotrade.barfeed import membf
from pyalgotrade.technical import ma
from utils import util
import BB_spread
import Orders_exec
import datetime
import json
import csv
import dateutil.parser
import os
from pyalgotrade.stratanalyzer import returns
from pyalgotrade import dataseries
import time



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

    def __init__(self, strat, instList, returnsAnalyzer, plotAllInstruments=True, plotBuySell=True, plotPortfolio=True, plotSignals=False):
        self.__dateTimes = set()

        self.__plotAllInstruments = plotAllInstruments
        self.__plotBuySell = plotBuySell
        self.__plotPortfolio = plotPortfolio
        self.__plotSignals = plotSignals
        strat.getBarsProcessedEvent().subscribe(self.__onBarsProcessed)
        strat.getBroker().getOrderUpdatedEvent().subscribe(self.__onOrderEvent)
        self.__instList = instList
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
        self.__orders = {} #### Need to be populated after successfully running the strategy.... by calling addOrders()....
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

        if self.__plotSignals:
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

    def addOrders(self, orders):
        self.__orders = orders

    def getOrders(self):
        return self.__orders

    '''
    def getOrdersFilteredByMomentumRank(self, filterCriteria=25):
        filteredOrders = {}
        for key, value in self.__orders.iteritems():

            if value[0][1] == 'Buy' or value[0][1] == 'Sell':
                dt = datetime.datetime.fromtimestamp(key)
                #mom_rank_orderedlist = tickersRankByMoneyFlowPercent(dt)
                mom_rank_orderedlist = tickersRankByMoneyFlow(dt)
                rank = mom_rank_orderedlist.values().index(self.__instList[0]) ### Please note first in the list is the stock details..
                if rank <= filterCriteria:
                    filteredOrders[key] = value
                else:
                    util.Log.info("Filtered Order of: " + self.__instList[0] + " on date: " + dt.strftime("%B %d, %Y") + " rank: " + str(rank))
            else:
                filteredOrders[key] = value

        return filteredOrders
    '''

    def getOrdersFilteredByRules(self, filterCriteria=25):
        filteredOrders = {}
        for key, value in self.__orders.iteritems():

            if value[0][1] == 'Buy' or value[0][1] == 'Sell':
                dt = datetime.datetime.fromtimestamp(key)
                ADR_5days = ADR(self.__instList[0], 5, dt)
                vol_5days = volume(self.__instList[0], 5, dt)
                mf = moneyflow(self.__instList[0],  dt)
                if (ADR_5days >=1) and (vol_5days >= 1000000) and mf >= 2000000:
                    filteredOrders[key] = value
                else:
                    util.getLogger().info("Filtered Order of: " + self.__instList[0] + " on date: " + dt.strftime("%B %d, %Y") 
                        + " ADR :", ADR_5days + " volume: " + vol_5days + " moneyflow: " + mf)
            else:
                filteredOrders[key] = value

        return filteredOrders

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

class Returns(returns.Returns):
     def __init__(self):
        #returns.Returns.__init__(self)
        self.__netReturns = dataseries.SequenceDataSeries()
        self.__netReturns.setMaxLen(5000)
        self.__cumReturns = dataseries.SequenceDataSeries()
        self.__cumReturns.setMaxLen(5000)
       
       

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

    ###### Please note zrangebyscore returns between values the scores to make it include both start date and end date as part of
    ######## data series we need to do date arithmetic on passed in data ################
    stdate, enddate = util.getRedisEffectiveDates(stdate, enddate)

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
        #dateTime = dt.timestamp_to_datetime(key)
        dateTime = dt.timestamp_to_datetime(key).replace(tzinfo=None) 
        data = data_dict[key].split("|") ### split pipe delimted values
        bar = BasicBar(dateTime, 
            float(data[0]) , float(data[1]), float(data[2]), float(data[3]), float(data[4]), float(data[3]), Frequency.DAY)
            #float(data[0]) , float(data[1]), float(data[2]), float(data[3]), float(data[5]), float(data[4]), Frequency.DAY)
        bd.append(bar)
    #feed = Feed(Frequency.DAY, 1024)
    feed.loadBars(ticker, bd)
    return feed

def ADR(ticker,nDays, date):
    adr_series = redis_build_ADR_ndays(ticker, nDays, (date - datetime.timedelta(days=10)), date)
    return adr_series[-1]

### Average Daily range....
def redis_build_ADR_ndays(ticker, nDays, stdate, enddate):
    import datetime
    from time import mktime
    from pyalgotrade.utils import dt

    ###### Please note zrangebyscore returns between values the scores to make it include both start date and end date as part of
    ######## data series we need to do date arithmetic on passed in data ################
    stdate, enddate = util.getRedisEffectiveDates(stdate, enddate)

    seconds = mktime(stdate.timetuple())
    seconds2 = mktime(enddate.timetuple())
    data_dict = {}
    try:
        redisConn = util.get_redis_conn()
        ticker_data = redisConn.zrangebyscore(ticker + ":EOD", int(seconds), int(seconds2), 0, -1, True)
        if(len(ticker_data) > 1):
            data_dict = redis_listoflists_to_dict(ticker_data)
        #data_dict = redis_listoflists_to_dict(ticker_data)
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
            Avg += (float(data[1])-float(data[2]))

        seconds = mktime(datetime.datetime.fromtimestamp(timestamp).timetuple())
        data_point.append(int(seconds)*1000)
        data_point.append(Avg/nDays)
        sma_ndays.append(data_point)
        i +=1
        j +=1
    return sma_ndays

def volume(ticker, nDays, date):
    vol_series = redis_build_volume_sma_ndays(ticker, nDays, (date - datetime.timedelta(days=10)), date)
    return vol_series[-1]

def redis_build_volume_sma_ndays(ticker, nDays, stdate, enddate):
    import datetime
    from time import mktime
    from pyalgotrade.utils import dt

    ###### Please note zrangebyscore returns between values the scores to make it include both start date and end date as part of
    ######## data series we need to do date arithmetic on passed in data ################
    stdate, enddate = util.getRedisEffectiveDates(stdate, enddate)

    seconds = mktime(stdate.timetuple())
    seconds2 = mktime(enddate.timetuple())
    data_dict = {}
    try:
        redisConn = util.get_redis_conn()
        ticker_data = redisConn.zrangebyscore(ticker + ":EOD", int(seconds), int(seconds2), 0, -1, True)
        if(len(ticker_data) > 1):
            data_dict = redis_listoflists_to_dict(ticker_data)
        #data_dict = redis_listoflists_to_dict(ticker_data)
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


    ###### Please note zrangebyscore returns between values the scores to make it include both start date and end date as part of
    ######## data series we need to do date arithmetic on passed in data ################
    stdate, enddate = util.getRedisEffectiveDates(stdate, enddate)

    seconds = mktime(stdate.timetuple())
    seconds2 = mktime(enddate.timetuple())
    data_dict = {}
    try:
        redisConn = util.get_redis_conn()
        ticker_data = redisConn.zrangebyscore(ticker + ":EOD", int(seconds), int(seconds2), 0, -1, True)
        if(len(ticker_data) > 1):
            data_dict = redis_listoflists_to_dict(ticker_data)
        #data_dict = redis_listoflists_to_dict(ticker_data)
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


def tickersRankByCashFlow(date, sortOrder):
    import collections

    momentum_rank = {}
    tickerList = util.getMasterTickerList()
    for x in range(len(tickerList)):
        moneyflow = cashflow_timeseries_TN(tickerList[x], (date - datetime.timedelta(days=10)), date)
        if len(moneyflow) > 1:
            data_point = moneyflow[len(moneyflow)-1]
            momentum_rank[data_point[1]] = tickerList[x]
    
    if sortOrder == 'Reverse':
        return collections.OrderedDict(sorted(momentum_rank.items(), reverse=True))
    else:
        return collections.OrderedDict(sorted(momentum_rank.items(), reverse=False))

def cashflow(ticker, date):
    cashflow = cashflow_timeseries_TN(ticker, (date - datetime.timedelta(days=10)), date)
    return cashflow[-1]
    


def cashflow_timeseries_TN(ticker, startdate, enddate):

    ###### Please note zrangebyscore returns between values the scores to make it include both start date and end date as part of
    ######## data series we need to do date arithmetic on passed in data ################
    startdate, enddate = util.getRedisEffectiveDates(startdate, enddate)

    seconds = mktime(startdate.timetuple())
    seconds2 = mktime(enddate.timetuple())
    data_dict = {}
    try:
        redisConn = util.get_redis_conn()
        ticker_data = redisConn.zrangebyscore(ticker + ":EOD", int(seconds), int(seconds2), 0, -1, True)
        if(len(ticker_data) > 1):
            data_dict = redis_listoflists_to_dict(ticker_data)
    except Exception,e:
        print str(e)
        pass

    cashflow_accum = []
    keys = sorted(data_dict.keys())
    i = 0 
    j = 2
    while j < len(keys):
        data_point = []
        cashflow = 0
        timestamp = keys[j-1]
        #timestamp = keys[j]
        keyList = keys[i:j]
        priceList = []
        volumeList = []
        for key in keyList:
            data = data_dict[key].split("|")
            priceList.append(float(data[3]))
            volumeList.append(float(data[4]))

        cashflow =  (priceList[1] - priceList[0]) * volumeList[1]
        seconds = mktime(datetime.datetime.fromtimestamp(timestamp).timetuple())
        data_point.append(int(seconds)*1000)
        data_point.append(cashflow)
        cashflow_accum.append(data_point)
        i +=1
        j +=1

    return cashflow_accum


def moneyflow(ticker, date):
    moneyflow = redis_build_moneyflow(ticker, (date - datetime.timedelta(days=10)), date)
    return moneyflow[-1]

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
        #data_point.append(sma_3days[x+1][1])
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
        #######We should definitely revisit and check this problem...
        if sma_3days[x][1] != 0:
            data_point.append(diff/sma_3days[x][1] * 100)
        else:
            data_point.append(-9999.00) ### Please note for now to make sure we are not facing divide by zero issue
        moneyflow.append(data_point)
    return moneyflow

def tickersRankByMoneyFlowPercent(date, sortOrder):
    import collections

    momentum_rank = {}
    tickerList = util.getMasterTickerList()
    for x in range(len(tickerList)):
        moneyflow = redis_build_moneyflow_percent(tickerList[x], (date - datetime.timedelta(days=10)), date)
        if len(moneyflow) > 1:
            data_point = moneyflow[len(moneyflow)-1]
            #data_point = moneyflow[len(moneyflow)-2]
            momentum_rank[data_point[1]] = tickerList[x]
        time.sleep(0.0001)

    if sortOrder == 'Reverse':
        return collections.OrderedDict(sorted(momentum_rank.items(), reverse=True))
    else:
        return collections.OrderedDict(sorted(momentum_rank.items(), reverse=False))

def tickersRankByMoneyFlow(date, sortOrder):
    import collections

    momentum_rank = {}
    tickerList = util.getMasterTickerList()
    for x in range(len(tickerList)):
        moneyflow = redis_build_moneyflow(tickerList[x], (date - datetime.timedelta(days=10)), date)
        if len(moneyflow) > 1:
            data_point = moneyflow[len(moneyflow)-1]
            momentum_rank[data_point[1]] = tickerList[x]
    if sortOrder == 'Reverse':
        return collections.OrderedDict(sorted(momentum_rank.items(), reverse=True))
    else:
        return collections.OrderedDict(sorted(momentum_rank.items(), reverse=False))

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
            ### Let's only populate the dates passed in the feed...
            if dateTime.date() <= enddate.date() and dateTime.date() >= stdate.date() :
                bar = BasicBar(dateTime, 
                float(row['Open']) , float(row['High']), float(row['Low']), float(row['Close']), float(row['Volume']), float(row['Close']), Frequency.DAY)
                bd.append(bar)
    feed.loadBars(ticker, bd)
    return feed

def getEarningsCal(instrument):
    import csv
    import dateutil.parser

    cal = []
    file_cal = util.getRelativePath('earnings_cal.csv')
    with open(file_cal, 'rU') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            symbol = row['Ticker']
            if symbol == instrument :
                if row['Flag'] == 'A':
                    dateTime =  dateutil.parser.parse(row['Cal_Date'])
                else:
                      ### Add additional day ...
                    if dateutil.parser.parse(row['Cal_Date']).date().weekday == 0:
                        dateTime = dateutil.parser.parse(row['Cal_Date']) - datetime.timedelta(days=2)
                    else:
                        dateTime = dateutil.parser.parse(row['Cal_Date']) - datetime.timedelta(days=1)
                cal.append(dateTime.date())
    return cal


def processOptionsFile(inputfile, outputfile):
    header = True
    keyList = [] ### we need only option row per ticker per type...
    #with open('L3_options_20131101.csv', 'rU') as fin:
    with open(inputfile, 'rU') as fin:
        with open(outputfile, 'w') as fout :
            reader = csv.DictReader(fin)
            for row in reader:
                #### Apply above stated rules to filter the rows...
                data_date = dateutil.parser.parse(row[' DataDate'])
                exp_date =  dateutil.parser.parse(row['Expiration'])
                intrinsicVal = float(row['UnderlyingPrice']) - float(row['Strike'])
                key = row['UnderlyingSymbol'] + row['Type']
                fieldnames = ['UnderlyingSymbol',   'UnderlyingPrice',  'Flags',    'OptionSymbol', 'Type',\
                                'Expiration', 'DataDate', 'Strike', 'Last', 'Bid', 'Ask', 'Volume', 'OpenInterest', 'T1OpenInterest', \
                                    'IVMean',   'IVBid',    'IVAsk', 'Delta', 'Gamma',  'Theta', 'Vega', 'AKA']
                ### Populate delta flag....
                Delta = False
                if row['Type'] == 'call' and float(row ['Delta']) >= 0.70:
                    Delta = True
                elif row['Type'] == 'put' and float(row ['Delta']) >= -0.70:
                    Delta = True

                #and abs(float(row ['Delta'])) >= 0.70

                if  (exp_date - data_date).days >= 30 and intrinsicVal > 0 and Delta and (0.10 <= float(row['Ask']) - float(row['Bid']) <= 0.35) and float(row['OpenInterest']) >= 100 and key not in keyList :
                    
                    
                    if os.stat(outputfile).st_size == 0 and header:
                        writer = csv.DictWriter(fout, fieldnames=fieldnames)
                        writer.writeheader()
                        header = False
                    else:
                        writer = csv.DictWriter(fout, fieldnames=fieldnames)

                    writer.writerow(
                            {'UnderlyingSymbol': row['UnderlyingSymbol'], 'UnderlyingPrice': row['UnderlyingPrice'], 
                            'Flags': row['Flags'],  'OptionSymbol': row['OptionSymbol'], 'Type':row['Type'], 'Expiration': row['Expiration'], 
                            'DataDate': row[' DataDate'], 'Strike': row['Strike'], 'Last': row['Last'], 'Bid': row['Bid'], 'Ask': row['Ask'], 
                            'Volume': row['Volume'], 'OpenInterest': row['OpenInterest'], 'T1OpenInterest': row['T1OpenInterest'], 'IVMean': row['IVMean'], 
                            'IVBid': row['IVBid'], 'IVAsk': row['IVAsk'], 'Delta': row['Delta'], 'Gamma': row['Gamma'], 'Theta': row['Theta'], 
                            'Vega': row['Vega'], 'AKA': row['AKA'] }
                    )
                    keyList.append(key) ### to track specific ticker option has been populated...
    return "Successfully processed"

##### Orders filtered by momentum rank....
def getOrdersFiltered(orders, instrument, filterCriteria=20):
    filteredOrders = {}
    
    for key, value in orders.iteritems():

        if value[0][1] == 'Buy' or value[0][1] == 'Sell':

            '''
            dt = datetime.datetime.fromtimestamp(key)
            #dtactual = dt + datetime.timedelta(days=1)
            if value[0][1] == 'Buy':
                mom_rank_orderedlist = tickersRankByCashFlow(dt, sortOrder = 'Reverse')
                #mom_rank_orderedlist = tickersRankByMoneyFlow(dtactual, sortOrder = 'Reverse')
                rank = mom_rank_orderedlist.values().index(instrument) if instrument in mom_rank_orderedlist.values() else -1 ### Please return high number so that orders do not get filtered..
            else:
                mom_rank_orderedlist = tickersRankByCashFlow(dt, sortOrder = 'Ascending')
                #mom_rank_orderedlist = tickersRankByMoneyFlow(dtactual, sortOrder = 'Ascending')
                rank = mom_rank_orderedlist.values().index(instrument) if instrument in mom_rank_orderedlist.values() else -1 ### Please return high number so that orders do not get filtered..
            print "^^^^^^^^^^^^^^^^^^^^^^^^@@@@@@@@@@@@@: ", dt, rank, mom_rank_orderedlist.keys()[rank]
            newval = []
            newval.append((value[0][0], value[0][1], value[0][2], rank))
            if rank <= filterCriteria:
                filteredOrders[key] =  newval
            else:
                util.Log.info("Filtered Order of: " + instrument + " on date: " + dt.strftime("%B %d, %Y") + " rank: " + str(rank))
            '''
            dt = datetime.datetime.fromtimestamp(key)
            seconds = mktime(dt.timetuple()) #### please note you need to get money flow of the one day before......
            keyString = int(seconds)*1000
            rediskey = "cashflow:"+str(keyString)
            redisConn = util.get_redis_conn()
            if value[0][1] == 'Buy':
                rank = redisConn.zrevrank(rediskey, instrument) 
            else:
                rank = redisConn.zrank(rediskey, instrument) 
            print "^^^^^^^^^^^^^^^^^^^^^^^^@@@@@@@@@@@@@: ", dt, rediskey, rank
            ### update rank based on cashflow for BUY and SELL orders...
            newval = []
            newval.append((value[0][0], value[0][1], value[0][2], rank))
            ########## Please note we are just appending relevant cashflow ranks and relevant filter rules will be applied 
            ########## during portfolio simulation rules...
            #filteredOrders[key] = newval
            if rank <= filterCriteria:
                #filteredOrders[key] = value
                filteredOrders[key] = newval
            else:
                util.Log.info("Filtered Order of: " + instrument + " on date: " + dt.strftime("%B %d, %Y") + " rank: " + str(rank))
        else:
            filteredOrders[key] = value

    return filteredOrders

def getOrdersFilteredByRules(orders, instrument):
        filteredOrders = {}
        for key, value in orders.iteritems():

            if value[0][1] == 'Buy' or value[0][1] == 'Sell':
                dt = datetime.datetime.fromtimestamp(key)
                ADR_5days = ADR(instrument, 5, dt)
                vol_5days = volume(instrument, 5, dt)
                mf = cashflow(instrument,  dt)
                newval = []
                newval.append((value[0][0], value[0][1], value[0][2], -1))
                if (ADR_5days[1] >=1) and (vol_5days[1] >= 1000000) and mf[1] >= 2000000:
                #if (ADR_5days[1] >=1) and (vol_5days[1] >= 500000) and mf[1] >= 750000 and value[0][1] == 'Buy':
                    print "Data:  ", dt, ADR_5days, vol_5days, mf
                    filteredOrders[key] = newval
                elif (ADR_5days[1] >=1) and (vol_5days[1] >= 1000000) and mf[1] <= -2000000 and value[0][1] == 'Sell':
                    print "Data:  ", ADR_5days, vol_5days, mf
                    filteredOrders[key] = newval
                else:
                    print "Data:  ", dt, ADR_5days, vol_5days, mf
                    print "In the else loop....................########"
                    util.Log.info("Filtered Order of: " + instrument + " on date: " + dt.strftime("%B %d, %Y") 
                        + " ADR :", str(ADR_5days[1]) + " volume: " + str(vol_5days[1]) + " moneyflow: " + str(mf[1]))
            else:
                filteredOrders[key] = value

        return filteredOrders


    
   
def run_strategy_redis(bBandsPeriod, instrument, startPortfolio, startdate, enddate, filterCriteria=20, indicators=True):

    feed = redis_build_feed_EOD(instrument, startdate, enddate)
    #feed = build_feed_TN(instrument, startdate, enddate)
    #feed = yahoofinance.build_feed([instrument], 2012, 2014, ".")

    # Add the SPY bars, which are used to determine if the market is Bullish or Bearish
    # on a particular day.
    feed = add_feeds_EOD_redis(feed, 'SPY', startdate, enddate)

    ###Get earnings calendar
    calList = getEarningsCal(instrument)

    strat = BB_spread.BBSpread(feed, instrument, bBandsPeriod, calList, startPortfolio)

    instList = [instrument, 'SPY']

    if indicators:
        # Attach a returns analyzers to the strategy.
        returnsAnalyzer = Returns()
        results = StrategyResults(strat, instList, returnsAnalyzer, plotSignals=True)

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

        ####Populate orders from the backtest run...
        #filteredOrders = getOrdersFiltered(strat.getOrders(), instrument, filterCriteria = 20)
        results.addOrders(strat.getOrders())
        #results.addOrders(filteredOrders)
       

        results.addSeries("upper", strat.getBollingerBands().getUpperBand())
        results.addSeries("middle", strat.getBollingerBands().getMiddleBand())
        results.addSeries("lower", strat.getBollingerBands().getLowerBand())
        results.addSeries("RSI", strat.getRSI())
        results.addSeries("EMA Fast", strat.getEMAFast())
        results.addSeries("EMA Slow", strat.getEMASlow())
        results.addSeries("EMA Signal", strat.getEMASignal())
        #results.addSeries("macd", strat.getMACD())
        return results
    else:
        # This is to ensue we consume less memory on the portfolio simulation case ... main thread.......
        returnsAnalyzer = Returns()
        results = StrategyResults(strat, instList, returnsAnalyzer, plotSignals=False)
        strat.run()
        if filterCriteria == 10000:
            orders = strat.getOrders()
        else:
            orders = getOrdersFiltered(strat.getOrders(), instrument, filterCriteria)
            #orders = getOrdersFilteredByRules(strat.getOrders(), instrument)
            
        return orders
    
    #return results
    

def run_strategy_TN(bBandsPeriod, instrument, startPortfolio, startdate, enddate):

    #feed = redis_build_feed_EOD(instrument, startdate, enddate)
    feed = build_feed_TN(instrument, startdate, enddate)
    #feed = yahoofinance.build_feed([instrument], 2012, 2014, ".")

    # Add the SPY bars, which are used to determine if the market is Bullish or Bearish
    # on a particular day.
    feed = add_feeds_TN(feed, 'SPY', startdate, enddate)

    ###Get earnings calendar
    calList = getEarningsCal(instrument)

    strat = BB_spread.BBSpread(feed, instrument, bBandsPeriod, calList, startPortfolio)

    instList = [instrument, 'SPY']

    # Attach a returns analyzers to the strategy.
    returnsAnalyzer = Returns()
    results = StrategyResults(strat, instList, returnsAnalyzer, plotSignals=True)

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

    ####Populate orders from the backtest run...
    results.addOrders(strat.getOrders())

    results.addSeries("upper", strat.getBollingerBands().getUpperBand())
    results.addSeries("middle", strat.getBollingerBands().getMiddleBand())
    results.addSeries("lower", strat.getBollingerBands().getLowerBand())
    results.addSeries("RSI", strat.getRSI())
    results.addSeries("EMA Fast", strat.getEMAFast())
    results.addSeries("EMA Slow", strat.getEMASlow())
    results.addSeries("EMA Signal", strat.getEMASignal())
    #results.addSeries("macd", strat.getMACD())
    
    return results

def run_master_strategy(initialcash, masterFile):

    ordersFile = Orders_exec.OrdersFile(masterFile, fakecsv=True)
    startdate = datetime.datetime.fromtimestamp(ordersFile.getFirstDate())
    enddate = datetime.datetime.fromtimestamp(ordersFile.getLastDate())
    print startdate, enddate

    #### Instruments in the order file...
    instList = ordersFile.getInstruments()
   
    feed = None
    #### Provide bars for all the instruments in the strategy...
    for instrument in ordersFile.getInstruments():
        if feed is None:
            feed = redis_build_feed_EOD(instrument, startdate, enddate)
        else:
            feed = add_feeds_EOD_redis(feed, instrument, startdate, enddate)

        
    useAdjustedClose = True
    myStrategy = Orders_exec.MyStrategy(feed, initialcash, ordersFile, useAdjustedClose)

    returnsAnalyzer = Returns()
    results = StrategyResults( myStrategy, instList, returnsAnalyzer)

    myStrategy.run()

    return results

    