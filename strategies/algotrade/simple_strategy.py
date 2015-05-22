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
    def __init__(self, frequency, maxLen=1024):
        membf.BarFeed.__init__(self, frequency, maxLen)

    def barsHaveAdjClose(self):
        return True

    def loadBars(self, instrument, bars):
        self.addBarsFromSequence(instrument, bars)


def run_strategy_redis(ticker, amount, stdate, enddate):
    from pyalgotrade import plotter
    
    #dt1 = datetime.datetime(2014, 01, 01, 17, 0, 0, 0)
    #dt2 = datetime.datetime(2014, 12, 31, 17, 0, 0, 0)
    seconds = mktime(stdate.timetuple())
    seconds2 = mktime(enddate.timetuple())

    redis_url = os.environ.get('REDISCLOUD_URL', 'redis://localhost:6379')
    url = urlparse.urlparse(redis_url)
    #print "$$$URL: ", url
    redisConn = redis.StrictRedis(host=url.hostname, port=url.port, password=url.password)
    redis_data = redisConn.zrangebyscore(ticker+':Adj. Close', int(seconds*1000), int(seconds2*1000), 0, -1, True)
    bd = []
    for x in range(len(redis_data)):
        v = float(redis_data[x][0])
        dateTime = dt.timestamp_to_datetime(redis_data[x][1]/1000)
        bar = BasicBar(dateTime, 
              v , v, v, v, 200000, v, Frequency.TRADE)
        bd.append(bar)
        #print bar.getDateTime(), bar.getFrequency()
    feed = Feed(Frequency.TRADE, 1024)
    feed.loadBars(ticker, bd)


    # Evaluate the strategy with the feed.
    myStrategy = MyStrategy(feed, ticker, amount, 20)

    # Attach a returns analyzers to the strategy.
    returnsAnalyzer = returns.Returns()
    myStrategy.attachAnalyzer(returnsAnalyzer)

    #plt = plotter.StrategyPlotter(myStrategy)

    results = StrategyResults(myStrategy)
    # Plot the simple returns on each bar.
    #plt.getOrCreateSubplot("returns").addDataSeries("Cumulative returns", returnsAnalyzer.getCumulativeReturns())
    # Plot the strategy.
    #plt.plot()

    myStrategy.run()
    portresults = results.getPortfolioResult()
    print "Final portfolio value: $%.2f" % myStrategy.getBroker().getEquity()
    #print "Portfolio results: ", portresults
    return portresults;
    
