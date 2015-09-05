import pyalgotrade.broker 
from pyalgotrade.barfeed import membf
from pyalgotrade.technical import ma
from utils import util
import xiquantFuncs
import BB_spread
import BB_SMA_xover_mtm
import EMA_breach_mtm
import Orders_exec
import datetime
import json
import csv
import dateutil.parser
import os
from pyalgotrade.stratanalyzer import returns
from pyalgotrade import dataseries
import time
import calendar
from pyalgotrade import bar
import collections
from pyalgotrade.bar import BasicBar, Frequency
import math



import xiquantPlatform


####=========================================================================================================################
#######            Special methods for pickle/serialization support any instance methods....
########======================================================================================================###############

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



####=========================================================================================================################
#######            Classes override/extended pyalgo base calsses to support BBSpread strategy...
########======================================================================================================###############


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
        seconds = calendar.timegm(bars.getDateTime().timetuple())
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
                #adjPrice_val = [dtInMilliSeconds, bar_val.getOpen(), bar_val.getHigh(), \
                #       bar_val.getLow(), bar_val.getAdjClose()]
                adjPrice_val = [dtInMilliSeconds, bar_val.getOpen(), bar_val.getHigh(), \
                        bar_val.getLow(), bar_val.getClose()]
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
                seconds = calendar.timegm(execInfo.getDateTime().timetuple())
                if action == pyalgotrade.broker.Order.Action.BUY:
                    val = {'x':int(seconds * 1000), 'title': 'B', 'text': 'Bought: ' + str(order.getInstrument()) +'  Shares: ' + str(order.getQuantity()) + " Price " +  str(execInfo.getPrice())}
                else:
                    val = {'x':int(seconds * 1000), 'title': 'CB', 'text': 'Cover Buy: ' + str(order.getInstrument()) +'  Shares: ' + str(order.getQuantity()) + " Price " +  str(execInfo.getPrice())}

                #val = {'x':int(seconds * 1000), 'title': 'B', 'text': 'Bought: ' + str(order.getInstrument()) +'  Shares: ' + str(order.getQuantity()) + " Price " +  str(execInfo.getPrice())}
                self.__tradeDetails.append(val)
            elif action in [pyalgotrade.broker.Order.Action.SELL, pyalgotrade.broker.Order.Action.SELL_SHORT]:
                #self.getSeries("Sell", SellMarker).addValue(execInfo.getDateTime(), execInfo.getPrice())
                #print "SELL: ", execInfo.getDateTime(), execInfo.getPrice()
                seconds = calendar.timegm(execInfo.getDateTime().timetuple())
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
        #for x in range(len(dateList)):
        dtIndex = -1
        for x in reversed(seq_data):
            dt =  dateList[dtIndex]
            sec = calendar.timegm(dt.timetuple())
            #val = [int(sec * 1000), seq_data.getValueAbsolute(x)]
            ############## This is to avoid JSON Parser not able to deal with double.NaN's...
            if math.isnan(x):
                pass #### Do nothing
            else:
                val = [int(sec * 1000), x]
                dataseries.append(val)
            dtIndex = dtIndex - 1
        return list(reversed(dataseries))

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
            sec = calendar.timegm(dt.timetuple())
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
            sec = calendar.timegm(dt.timetuple())
            val = [int(sec * 1000), returns.getValueAbsolute(x)]
            dataseries.append(val)
        return dataseries

class Feed(membf.BarFeed):

    def __init__(self, frequency, maxLen=1024):
        membf.BarFeed.__init__(self, frequency, maxLen)
        self.__barSeries = {}

    def barsHaveAdjClose(self):
        return True

    def loadBars(self, instrument, bars):
        self.addBarsFromSequence(instrument, bars) #### this is for raw values...
        self.__barSeries[instrument] = bars

    def getBarSeries(self, instrument):
        return self.__barSeries[instrument]

class xiQuantBasicBar(bar.BasicBar):
    def __init__(self, dateTime, open_, high, low, close, volume, adjClose, frequency, dividend, split):
        bar.BasicBar.__init__(self, dateTime, open_, high, low, close, volume, adjClose, frequency)
        self.__dividend = dividend
        self.__split = split

    def getDividend(self):
        return self.__dividend

    def getSplit(self):
        return self.__split

