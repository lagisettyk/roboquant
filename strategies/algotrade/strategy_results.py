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

    def __init__(self, strat, plotAllInstruments=True, plotBuySell=True, plotPortfolio=True):
        self.__dateTimes = set()

        self.__plotAllInstruments = plotAllInstruments
        self.__plotBuySell = plotBuySell
        self.__plotPortfolio = plotPortfolio
        strat.getBarsProcessedEvent().subscribe(self.__onBarsProcessed)
        strat.getBroker().getOrderUpdatedEvent().subscribe(self.__onOrderEvent)
        self.__portfolioValues = []

    def __onBarsProcessed(self, strat, bars):
        dateTime = bars.getDateTime()
        self.__dateTimes.add(dateTime)

        # Feed the portfolio evolution subplot.
        if self.__plotPortfolio:
            #self.__portfolioValues[bars.getDateTime()] = strat.getBroker().getEquity()
            seconds = mktime(bars.getDateTime().timetuple())
            val = [int(seconds * 1000), strat.getBroker().getEquity()]
            self.__portfolioValues.append(val)
            #print "Datetime, value: ", bars.getDateTime(), strat.getBroker().getEquity()

    def __onOrderEvent(self, broker_, orderEvent):
        order = orderEvent.getOrder()
        if self.__plotBuySell and orderEvent.getEventType() in (pyalgotrade.broker.OrderEvent.Type.PARTIALLY_FILLED, pyalgotrade.broker.OrderEvent.Type.FILLED): #and order.getInstrument() == self.__instrument:
            action = order.getAction()
            execInfo = orderEvent.getEventInfo()
            if action in [pyalgotrade.broker.Order.Action.BUY, pyalgotrade.broker.Order.Action.BUY_TO_COVER]:
                #self.getSeries("Buy", BuyMarker).addValue(execInfo.getDateTime(), execInfo.getPrice())
                print "BUY: ", execInfo.getDateTime(), execInfo.getPrice()
            elif action in [pyalgotrade.broker.Order.Action.SELL, pyalgotrade.broker.Order.Action.SELL_SHORT]:
                #self.getSeries("Sell", SellMarker).addValue(execInfo.getDateTime(), execInfo.getPrice())
                print "SELL: ", execInfo.getDateTime(), execInfo.getPrice()

    def getPortfolioResult(self):
        return self.__portfolioValues        
