from pyalgotrade import strategy
from pyalgotrade.barfeed import yahoofeed
from pyalgotrade.technical import ma, rsi

import datetime
import redis
from time import mktime
import urlparse
import os
from pyalgotrade.bar import BasicBar, Frequency
from pyalgotrade.barfeed import membf
from pyalgotrade.utils import dt
from pyalgotrade.stratanalyzer import returns
from strategy_results import StrategyResults
from pyalgotrade.technical import cross


class SMACrossOver(strategy.BacktestingStrategy):
    def __init__(self, feed, instrument, amount, smaPeriod):
        strategy.BacktestingStrategy.__init__(self, feed, amount)
        self.__instrument = instrument
        self.__position = None
        # We'll use adjusted close values instead of regular close values.
        self.setUseAdjustedValues(True)
        self.__prices = feed[instrument].getPriceDataSeries()
        self.__sma = ma.SMA(self.__prices, smaPeriod)

    def getSMA(self):
        return self.__sma

    def onEnterCanceled(self, position):
        self.__position = None

    def onExitOk(self, position):
        self.__position = None

    def onExitCanceled(self, position):
        # If the exit was canceled, re-submit it.
        self.__position.exitMarket()

    def onBars(self, bars):
        # If a position was not opened, check if we should enter a long position.
        if self.__position is None:
            if cross.cross_above(self.__prices, self.__sma) > 0:
                shares = int(self.getBroker().getCash() * 0.9 / bars[self.__instrument].getPrice())
                # Enter a buy market order. The order is good till canceled.
                self.__position = self.enterLong(self.__instrument, shares, True)
        # Check if we have to exit the position.
        elif not self.__position.exitActive() and cross.cross_below(self.__prices, self.__sma) > 0:
            self.__position.exitMarket()


class MultiInstrumentStrategy(strategy.BacktestingStrategy):
    def __init__(self, feed, instrumentList, amount, smaPeriod):
        strategy.BacktestingStrategy.__init__(self, feed, amount)
        self.__instrumentList = instrumentList
        self.__prices = {}
        self.__sma = {}
        # We'll use adjusted close values instead of regular close values.
        self.setUseAdjustedValues(True)
        for x in range(len(self.__instrumentList)):
            self.__prices[self.__instrumentList[x]] = feed[self.__instrumentList[x]].getPriceDataSeries()
            self.__sma[self.__instrumentList[x]] = ma.SMA(self.__prices[self.__instrumentList[x]], smaPeriod)

        print self.__prices

        #self.__instrument = instrumentList[0]
        self.__positions = self.getBroker().getPositions()
        self.__activePosition = ''
        
    #def getSMA(self):
    #    return self.__sma

    def onEnterCanceled(self, position):
        self.__position = []

    def onExitOk(self, position):
        self.__position = []

    def onExitCanceled(self, position):
        # If the exit was canceled, re-submit it.
        self.__position[0].exitMarket()
        self.__position[1].exitMarket()

    def onBars(self, bars):
        inst0_cond = cross.cross_above(self.__prices[self.__instrumentList[0]], self.__sma[self.__instrumentList[0]])
        inst2_cond = cross.cross_above(self.__prices[self.__instrumentList[2]], self.__sma[self.__instrumentList[2]])
        # If a position was not opened, check if we should enter a long position.
        if not self.__positions:
            if inst0_cond > 0 or inst2_cond > 0:
                if inst0_cond > 0:
                    shares_0 = int(self.getBroker().getCash() * 0.6 / bars[self.__instrumentList[0]].getPrice())
                    shares_2 = int(self.getBroker().getCash() * 0.3 / bars[self.__instrumentList[2]].getPrice())
                else:
                    shares_0 = int(self.getBroker().getCash() * 0.3 / bars[self.__instrumentList[0]].getPrice())
                    shares_2 = int(self.getBroker().getCash() * 0.6 / bars[self.__instrumentList[2]].getPrice())
                # Enter a buy market order. The order is good till canceled.
                print "%%%%%$$$$: ", shares_0, shares_2
                self.__positions[self.__instrumentList[0]] = self.enterLong(self.__instrumentList[0], int(shares_0), True)
                self.__positions[self.__instrumentList[2]] =self.enterLong(self.__instrumentList[2], int(shares_2), True)
                self.__activePosition = self.__instrumentList[0]
        # Check if we have to exit the position.
        elif cross.cross_below(self.__prices[self.__activePosition], self.__sma[self.__activePosition]) > 0:
            self.__position[self.__instrumentList[0]].exitMarket()
            self.__position[self.__instrumentList[2]].exitMarket()