class Returns(returns.Returns):
     def __init__(self):
        #returns.Returns.__init__(self)
        self.__netReturns = dataseries.SequenceDataSeries()
        self.__netReturns.setMaxLen(5000)
        self.__cumReturns = dataseries.SequenceDataSeries()
        self.__cumReturns.setMaxLen(5000)


def adjustBars(instrument, bars, startdate, enddate):

    bars = []
    bars_in_dtrange = [bar for bar in bars if startdate.replace(tzinfo=None) <= bar.getDateTime() <= enddate.replace(tzinfo=None)]
    bars_in_dtrange.sort(key=lambda bar: bar.getDateTime(), reverse=True)
    k = 0
    splitdataList = []
    dividendList = []
    for bar in bars_in_dtrange:
        splitdata = bar.getSplit()
        dividend = bar.getDividend()
        if splitdata != 1.0:
            splitdataList.append(bar.getSplit())
        if dividend != 0.0:
            adjFactor = (bar.getClose() + bar.getDividend()) / bar.getClose()
            dividendList.append(adjFactor)
        #### Special case.... end date / analysis date nothing to do..
        if (k==0):
            bar = BasicBar(bar.getDateTime(), 
                    bar.getOpen() , bar.getHigh(), bar.getLow(), bar.getClose(), bar.getVolume(), bar.getClose(), Frequency.DAY)
            bars.append(bar)
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

            bar = BasicBar(bar.getDateTime(), 
                    Open , High, Low, Close, Volume, Close, Frequency.DAY)
            bars.append(bar)
        k +=1
        feed = Feed(Frequency.DAY, 1024)
        return feed.loadBars(instrument+"_adjusted", bars)
    


####=========================================================================================================################
#######            Helper methods related to running BBSpread strategy.....
########======================================================================================================###############
       

def ADR(ticker,nDays, date):
    adr_series = redis_build_ADR_ndays(ticker, nDays, (date - datetime.timedelta(days=10)), date)
    return adr_series[-1]

### Average Daily range....
def redis_build_ADR_ndays(ticker, nDays, stdate, enddate):
    import datetime
    from pyalgotrade.utils import dt

    ###### Please note zrangebyscore returns between values the scores to make it include both start date and end date as part of
    ######## data series we need to do date arithmetic on passed in data ################
    stdate, enddate = util.getRedisEffectiveDates(stdate, enddate)

    seconds = calendar.timegm(stdate.timetuple())
    seconds2 = calendar.timegm(enddate.timetuple())
    data_dict = {}
    try:
        redisConn = util.get_redis_conn()
        ticker_data = redisConn.zrangebyscore(ticker + ":EODRAW", int(seconds), int(seconds2), 0, -1, True)
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

        seconds = calendar.timegm(datetime.datetime.fromtimestamp(timestamp).timetuple())
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
    from pyalgotrade.utils import dt

    ###### Please note zrangebyscore returns between values the scores to make it include both start date and end date as part of
    ######## data series we need to do date arithmetic on passed in data ################
    stdate, enddate = util.getRedisEffectiveDates(stdate, enddate)

    seconds = calendar.timegm(stdate.timetuple())
    seconds2 = calendar.timegm(enddate.timetuple())
    data_dict = {}
    try:
        redisConn = util.get_redis_conn()
        ticker_data = redisConn.zrangebyscore(ticker + ":EODRAW", int(seconds), int(seconds2), 0, -1, True)
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

        seconds = calendar.timegm(datetime.datetime.fromtimestamp(timestamp).timetuple())
        data_point.append(int(seconds)*1000)
        data_point.append(Avg/nDays)
        sma_ndays.append(data_point)
        i +=1
        j +=1
    return sma_ndays

def redis_build_sma_3days(ticker, stdate, enddate):
    import datetime
    from pyalgotrade.utils import dt


    ###### Please note zrangebyscore returns between values the scores to make it include both start date and end date as part of
    ######## data series we need to do date arithmetic on passed in data ################
    stdate, enddate = util.getRedisEffectiveDates(stdate, enddate)

    seconds = calendar.timegm(stdate.timetuple())
    seconds2 = calendar.timegm(enddate.timetuple())
    data_dict = {}
    try:
        redisConn = util.get_redis_conn()
        ticker_data = redisConn.zrangebyscore(ticker + ":EODRAW", int(seconds), int(seconds2), 0, -1, True)
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

