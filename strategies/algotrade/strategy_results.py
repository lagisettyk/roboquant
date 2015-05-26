import pyalgotrade.broker 
from time import mktime


class StrategyResults(object):
    """Class responsible for plotting a strategy execution.
    :param strat: The strategy to plot.
    :type strat: :class:`pyalgotrade.strategy.BaseStrategy`.
    :param plotAllInstruments: Set to True to get a subplot for each instrument available.
    :type plotAllInstruments: boolean.
    :param plotBuySell: Set to True to get the buy/sell events plotted for each instrument available.
    :type plotBuySell: boolean.
    :param plotPortfolio: Set to True to get the portfolio value (shares + cash) plotted.
    :type plotPortfolio: boolean.
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
        #### attach returns analyzer to strategy...
        strat.attachAnalyzer(returnsAnalyzer)
        self.__returnsAnalyzer = returnsAnalyzer

    def __onBarsProcessed(self, strat, bars):
        dateTime = bars.getDateTime()
        self.__dateTimes.add(dateTime)
        seconds = mktime(bars.getDateTime().timetuple())
        

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