class MyStrategy(strategy.BacktestingStrategy):
    def __init__(self, feed, instrument, amount, smaPeriod):
        strategy.BacktestingStrategy.__init__(self, feed, amount)
        self.__position = None
        self.__instrument = instrument
        # We'll use adjusted close values instead of regular close values
        self.setUseAdjustedValues(True)
        self.__sma = ma.SMA(feed[instrument].getPriceDataSeries(), smaPeriod)
        
        #self.__rsi = rsi.RSI(feed[instrument].getAdjCloseDataSeries(), 14)
        #self.__sma = ma.SMA(self.__rsi, 15)
        #self.__instrument = instrument
        

    def onEnterOk(self, position):
        execInfo = position.getEntryOrder().getExecutionInfo()
        self.info("BUY at $%.2f" % (execInfo.getPrice()))

    def onEnterCanceled(self, position):
        self.__position = None

    def onExitOk(self, position):
        execInfo = position.getExitOrder().getExecutionInfo()
        self.info("SELL at $%.2f" % (execInfo.getPrice()))
        self.__position = None

    def onExitCanceled(self, position):
        # If the exit was canceled, re-submit it.
        self.__position.exitMarket()

    def onBars(self, bars):
        # Wait for enough bars to be available to calculate a SMA.
        if self.__sma[-1] is None:
            return

        bar = bars[self.__instrument]
        # If a position was not opened, check if we should enter a long position.
        if self.__position is None:
            if bar.getPrice() > self.__sma[-1]:
                # Enter a buy market order for 10 shares. The order is good till canceled.
                self.__position = self.enterLong(self.__instrument, 10, True)
        # Check if we have to exit the position.
        elif bar.getPrice() < self.__sma[-1]:
            self.__position.exitMarket()

'''
def run_strategy(smaPeriod):
    # Load the yahoo feed from the CSV file
    feed = yahoofeed.Feed()
    feed.addBarsFromCSV("orcl", "/home/parallels/Code/heroku-envbased/roboquant/strategies/algotrade/orcl-2014.csv")

    # Evaluate the strategy with the feed.
    myStrategy = MyStrategy(feed, "orcl", smaPeriod)
    myStrategy.run()
    print "Final portfolio value: $%.2f" % myStrategy.getBroker().getEquity()
'''

class Feed(membf.BarFeed):
    def __init__(self, frequency, maxLen=3000):
        membf.BarFeed.__init__(self, frequency, maxLen)

    def barsHaveAdjClose(self):
        return True

    def loadBars(self, instrument, bars):
        self.addBarsFromSequence(instrument, bars)

def redis_listoflists_to_dict(redis_list):
    list_values, list_keys = zip(*redis_list)
    return dict(zip(list_keys, list_values))