def tickersRankByCashFlow(date, sortOrder='Reverse'):
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

    seconds = calendar.timegm(startdate.timetuple())
    seconds2 = calendar.timegm(enddate.timetuple())
    data_dict = {}
    try:
        redisConn = util.get_redis_conn()
        ticker_data = redisConn.zrangebyscore(ticker + ":EODRAW", int(seconds), int(seconds2), 0, -1, True)
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
        keyList = keys[i:j]
        priceList = []
        volumeList = []
        for key in keyList:
            data = data_dict[key].split("|")
            priceList.append(float(data[3]))
            volumeList.append(float(data[4]))

        cashflow =  (priceList[1] - priceList[0]) * volumeList[1]
        seconds = calendar.timegm(datetime.datetime.fromtimestamp(timestamp).timetuple())
        data_point.append(int(seconds)*1000)
        data_point.append(cashflow)
        cashflow_accum.append(data_point)
        i +=1
        j +=1

    return cashflow_accum

def cashflow_timeseries_percentChange(instrument, startdate, enddate):

    from pyalgotrade.talibext import indicator

    mfiDS = []

    try:
        feed = redis_build_feed_EOD_RAW(instrument, startdate, enddate)
        barsDictForCurrAdj = {}
        barsDictForCurrAdj[instrument] = feed.getBarSeries(instrument)
        feedLookbackEndAdj = xiquantPlatform.xiQuantAdjustBars(barsDictForCurrAdj, startdate, enddate)
        feedLookbackEndAdj.adjustBars()
        barDS = feedLookbackEndAdj.getBarSeries(instrument + "_adjusted")
        mfi = indicator.MFI(barDS, len(barDS), 3)
        dateTimes = feedLookbackEndAdj.getDateTimes(instrument + "_adjusted")
        mfiDS = numpy_to_highchartds(dateTimes, mfi, startdate, enddate)
    except Exception,e: 
        pass

    return mfiDS

    '''
    cfPercentSeries = []
    i = 1
    while i < len(mfiDS):
        mfiPercentChange = ((mfiDS[i][1] - mfiDS[i-1][1]) / mfiDS[i-1][1]) * 100
        val = [mfiDS[i][0], mfiPercentChange]
        cfPercentSeries.append(val)
        i += 1
    return cfPercentSeries
    '''


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


####=========================================================================================================################
#######            Methods related to BB_SPread strategy..........
########======================================================================================================###############

####################### Populate momentum rank field ########################################################################

##### topNMomentum stocks ..............
def updateOrdersRankbyMoneyFlowPercentChange(orders, instrument):
    from pyalgotrade.talibext import indicator

    updatedOrders = {}
    for key, value in orders.iteritems():

        if value[0][1] == 'Buy' or value[0][1] == 'Sell':
           
            dt = datetime.datetime.fromtimestamp(key) + datetime.timedelta(days=1)
            dt0 = dt - datetime.timedelta(days=30)

            '''
            cfData = cashflow_timeseries_TN(instrument, dt0, dt)
            cfPercentChange = float((cfData[-1][1] - cfData[-2][1])/(cfData[-2][1])) 
            rank = cfPercentChange * 100.0
            '''

            feed = redis_build_feed_EOD_RAW(instrument, dt0, dt)
            barsDictForCurrAdj = {}
            barsDictForCurrAdj[instrument] = feed.getBarSeries(instrument)
            feedLookbackEndAdj = xiquantPlatform.xiQuantAdjustBars(barsDictForCurrAdj, dt0, dt)
            feedLookbackEndAdj.adjustBars()
            barDS = feedLookbackEndAdj.getBarSeries(instrument + "_adjusted")
            #mfi = indicator.MFI(barDS, len(barDS), 3)
            print "*******************++++++++++++++++++++================:", barDS[-1].getDateTime(), barDS[-1].getClose(), barDS[-1].getVolume()
            #mfiDSPercentChange = float((mfi[-1] - mfi[-2]) / (mfi[-2]))
            analysisDayMoneyFlow = barDS[-1].getClose() *  barDS[-1].getVolume()
            previousDayMoneyFlow = barDS[-2].getClose() *  barDS[-2].getVolume()
            cfPercentChange =  ((analysisDayMoneyFlow - previousDayMoneyFlow)/(previousDayMoneyFlow)) * 100.0

            if value[0][1] == 'Buy':
                if cfPercentChange >= 20.0:
                    rank = 10
                else:
                    rank = 10000
            else:
                if cfPercentChange <= -20.0:
                    rank = 10
                else:
                    rank = 10000
    
            ### update rank based on cashflow for BUY and SELL orders...
            newval = []
            #newval.append((value[0][0], value[0][1], value[0][2], rank))
            newval.append((value[0][0], value[0][1], value[0][2], value[0][3], rank))
            ########## Please note we are just appending relevant cashflow ranks and relevant filter rules will be applied 
            ########## during portfolio simulation rules...
            updatedOrders[key] = newval
        else:
            updatedOrders[key] = value

    return updatedOrders



    


def updateOrdersRank(orders, instrument):
    updatedOrders = {}
    for key, value in orders.iteritems():

        if value[0][1] == 'Buy' or value[0][1] == 'Sell':
           
            dt = datetime.datetime.fromtimestamp(key)
            seconds = calendar.timegm(dt.timetuple()) #### please note you need to get money flow of the one day before......
            keyString = int(seconds)*1000
            rediskey = "cashflow:"+str(keyString)
            redisConn = util.get_redis_conn()
            if value[0][1] == 'Buy':
                rank = redisConn.zrevrank(rediskey, instrument) 
            else:
                rank = redisConn.zrank(rediskey, instrument) 
            ### update rank based on cashflow for BUY and SELL orders...
            newval = []
            #newval.append((value[0][0], value[0][1], value[0][2], rank))
            newval.append((value[0][0], value[0][1], value[0][2], value[0][3], rank))
            ########## Please note we are just appending relevant cashflow ranks and relevant filter rules will be applied 
            ########## during portfolio simulation rules...
            updatedOrders[key] = newval
        else:
            updatedOrders[key] = value

    return updatedOrders

##### Orders filtered by momentum rank....
def getOrdersFiltered(orders, instrument, filterCriteria=20):

    #orders = getOrdersFilteredByRules(orders, instrument) ##### Please note this is to filter orders based on ADR Cashflow etc...
    filteredOrders = {}
    
    for key, value in orders.iteritems():

        if value[0][1] == 'Buy' or value[0][1] == 'Sell':
           
            dt = datetime.datetime.fromtimestamp(key)
            seconds = calendar.timegm(dt.timetuple()) #### please note you need to get money flow of the one day before......
            keyString = int(seconds)*1000
            rediskey = "cashflow:"+str(keyString)
            redisConn = util.get_redis_conn()
            if value[0][1] == 'Buy':
                rank = redisConn.zrevrank(rediskey, instrument) 
            else:
                rank = redisConn.zrank(rediskey, instrument) 
            ### update rank based on cashflow for BUY and SELL orders...
            newval = []
            newval.append((value[0][0], value[0][1], value[0][2], rank))
            ########## Please note we are just appending relevant cashflow ranks and relevant filter rules will be applied 
            ########## during portfolio simulation rules...
            if filterCriteria < 20:
                filteredOrders[key] = newval
            else:
                if rank <= filterCriteria:
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
                #if (ADR_5days[1] >=1) and (vol_5days[1] >= 1000000) and mf[1] >= 2000000:
                if mf[1] >= 2000000 and value[0][1] == 'Buy':
                    print "Data:  ", dt, ADR_5days, vol_5days, mf
                    filteredOrders[key] = newval
                elif mf[1] <= -2000000 and value[0][1] == 'Sell':
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


def numpy_to_highchartds(datetimes, data, startdate, enddate):
    dataseries = []
    dateList = list(datetimes)
    dateList.sort()
    dtIndex = -1
    for x in reversed(data):
        dt = dateList[dtIndex]
        sec = calendar.timegm(dt.timetuple())
        if math.isnan(x):
            pass #### Do nothing
        else:
            val = [int(sec * 1000), x]
            dataseries.append(val)
        dtIndex = dtIndex - 1

    return list(reversed(dataseries))