def run_strategy_redis(ticker, amount, stdate, enddate):
    from pyalgotrade import plotter
    
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
    Adj_Low_dict = redis_listoflists_to_dict(redis_Adj_Open)
    Adj_Close_dict = redis_listoflists_to_dict(redis_Adj_Open)
    Adj_Volume_dict = redis_listoflists_to_dict(redis_Adj_Open)

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
            Adj_Open = Adj_Close
            Adj_High = Adj_Close
            Adj_Low = Adj_Close
            Adj_Volume = Adj_Close * 250000 ### Constant volume...
            #print "$$$$$####@@@@", Adj_Close, Adj_Open, Adj_High, Adj_Low, Adj_Volume, dateTime

        #print key, Adj_Close, Adj_Open, Adj_High, Adj_Low, Adj_Volume, dateTime  
        bar = BasicBar(dateTime, 
              Adj_Open , Adj_High, Adj_Low, Adj_Close, Adj_Volume, Adj_Close, Frequency.TRADE)
        bd.append(bar)
    '''
    bd = []
    Adj_Open, Adj_High, Adj_Low, Adj_Close, Adj_Volume, dt_millisec, dateTime = []
    for x in range(len(redis_Adj_Close)):
        dt_millisec.append(redis_Adj_Close[x][1])
        dateTime.append(dt.timestamp_to_datetime(redis_Adj_Close[x][1]/1000))
        Adj_Close.append(float(redis_Adj_Close[x][0]))

    for j in range(len(dt_millisec)):
        dateTime = dt.timestamp_to_datetime(redis_Adj_Open[x][1]/1000)
        Adj_Open = float(redis_Adj_Open[x][0])
        Adj_High = float(redis_Adj_High[x][0])
        Adj_Low = float(redis_Adj_Low[x][0])
        Adj_Close = float(redis_Adj_Close[x][0])
        Adj_Volume = float(redis_Adj_Volume[x][0])
        

        print dateTime, redis_Adj_Close[x][1]/1000, Adj_Open, Adj_High, Adj_Low, Adj_Close, Adj_Volume
        bar = BasicBar(dateTime, 
              Adj_Open , Adj_High, Adj_Low, Adj_Close, Adj_Volume, Adj_Close, Frequency.TRADE)
        bd.append(bar)
    '''
    
    feed = Feed(Frequency.DAY, 3000)
    feed.loadBars(ticker, bd)


    # Evaluate the strategy with the feed.
    #myStrategy = MyStrategy(feed, ticker, amount, 20)
    myStrategy = SMACrossOver(feed, ticker, amount, 18)

    # Attach a returns analyzers to the strategy.
    returnsAnalyzer = returns.Returns()
    results = StrategyResults(myStrategy, returnsAnalyzer)

    #plt = plotter.StrategyPlotter(myStrategy)
    # Plot the simple returns on each bar.
    #plt.getOrCreateSubplot("returns").addDataSeries("Cumulative returns", returnsAnalyzer.getCumulativeReturns())
    # Plot the strategy.
    #plt.plot()

    myStrategy.run()
    print "Final portfolio value: $%.2f" % myStrategy.getBroker().getEquity()
    return results;
    

def run_strategy_multipleinstruments(amount, stdate, enddate):
    from pyalgotrade import plotter
    
    seconds = mktime(stdate.timetuple())
    seconds2 = mktime(enddate.timetuple())

    redis_url = os.environ.get('REDISCLOUD_URL', 'redis://localhost:6379')
    url = urlparse.urlparse(redis_url)
    redisConn = redis.StrictRedis(host=url.hostname, port=url.port, password=url.password)
    tickerList = ['AAPL', 'MSFT', 'GS']
    #### Initialize feed....
    feed = Feed(Frequency.TRADE, 3000)
    for ticker in range(len(tickerList)):
        redis_data = redisConn.zrangebyscore(tickerList[ticker]+':Adj. Close', int(seconds*1000), int(seconds2*1000), 0, -1, True)
        bd = []
        for x in range(len(redis_data)):
            v = float(redis_data[x][0])
            dateTime = dt.timestamp_to_datetime(redis_data[x][1]/1000)
            bar = BasicBar(dateTime, 
                  v , v, v, v, 200000, v, Frequency.DAY)
            bd.append(bar)
        print tickerList[ticker], len(bd)
        feed.loadBars(tickerList[ticker], bd)


    # Evaluate the strategy with the feed.
    #myStrategy = MyStrategy(feed, ticker, amount, 20)
    myStrategy = MultiInstrumentStrategy(feed, tickerList, amount, 20)

    # Attach a returns analyzers to the strategy.
    returnsAnalyzer = returns.Returns()
    results = StrategyResults(myStrategy, returnsAnalyzer)

    #plt = plotter.StrategyPlotter(myStrategy)
    # Plot the simple returns on each bar.
    #plt.getOrCreateSubplot("returns").addDataSeries("Cumulative returns", returnsAnalyzer.getCumulativeReturns())
    # Plot the strategy.
    #plt.plot()

    myStrategy.run()
    print "Final portfolio value: $%.2f" % myStrategy.getBroker().getEquity()
    return results;
    