def compute_BBands(instrument, startdate, enddate ):
    from pyalgotrade.talibext import indicator

    bBandsPeriod = 20 #### No of periods.....
    feed = redis_build_feed_EOD_RAW(instrument, startdate, enddate)
    barsDictForCurrAdj = {}
    barsDictForCurrAdj[instrument] = feed.getBarSeries(instrument)
    feedLookbackEndAdj = xiquantPlatform.xiQuantAdjustBars(barsDictForCurrAdj, startdate, enddate)
    feedLookbackEndAdj.adjustBars()
    closeDS = feedLookbackEndAdj.getCloseDataSeries(instrument + "_adjusted")
    upper, middle, lower = indicator.BBANDS(closeDS, len(closeDS), bBandsPeriod, 2.0, 2.0)

    dateTimes = feedLookbackEndAdj.getDateTimes(instrument + "_adjusted")
    upperDS = numpy_to_highchartds(dateTimes, upper, startdate, enddate)
    middleDS = numpy_to_highchartds(dateTimes, middle, startdate, enddate)
    lowerDS = numpy_to_highchartds(dateTimes, lower, startdate, enddate)

    ##########Display price seriesin the center of Bolinger bands......##################
    barDS = feedLookbackEndAdj.getBarSeries(instrument + "_adjusted")
    adj_Close_Series = []
    for bar in barDS:
        dt = bar.getDateTime()
        sec = calendar.timegm(dt.timetuple())
        dtInMilliSeconds = int(sec * 1000)
        adjPrice_val = [dtInMilliSeconds, bar.getOpen(), bar.getHigh(), \
                        bar.getLow(), bar.getClose()]
        adj_Close_Series.append(adjPrice_val)


    return upperDS, middleDS, lowerDS, adj_Close_Series

def compute_SMA(instrument, startdate, enddate ):
    from pyalgotrade.talibext import indicator

    noOfPeriods = 20 #### No of periods.....
    feed = redis_build_feed_EOD_RAW(instrument, startdate, enddate)
    barsDictForCurrAdj = {}
    barsDictForCurrAdj[instrument] = feed.getBarSeries(instrument)
    feedLookbackEndAdj = xiquantPlatform.xiQuantAdjustBars(barsDictForCurrAdj, startdate, enddate)
    feedLookbackEndAdj.adjustBars()
    closeDS = feedLookbackEndAdj.getCloseDataSeries(instrument + "_adjusted")
    sma_20 = indicator.SMA(closeDS, len(closeDS), noOfPeriods)

    dateTimes = feedLookbackEndAdj.getDateTimes(instrument + "_adjusted")
    smaDS = numpy_to_highchartds(dateTimes, sma_20, startdate, enddate)
    
    ##########Display price seriesin the center of Bolinger bands......##################
    barDS = feedLookbackEndAdj.getBarSeries(instrument + "_adjusted")
    adj_Close_Series = []
    for bar in barDS:
        dt = bar.getDateTime()
        sec = calendar.timegm(dt.timetuple())
        dtInMilliSeconds = int(sec * 1000)
        adjPrice_val = [dtInMilliSeconds, bar.getOpen(), bar.getHigh(), \
                        bar.getLow(), bar.getClose()]
        adj_Close_Series.append(adjPrice_val)


    return smaDS, adj_Close_Series

def compute_EMA(instrument, startdate, enddate ):
    from pyalgotrade.talibext import indicator

    noOfPeriods = 10 #### No of periods.....
    feed = redis_build_feed_EOD_RAW(instrument, startdate, enddate)
    barsDictForCurrAdj = {}
    barsDictForCurrAdj[instrument] = feed.getBarSeries(instrument)
    feedLookbackEndAdj = xiquantPlatform.xiQuantAdjustBars(barsDictForCurrAdj, startdate, enddate)
    feedLookbackEndAdj.adjustBars()
    closeDS = feedLookbackEndAdj.getCloseDataSeries(instrument + "_adjusted")
    ema_10 = indicator.SMA(closeDS, len(closeDS), noOfPeriods)

    dateTimes = feedLookbackEndAdj.getDateTimes(instrument + "_adjusted")
    emaDS = numpy_to_highchartds(dateTimes, ema_10, startdate, enddate)
    
    ##########Display price seriesin the center of Bolinger bands......##################
    barDS = feedLookbackEndAdj.getBarSeries(instrument + "_adjusted")
    adj_Close_Series = []
    for bar in barDS:
        dt = bar.getDateTime()
        sec = calendar.timegm(dt.timetuple())
        dtInMilliSeconds = int(sec * 1000)
        adjPrice_val = [dtInMilliSeconds, bar.getOpen(), bar.getHigh(), \
                        bar.getLow(), bar.getClose()]
        adj_Close_Series.append(adjPrice_val)

    return emaDS, adj_Close_Series


def computeIndicators(instrument, indicator, startdate, enddate ):
    if indicator == 'BBands':
        return compute_BBands(instrument, startdate, enddate)
    if indicator == 'SMA-20':
        return compute_SMA(instrument,  startdate, enddate)
    if indicator == 'EMA-10':
        return compute_EMA(instrument,  startdate, enddate)
    

    

def run_strategy_redis(bBandsPeriod, instrument, startPortfolio, startdate, enddate, filterCriteria=20, indicators=True):

    
    feed = redis_build_feed_EOD_RAW(instrument, startdate, enddate)
    # Add the SPY bars, which are used to determine if the market is Bullish or Bearish
    # on a particular day.
    feed = add_feeds_EOD_redis_RAW(feed, 'SPY', startdate, enddate)
    feed = add_feeds_EOD_redis_RAW(feed, 'QQQ', startdate, enddate)
    

    ###Get earnings calendar
    calList = getEarningsCal(instrument)

    barsDictForCurrAdj = {}
    barsDictForCurrAdj[instrument] = feed.getBarSeries(instrument)
    barsDictForCurrAdj['SPY'] = feed.getBarSeries('SPY')
    barsDictForCurrAdj['QQQ'] = feed.getBarSeries('QQQ')
    feedAdjustedToEndDate = xiquantPlatform.adjustBars(barsDictForCurrAdj, startdate, enddate)


    strat = BB_spread.BBSpread(feedAdjustedToEndDate, feed, instrument, bBandsPeriod, calList, startPortfolio)

    instList = [instrument+"_adjusted", 'SPY'+"_adjusted", 'QQQ'+"_adjusted"]

    if indicators:
        # Attach a returns analyzers to the strategy.
        returnsAnalyzer = Returns()
        results = StrategyResults(strat, instList, returnsAnalyzer, plotSignals=True)

        ###Initialize the bands to maxlength of 5000 for 10 years backtest..
        #strat.getBollingerBands().getMiddleBand().setMaxLen(5000)
        #strat.getBollingerBands().getUpperBand().setMaxLen(5000)
        #strat.getBollingerBands().getLowerBand().setMaxLen(5000) 
        #strat.getRSI().setMaxLen(5000)
        #strat.getEMAFast().setMaxLen(5000)
        #strat.getEMASlow().setMaxLen(5000)
        #strat.getEMASignal().setMaxLen(5000)
        #### Add boilingerbands series....
        strat.run()

        ####Populate orders from the backtest run...
        results.addOrders(strat.getOrders())
        results.addSeries("upper", strat.getUpperBollingerBands())
        results.addSeries("middle", strat.getMiddleBollingerBands())
        results.addSeries("lower", strat.getLowerBollingerBands())
        results.addSeries("RSI", strat.getRSI())
        results.addSeries("EMA Fast", strat.getEMAFast())
        results.addSeries("EMA Slow", strat.getEMASlow())
        results.addSeries("EMA Signal", strat.getEMASignal())
        return results
    else:
        # This is to ensue we consume less memory on the portfolio simulation case ... main thread.......
        returnsAnalyzer = Returns()
        results = StrategyResults(strat, instList, returnsAnalyzer, plotSignals=False)
        strat.run()
        updatedOrders = updateOrdersRank(strat.getOrders(), instrument)

        return updatedOrders



def run_master_strategy(initialcash, masterFile, startdate, enddate, filterAction='Both', rank=10000):

    #ordersFile = Orders_exec.OrdersFile(masterFile, fakecsv=True)

    filePath = os.path.join(os.path.dirname(__file__), masterFile)
    ordersFile = Orders_exec.OrdersFile(filePath, filterAction, rank)
    #startdate = datetime.datetime.fromtimestamp(ordersFile.getFirstDate()) - datetime.timedelta(days=1)
    #enddate = datetime.datetime.fromtimestamp(ordersFile.getLastDate()) +  datetime.timedelta(days=1)
    #enddate = dateutil.parser.parse('2014-12-31T08:00:00.000Z')
    print startdate, enddate

    #### Instruments in the order file...
    instList = ordersFile.getInstruments()
   
    feed = None
    #### Provide bars for all the instruments in the strategy...
    for instrument in ordersFile.getInstruments():
        if feed is None:
            feed = redis_build_feed_EOD_RAW(instrument, startdate, enddate)
        else:
            feed = add_feeds_EOD_redis_RAW(feed, instrument, startdate, enddate)

    # Add the SPY bars to support the simulation of whether we should have
    # entered certain trades or not -- based on the SPY opening higher/lower
    # than 20 SMA value for bullish/bearish trades.
    feed = add_feeds_EOD_redis_RAW(feed, 'SPY', startdate, enddate)

    barsDictForCurrAdj = {}
    for instrument in ordersFile.getInstruments():
        barsDictForCurrAdj[instrument] = feed.getBarSeries(instrument)
    barsDictForCurrAdj['SPY'] = feed.getBarSeries('SPY')
    feedAdjustedToEndDate = xiquantPlatform.adjustBars(barsDictForCurrAdj, startdate, enddate, keyFlag=False)

    cash = 100000
    useAdjustedClose = True
    myStrategy = Orders_exec.MyStrategy(feedAdjustedToEndDate, initialcash, ordersFile, useAdjustedClose)

    returnsAnalyzer = Returns()
    results = StrategyResults( myStrategy, instList, returnsAnalyzer)

    myStrategy.run()

    return results



def run_strategy_BBSMAXOverMTM(bBandsPeriod, instrument, startPortfolio, startdate, enddate, filterCriteria=20, indicators=True):

    
    feed = redis_build_feed_EOD_RAW(instrument, startdate, enddate)
    # Add the SPY bars, which are used to determine if the market is Bullish or Bearish
    # on a particular day.
    feed = add_feeds_EOD_redis_RAW(feed, 'SPY', startdate, enddate)
    feed = add_feeds_EOD_redis_RAW(feed, 'QQQ', startdate, enddate)
    

    ###Get earnings calendar
    calList = getEarningsCal(instrument)

    barsDictForCurrAdj = {}
    barsDictForCurrAdj[instrument] = feed.getBarSeries(instrument)
    barsDictForCurrAdj['SPY'] = feed.getBarSeries('SPY')
    barsDictForCurrAdj['QQQ'] = feed.getBarSeries('QQQ')
    feedAdjustedToEndDate = xiquantPlatform.adjustBars(barsDictForCurrAdj, startdate, enddate)

    strat = BB_SMA_xover_mtm.BBSMAXOverMTM(feedAdjustedToEndDate, feed, instrument, bBandsPeriod, calList, startPortfolio)

    instList = [instrument+"_adjusted", 'SPY'+"_adjusted", 'QQQ'+"_adjusted"]

    if indicators:
        # Attach a returns analyzers to the strategy.
        returnsAnalyzer = Returns()
        results = StrategyResults(strat, instList, returnsAnalyzer, plotSignals=True)
        strat.run()

        ####Populate orders from the backtest run...
        results.addOrders(strat.getOrders())
        results.addSeries("upper", strat.getUpperBollingerBands())
        results.addSeries("middle", strat.getMiddleBollingerBands())
        results.addSeries("lower", strat.getLowerBollingerBands())
        return results
    else:
        # This is to ensue we consume less memory on the portfolio simulation case ... main thread.......
        returnsAnalyzer = Returns()
        results = StrategyResults(strat, instList, returnsAnalyzer, plotSignals=False)
        strat.run()

        updatedOrders = updateOrdersRank(strat.getOrders(), instrument)

        return updatedOrders

def run_strategy_EMABreachMTM(bBandsPeriod, instrument, startPortfolio, startdate, enddate, filterCriteria=20, indicators=True):

    
    feed = redis_build_feed_EOD_RAW(instrument, startdate, enddate)
    # Add the SPY bars, which are used to determine if the market is Bullish or Bearish
    # on a particular day.
    feed = add_feeds_EOD_redis_RAW(feed, 'SPY', startdate, enddate)
    feed = add_feeds_EOD_redis_RAW(feed, 'QQQ', startdate, enddate)
    

    ###Get earnings calendar
    calList = getEarningsCal(instrument)

    barsDictForCurrAdj = {}
    barsDictForCurrAdj[instrument] = feed.getBarSeries(instrument)
    barsDictForCurrAdj['SPY'] = feed.getBarSeries('SPY')
    barsDictForCurrAdj['QQQ'] = feed.getBarSeries('QQQ')
    feedAdjustedToEndDate = xiquantPlatform.adjustBars(barsDictForCurrAdj, startdate, enddate)

    strat = EMA_breach_mtm.EMABreachMTM(feedAdjustedToEndDate, feed, instrument, bBandsPeriod, calList, startPortfolio)

    instList = [instrument+"_adjusted", 'SPY'+"_adjusted", 'QQQ'+"_adjusted"]

    if indicators:
        # Attach a returns analyzers to the strategy.
        returnsAnalyzer = Returns()
        results = StrategyResults(strat, instList, returnsAnalyzer, plotSignals=True)
        strat.run()

        ####Populate orders from the backtest run...
        results.addOrders(strat.getOrders())
        results.addSeries("upper", strat.getUpperBollingerBands())
        results.addSeries("middle", strat.getMiddleBollingerBands())
        results.addSeries("lower", strat.getLowerBollingerBands())
        return results
    else:
        # This is to ensue we consume less memory on the portfolio simulation case ... main thread.......
        returnsAnalyzer = Returns()
        results = StrategyResults(strat, instList, returnsAnalyzer, plotSignals=False)
        strat.run()

        updatedOrders = updateOrdersRank(strat.getOrders(), instrument)

        return updatedOrders

####=========================================================================================================################
#######            Methods related to OHLC EODRAW values....
########======================================================================================================###############


def redis_listoflists_to_dict(redis_list):
    list_values, list_keys = zip(*redis_list)
    return dict(zip(list_keys, list_values))

    
def redis_build_feed_EOD_RAW(ticker, stdate, enddate):
    from pyalgotrade.bar import BasicBar, Frequency

    feed = Feed(Frequency.DAY, 1024)
    return add_feeds_EOD_redis_RAW(feed, ticker, stdate, enddate)
    #return add_feeds_EODRAW_CSV(feed, ticker, stdate, enddate)


def add_feeds_EOD_redis_RAW( feed, ticker, stdate, enddate):
    import datetime
    from pyalgotrade.utils import dt
    from pyalgotrade.bar import BasicBar, Frequency

    ###### Please note zrangebyscore returns between values the scores to make it include both start date and end date as part of
    ######## data series we need to do date arithmetic on passed in data ################
    stdate, enddate = util.getRedisEffectiveDates(stdate, enddate)

    seconds = calendar.timegm(stdate.timetuple())
    seconds2 = calendar.timegm(enddate.timetuple())

    data_dict = {}
    try:
        redisConn = util.get_redis_conn()
        ### added EOD as data source
        ticker_data = redisConn.zrangebyscore(ticker + ":EODRAW", int(seconds), int(seconds2), 0, -1, True)
        data_dict = redis_listoflists_to_dict(ticker_data)
    except Exception,e:
        print str(e)
        pass

    bd = [] ##### initialize bar data.....
    for key in data_dict:
        #dateTime = dt.timestamp_to_datetime(key)
        dateTime = dt.timestamp_to_datetime(key).replace(tzinfo=None) 
        data = data_dict[key].split("|") ### split pipe delimted values
        bar = xiQuantBasicBar(dateTime, float(data[0]) , float(data[1]), float(data[2]), float(data[3]), float(data[4]), float(data[5]), Frequency.DAY,float(data[6]), float(data[7]))

        bd.append(bar)
    #feed = Feed(Frequency.DAY, 1024)
    feed.loadBars(ticker, bd)
    return feed

'''
def add_feeds_EODRAW_CSV(feed, ticker, stdate, enddate):
    import datetime
    from pyalgotrade.utils import dt
    from pyalgotrade.bar import BasicBar, Frequency
    import csv
    import dateutil.parser
    import os


    bd = [] ##### initialize bar data.....
    file_EODRAW = os.path.join(os.path.dirname(__file__), ticker+'_EODRAW.csv')
    with open(file_EODRAW, 'rU') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            dateTime = dateutil.parser.parse(row['Date'])
            ### Let's only populate the dates passed in the feed...
            if dateTime.date() <= enddate.date() and dateTime.date() >= stdate.date() :
                bar = xiQuantBasicBar(dateTime, 
                float(row['Open']) , float(row['High']), float(row['Low']), float(row['Close']), float(row['Volume']), float(row['AdjClose']), Frequency.DAY, float(row['Dividend']), float(row['Split']) )
                bd.append(bar)
    feed.loadBars(ticker, bd)
    return feed
'''


####=========================================================================================================################
#######            Methods related to Options processing files............
########======================================================================================================###############

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