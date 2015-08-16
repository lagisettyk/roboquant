#!/usr/bin/python
from pyalgotrade import strategy
from pyalgotrade import plotter
#from pyalgotrade.tools import yahoofinance
from pyalgotrade.stratanalyzer import sharpe
from pyalgotrade.talibext import indicator

### technical.EventWindow and technical.EventBasedFilter
### could be used instead of dsToNumpyArray
### For later code cleanup
#from pyalgotrade import dataseries
#from pyalgotrade import technical

import numpy
import datetime
#import Image
from matplotlib import pyplot
import operator
#from decimal import getcontext, Decimal
#getcontext().prec = 2

import logging
import json
import jsonschema

import xiquantFuncs
import xiquantStrategyParams as consts
import divergence
import xiquantPlatform

import os

#import dateutil.parser

class BBSpread(strategy.BacktestingStrategy):
	def __init__(self, feedAnalysis, feedRaw, instrument, bBandsPeriod, earningsCal, startPortfolio):
		self.__feed = feedAnalysis
		strategy.BacktestingStrategy.__init__(self, self.__feed, startPortfolio)

		barsDict = {}
		barsDict[instrument] = feedRaw.getBarSeries(instrument)
		barsDict['SPY'] = feedRaw.getBarSeries('SPY')
		barsDict['QQQ'] = feedRaw.getBarSeries('QQQ')
		self.__barsDict = barsDict

		self.__feedLookbackAdjusted = feedRaw
		self.__bullishOrBearish = 0
		self.__longPos = None
		self.__shortPos = None
		self.__entryDay = None
		self.__entryDayStopPrice = 0.0
		self.__instrument = instrument
		self.__instrumentAdj = instrument + "_adjusted"
		self.__priceDS = self.__feed[self.__instrumentAdj].getCloseDataSeries()
		self.__bb_lower = 0
		self.__bb_middle = 0
		self.__bb_upper = 0
		self.__bbPeriod = bBandsPeriod
		self.__macd = None
		self.__ema1 = 0
		self.__ema2 = 0
		self.__ema3 = 0
		self.__sma1 = 0
		self.__sma2 = 0
		self.__adx = None
		self.__dmiPlus = None
		self.__dmiMinus = None
		# Count used to pick up the first day of the croc mouth opening
		self.__bbFirstCrocDay = None
		self.__bbFirstUpperCrocDay = None
		self.__bbFirstLowerCrocDay = None
		self.__logger = None
		self.__earningsCal = earningsCal
		# Orders are stored in a dictionary with datetime as the key and a list of orders
		# as the value. Each item in the list is a tuple of (instrument, action, price) or
		# (instrument, action) kinds.
		self.__orders = {} 
		self.__entryOrderForFile = None
		self.__entryOrder = None
		self.__entryOrderTime = None
		self.__entryOrderTuple = None
		self.__SPYExceptions = consts.SPY_EXCEPTIONS
		self.__portfolioCashBefore = 0.0
		self.__adjRatio = 0.0
		self.__adjEntryPrice = 0.0
		self.__entryDayAdjStopPrice = 0.0
		self.__bandBreachOrTouch = True
		self.__noBandBreachOrTouchEntryPrice = 0.0

	def initLogging(self):
		logger = logging.getLogger("xiQuant")
		logger.propagate = True # stop the logs from going to the console
		logger.setLevel(logging.DEBUG)
		logFileName = "BB_Spread_" + self.__instrument + ".log"
		handler = logging.FileHandler(logFileName, delay=True)
		handler.setLevel(logging.DEBUG)
		#formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
		formatter = logging.Formatter('%(levelname)-8s %(message)s')
		handler.setFormatter(formatter)
		logger.addHandler(handler)
		return logger
		
	def stopLogging(self):
		logging.shutdown()
		return
		
	def isTechBullish(self):
		self.__logger.debug("QQQ Close: $%.2f" % self.__qqqDS[-1])
		self.__logger.debug("QQQ 20 SMA: $%.2f" % self.__smaQQQShort1[-1])
		self.__logger.debug("QQQ Upper BBand: $%.2f" % self.__upperQQQBBDataSeries[-1])
		if self.__qqqDS[-1] > self.__smaQQQShort1[-1] and self.__qqqDS[-1] < self.__upperQQQBBDataSeries[-1]:
			self.__logger.debug("The tech sector is Bullish today.")
			return True
		else:
			self.__logger.debug("The tech sector is NOT Bullish today.")
			return False

	def isTechBearish(self):
		self.__logger.debug("QQQ Close: $%.2f" % self.__qqqDS[-1])
		self.__logger.debug("QQQ 20 SMA: $%.2f" % self.__smaQQQShort1[-1])
		self.__logger.debug("QQQ Lower BBand: $%.2f" % self.__lowerQQQBBDataSeries[-1])
		if self.__qqqDS[-1] < self.__smaQQQShort1[-1] and self.__qqqDS[-1] > self.__lowerQQQBBDataSeries[-1]:
			self.__logger.debug("The tech sector is Bearish today.")
			return True
		else:
			self.__logger.debug("The tech sector is NOT Bearish today.")
			return False

	def isBullish(self):
		self.__logger.debug("SPY Close: $%.2f" % self.__spyDS[-1])
		self.__logger.debug("SPY 20 SMA: $%.2f" % self.__smaSPYShort1[-1])
		self.__logger.debug("SPY Upper BBand: $%.2f" % self.__upperSPYBBDataSeries[-1])
		if self.__spyDS[-1] > self.__smaSPYShort1[-1] and (self.__spyDS[-1] < self.__upperSPYBBDataSeries[-1] or self.__spyDS[-1] >= self.__upperSPYBBDataSeries[-1]):
			self.__logger.debug("The market is Bullish today.")
			return True
		else:
			self.__logger.debug("The market is NOT Bullish today.")
			return False

	def isBearish(self):
		self.__logger.debug("SPY Close: $%.2f" % self.__spyDS[-1])
		self.__logger.debug("SPY 20 SMA: $%.2f" % self.__smaSPYShort1[-1])
		self.__logger.debug("SPY Lower BBand: $%.2f" % self.__lowerSPYBBDataSeries[-1])
		if self.__spyDS[-1] < self.__smaSPYShort1[-1] and (self.__spyDS[-1] > self.__lowerSPYBBDataSeries[-1] or self.__spyDS[-1] <= self.__lowerSPYBBDataSeries[-1]):
			self.__logger.debug("The market is Bearish today.")
			return True
		else:
			self.__logger.debug("The market is NOT Bearish today.")
			return False

	def getOrders(self):
		return self.__orders

	def onStart(self):
		self.__logger = self.initLogging()
		self.__logger.info("Initial portfolio value: $%.2f" % self.getBroker().getEquity())
		print "Load the input JSON strategy file."
		#jsonStrategies = open('json_strategies')
		jsonStrategiesPath = os.path.join(os.path.dirname(__file__), 'json_strategies')
		jsonStrategies = open(jsonStrategiesPath)
		self.__inpStrategy = json.load(jsonStrategies)
		print "Load the input JSON entry price file."
		#jsonEntryPrice = open('json_entry_price')
		jsonEntryPricePath = os.path.join(os.path.dirname(__file__), 'json_entry_price')
		jsonEntryPrice = open(jsonEntryPricePath)
		self.__inpEntry = json.load(jsonEntryPrice)
		print "Load the input JSON exit price file."
		#jsonExitPrice = open('json_exit_price')
		jsonExitPricePath = os.path.join(os.path.dirname(__file__), 'json_exit_price')
		jsonExitPrice = open(jsonExitPricePath)
		self.__inpExit = json.load(jsonExitPrice)
		jsonStrategies.close()
		jsonEntryPrice.close()
		jsonExitPrice.close()



	def onFinish(self, bars):
		self.stopLogging()

		# Write the in-memory orders to a file.
		dataRows = []
		for key, value in self.__orders.iteritems():
			row = []
			row.append(key)
			row.append(value[0][0])
			row.append(value[0][1])
			row.append(value[0][2])
			row.append(value[0][3])
			row.append(value[0][4])
			dataRows.append(row)

		# This is for ordering orders by timestamp and rank....
		dataRows.sort(key = operator.itemgetter(0, 1))
		fake_csv = xiquantFuncs.make_fake_csv(dataRows)
		#self.__realOrdersFile = open(consts.ORDERS_FILE, 'a+')
		self.__realOrdersFile = open(consts.ORDERS_FILE, 'w')
		for line in fake_csv:
			self.__realOrdersFile.write(line)

		self.__realOrdersFile.close()
		return

	def onEnterOk(self, position):
		execInfo = position.getEntryOrder().getExecutionInfo()
		t = self.__priceDS.getDateTimes()[-1]
		tInSecs = xiquantFuncs.secondsSinceEpoch(t)
		if self.__longPos == position:
			self.__logger.info("%s: BOUGHT %d at $%.2f" % (execInfo.getDateTime(), execInfo.getQuantity(), execInfo.getPrice()))
			existingOrdersForTime = self.__orders.setdefault(self.__entryOrderTime, [])
			existingOrdersForTime.append(self.__entryOrderTuple)
			self.__orders[self.__entryOrderTime] = existingOrdersForTime
			self.__logger.info("Portfolio cash after BUY: $%.2f" % self.getBroker().getCash(includeShort=False))
		elif self.__shortPos == position:
			self.__logger.info("%s: SOLD %d at $%.2f" % (execInfo.getDateTime(), execInfo.getQuantity(), execInfo.getPrice()))
			existingOrdersForTime = self.__orders.setdefault(self.__entryOrderTime, [])
			existingOrdersForTime.append(self.__entryOrderTuple)
			self.__orders[self.__entryOrderTime] = existingOrdersForTime
			self.__logger.info("Portfolio cash after SELL: $%.2f" % self.getBroker().getCash(includeShort=False))

		# Enter a stop loss order for the entry day
		if self.__longPos == position:
			self.__longPos.exitStop(self.__entryDayStopPrice, True)
			# Adding a second to the stop loss order to ensure that the stop loss order
			# gets picked up ONLY after the initial order is picked up during the order
			# processing phase.
			tInSecs = xiquantFuncs.secondsSinceEpoch(t + datetime.timedelta(seconds=1))
			existingOrdersForTime = self.__orders.setdefault(tInSecs, [])
			existingOrdersForTime.append((self.__instrument, 'Stop-Sell', self.__entryDayAdjStopPrice, consts.DUMMY_ADJ_RATIO, consts.DUMMY_RANK))
			self.__orders[tInSecs] = existingOrdersForTime
			self.__logger.info("%s: Stop Loss SELL order of %d %s shares set at %.2f" % (self.getCurrentDateTime(), self.__longPos.getShares(), self.__instrument, self.__entryDayStopPrice))
		elif self.__shortPos == position: 
			self.__shortPos.exitStop(self.__entryDayStopPrice, True)
			# Adding a second to the stop loss order to ensure that the stop loss order
			# gets picked up ONLY after the initial order is picked up during the order
			# processing phase.
			tInSecs = xiquantFuncs.secondsSinceEpoch(t + datetime.timedelta(seconds=1))
			existingOrdersForTime = self.__orders.setdefault(tInSecs, [])
			existingOrdersForTime.append((self.__instrument, 'Stop-Buy', self.__entryDayAdjStopPrice, consts.DUMMY_ADJ_RATIO, consts.DUMMY_RANK))
			self.__orders[tInSecs] = existingOrdersForTime
			self.__logger.info("%s: Stop Loss BUY order of %d %s shares set at %.2f" % (self.getCurrentDateTime(), self.__shortPos.getShares(), self.__instrument, self.__entryDayStopPrice))

	def onEnterCanceled(self, position):
		# This would have to be revisited as we would like to try and renter with
		# a higher price for options, as long as the entry point is within the
		# range that the tech. analysis has come up with.
		if self.__longPos == position:
			self.__longPos = None 
			self.__entryDay = None
			self.__logger.debug("An enter LONG order cancelled.")
		elif self.__shortPos == position: 
			self.__shortPos = None 
			self.__entryDay = None
			self.__logger.debug("An enter SHORT order cancelled.")
		else: 
			assert(False)

	def onExitOk(self, position):
		execInfo = position.getExitOrder().getExecutionInfo()
		t = self.__priceDS.getDateTimes()[-1]
		tInSecs = xiquantFuncs.secondsSinceEpoch(t)
		if self.__longPos == position: 
			self.__logger.info("%s: SOLD CLOSE %d at $%.2f" % (execInfo.getDateTime(), execInfo.getQuantity(), execInfo.getPrice()))
			self.__logger.info("Portfolio after SELL CLOSE: $%.2f" % self.getBroker().getCash(includeShort=False))
			self.__longPos = None 
		elif self.__shortPos == position: 
			self.__logger.info("%s: COVER BUY %d at $%.2f" % (execInfo.getDateTime(), execInfo.getQuantity(), execInfo.getPrice()))
			self.__logger.info("Portfolio after COVER BUY: $%.2f" % self.getBroker().getCash(includeShort=False))
			self.__shortPos = None 
		else: 
			assert(False)

	def onExitCanceled(self, position):
		# If the exit was canceled, re-submit it.
		######## This needs to be re-looked at as we constantly tighten the existing stop limit
		######## order by canceling the previous ones.
		# position.exitMarket()
		pass

	def getBollingerBands(self):
		return self.__bbands

	def getUpperBollingerBands(self):
		return self.__upperBBDataSeries 

	def getMiddleBollingerBands(self):
		return self.__middleBBDataSeries

	def getLowerBollingerBands(self):
		return self.__lowerBBDataSeries


	def getSPYBollingerBands(self):
		return self.__spyBBands

	def getQQQBollingerBands(self):
		return self.__qqqBBands

	def getRSI(self):
		return self.__rsi

	def getEMAFast(self):
		return self.__emaFast

	def getEMASlow(self):
		return self.__emaSlow

	def getEMASignal(self):
		return self.__emaSignal

	def getEMASHORT1(self):
		return self.__emaShort1

	def getEMASHORT2(self):
		return self.__emaShort2

	def getEMASHORT3(self):
		return self.__emaShort3

	def getSPYSMASHORT2(self):
		return self.__smaSPYShort1

	def getQQQSMASHORT2(self):
		return self.__smaQQQShort1

	def getSMALONG1(self):
		return self.__smaLong1

	def getSMALONG2(self):
		return self.__smaLong2

	def getMACD(self):
		return self.__macd

	def getADX(self):
		return self.__adx

	def getDMIPlus(self):
		return self.__dmiPlus

	def getDMIMinus(self):
		return self.__dmiMinus

	def onBars(self, bars):

		if len(self.__priceDS) < consts.TRADE_DAYS_IN_RESISTANCE_LOOKBACK_WINDOW:
			return
		
		lookbackEndDate = self.__priceDS.getDateTimes()[-1] 
		lookbackStartDate = lookbackEndDate - datetime.timedelta(days=consts.TRADE_DAYS_IN_RESISTANCE_LOOKBACK_WINDOW)
		feedLookbackEndAdj = xiquantPlatform.xiQuantAdjustBars(self.__barsDict, lookbackStartDate, lookbackEndDate)
		feedLookbackEndAdj.adjustBars()

		bar = feedLookbackEndAdj.getBarSeries(self.__instrumentAdj)[-1]

		self.__spyDS = feedLookbackEndAdj.getCloseDataSeries('SPY_adjusted')
		self.__qqqDS = feedLookbackEndAdj.getCloseDataSeries('QQQ_adjusted')
		self.__openDS = feedLookbackEndAdj.getOpenDataSeries(self.__instrumentAdj)
		self.__closeDS = feedLookbackEndAdj.getCloseDataSeries(self.__instrumentAdj)
		self.__volumeDS = feedLookbackEndAdj.getVolumeDataSeries(self.__instrumentAdj)
		self.__upperBBDataSeries, self.__middleBBDataSeries, self.__lowerBBDataSeries = indicator.BBANDS(self.__closeDS, len(self.__closeDS), self.__bbPeriod, 2.0, 2.0)
		self.__upperSPYBBDataSeries, self.__middleSPYBBDataSeries, self.__lowerSPYBBDataSeries = indicator.BBANDS(self.__spyDS, len(self.__spyDS), self.__bbPeriod, 2, 2)
		self.__upperQQQBBDataSeries, self.__middleQQQBBDataSeries, self.__lowerQQQBBDataSeries = indicator.BBANDS(self.__qqqDS, len(self.__qqqDS), self.__bbPeriod, 2, 2)
		self.__rsi = indicator.RSI(self.__closeDS, len(self.__closeDS), consts.RSI_SETTING)
		#print "RSI: ", self.__rsi
		self.__lowPriceDS = feedLookbackEndAdj.getLowDataSeries(self.__instrumentAdj)
		self.__highPriceDS = feedLookbackEndAdj.getHighDataSeries(self.__instrumentAdj)
		self.__emaFast = indicator.EMA(self.__closeDS, len(self.__closeDS), consts.MACD_FAST_FASTPERIOD)
		#print "EMA Fast: ", self.__emaFast
		self.__emaSlow = indicator.EMA(self.__closeDS, len(self.__closeDS), consts.MACD_FAST_SLOWPERIOD)
		#print "EMA Slow: ", self.__emaSlow
		self.__emaSignal = indicator.EMA(self.__closeDS, len(self.__closeDS), consts.MACD_FAST_SIGNALPERIOD)
		#print "EMA Signal: ", self.__emaSignal
		self.__emaShort1 = indicator.EMA(self.__closeDS, len(self.__closeDS), consts.EMA_SHORT_1)
		#print "EMA Short1: ", self.__emaShort1
		self.__emaShort2 = indicator.EMA(self.__closeDS, len(self.__closeDS), consts.EMA_SHORT_2)
		#print "EMA Short2: ", self.__emaShort2
		self.__emaShort3 = indicator.EMA(self.__closeDS, len(self.__closeDS), consts.EMA_SHORT_3)
		#print "EMA Short3: ", self.__emaShort3
		self.__smaSPYShort1 = indicator.SMA(self.__spyDS, len(self.__spyDS), consts.SMA_SHORT_1)
		#print "SMA SPY Short1: ", self.__smaSPYShort1
		self.__smaQQQShort1 = indicator.SMA(self.__qqqDS, len(self.__qqqDS), consts.SMA_SHORT_1)
		#print "QQQ SPY Short1: ", self.__smaQQQShort1
		self.__smaLowerTiny = indicator.SMA(self.__lowerBBDataSeries, len(self.__lowerBBDataSeries), consts.SMA_TINY)
		#print "SMA Lower Tiny: ", self.__smaLowerTiny
		self.__smaUpperTiny = indicator.SMA(self.__upperBBDataSeries, len(self.__upperBBDataSeries), consts.SMA_TINY)
		#print "SMA Upper Tiny: ", self.__smaUpperTiny
		self.__smaLong1 = indicator.SMA(self.__spyDS, len(self.__spyDS), consts.SMA_LONG_1)
		#print "SMA Long1: ", self.__smaLong1
		self.__smaLong2 = indicator.SMA(self.__spyDS, len(self.__spyDS), consts.SMA_LONG_2)
		#print "SMA Long2: ", self.__smaLong2
		self.__stdDevLower = indicator.STDDEV(self.__lowerBBDataSeries, len(self.__lowerBBDataSeries), consts.SMA_TINY)
		#print "Std Dev Lower: ", self.__stdDevLower
		self.__stdDevUpper = indicator.STDDEV(self.__upperBBDataSeries, len(self.__upperBBDataSeries), consts.SMA_TINY)
		#print "Std Dev Upper: ", self.__stdDevUpper

		self.__logger.debug("=====================================================================")
		# Cancel any existing entry orders from yesterday.
		# We do this because the broker gets the daily bar first so the broker can execute
		# the order placed at the end of yesterday (after analysis), so if there are any
		# active orders it means that the broker was not able to execute the orders based on
		# today's bar.
		if self.__longPos and self.__longPos.entryActive():
			self.__longPos.cancelEntry()
		if self.__shortPos and self.__shortPos.entryActive():
			self.__shortPos.cancelEntry()

		# Ensure that enough BB entries exist in the data series for running the
		# strategy.
		if len(self.__priceDS) < self.__bbPeriod + consts.BB_SLOPE_LOOKBACK_WINDOW:
			self.__logger.debug("Not enough bar entries for the BB bands.")
			self.__logger.debug("BB Period: %d" % self.__bbPeriod)
			self.__logger.debug("BB Slope Lookback Window: %d" % consts.BB_SLOPE_LOOKBACK_WINDOW)
			return

		lower = self.__lowerBBDataSeries[-1]
		middle = self.__middleBBDataSeries[-1]
		upper = self.__upperBBDataSeries[-1]
		if lower is None:
			return

		if len(self.__priceDS) < consts.MACD_PRICE_DVX_LOOKBACK:
			self.__logger.debug("Not enough bar entries for MACD price divergence check.")
			self.__logger.debug("MACD Price Dvx Lookback Window: %d" % consts.MACD_PRICE_DVX_LOOKBACK)
			return
		#self.__macd = xiquantFuncs.dsToNumpyArray(self.__emaFast, consts.MACD_PRICE_DVX_LOOKBACK) - xiquantFuncs.dsToNumpyArray(self.__emaSlow, consts.MACD_PRICE_DVX_LOOKBACK)
		self.__macd = indicator.MACD(self.__closeDS, consts.MACD_PRICE_DVX_LOOKBACK, consts.MACD_FAST_FASTPERIOD, consts.MACD_FAST_SLOWPERIOD, consts.MACD_FAST_SIGNALPERIOD)

		if len(self.__priceDS) <= consts.DMI_PERIOD:
			self.__logger.debug("Not enough bar entries for DMI computations.")
			self.__logger.debug("DMI Period: %d" % consts.DMI_PERIOD)
			return
		self.__adx = indicator.ADX(feedLookbackEndAdj.getBarSeries(self.__instrumentAdj), consts.ADX_COUNT, consts.ADX_PERIOD)
		self.__dmiPlus = indicator.PLUS_DI(feedLookbackEndAdj.getBarSeries(self.__instrumentAdj), consts.DMI_COUNT, consts.DMI_PERIOD)
		self.__dmiMinus = indicator.MINUS_DI(feedLookbackEndAdj.getBarSeries(self.__instrumentAdj), consts.DMI_COUNT, consts.DMI_PERIOD)



		############Compute Money Flow Index which is more appropriate check then cash flow Index.....
		self.__mfi = indicator.MFI(feedLookbackEndAdj.getBarSeries(self.__instrumentAdj), len(feedLookbackEndAdj.getBarSeries(self.__instrumentAdj)), 14)
		self.__mfi_tiny = indicator.MFI(feedLookbackEndAdj.getBarSeries(self.__instrumentAdj), len(feedLookbackEndAdj.getBarSeries(self.__instrumentAdj)), 3)
		

		self.__ema1 = self.getEMASHORT1()[-1]
		self.__ema2 = self.getEMASHORT2()[-1]
		self.__ema3 = self.getEMASHORT3()[-1]
		if self.__ema1 is None or self.__ema2 is None or self.__ema3 is None:
			return

		self.__sma1 = self.getSMALONG1()[-1]
		self.__sma2 = self.getSMALONG2()[-1]
		if self.__sma1 is None or self.__sma2 is None:
			return

		self.__bb_lower = lower
		self.__bb_middle = middle
		self.__bb_upper = upper
		self.__logger.debug("%s: Lower BBand: $%.2f" % (bar.getDateTime(), lower))
		self.__logger.debug("%s: Middle BBand: $%.2f" % (bar.getDateTime(), middle))
		self.__logger.debug("%s: Upper BBand: $%.2f" % (bar.getDateTime(), upper))
		self.__logger.debug("%s: Close Price: $%.2f" % (bar.getDateTime(), bar.getClose()))
		self.__logger.debug("%s: Open Price: $%.2f" % (bar.getDateTime(), bar.getOpen()))
		self.__logger.debug("%s: High Price: $%.2f" % (bar.getDateTime(), bar.getHigh()))
		self.__logger.debug("%s: Low Price: $%.2f" % (bar.getDateTime(), bar.getLow()))
		sharesToBuy = 0
	
		self.__logger.info("Portfolio Cash: $%.2f" % self.getBroker().getCash(includeShort=False))
		# The following explicit exit on market order occurs ONLY on the earnings day otherwise
		# we always let the market kick us out of a position with the stop loss orders.
		if self.exitLongSignal(bar):
			self.__portfolioCashBefore = self.getBroker().getCash(includeShort=False)
			self.__longPos.cancelExit()
			self.__longPos.exitMarket()
			t = bar.getDateTime()
			tInSecs = xiquantFuncs.secondsSinceEpoch(t)
			existingOrdersForTime = self.__orders.setdefault(tInSecs, [])
			existingOrdersForTime.append((self.__instrument, 'Sell-Market', consts.DUMMY_MARKET_PRICE, consts.DUMMY_ADJ_RATIO, consts.DUMMY_RANK))
			self.__orders[tInSecs] = existingOrdersForTime
			self.__logger.info("Exiting a LONG position")
			self.__logger.info("Portfolio Cash: $%.2f" % self.getBroker().getCash(includeShort=False))
		elif self.exitShortSignal(bar):
			self.__portfolioCashBefore = self.getBroker().getCash(includeShort=False)
			self.__shortPos.cancelExit()
			self.__shortPos.exitMarket()
			t = bar.getDateTime()
			tInSecs = xiquantFuncs.secondsSinceEpoch(t)
			existingOrdersForTime = self.__orders.setdefault(tInSecs, [])
			existingOrdersForTime.append((self.__instrument, 'Buy-Market' , consts.DUMMY_MARKET_PRICE, consts.DUMMY_ADJ_RATIO, consts.DUMMY_RANK))
			self.__orders[tInSecs] = existingOrdersForTime
			self.__logger.debug("Exiting a SHORT position")
			self.__logger.debug("Portfolio Cash: $%.2f" % self.getBroker().getCash(includeShort=False))
		else:
			if self.enterLongSignal(bar):
				# Bullish; enter a long position.
				self.__logger.info("Bullish; Trying to enter a LONG position")
				self.__logger.debug("%s: Portfolio Cash: $%.2f" % (bar.getDateTime(), self.getBroker().getCash(includeShort=False)))
				currPrice = bar.getClose()
				#self.__logger.debug("%s: Close Price: $%.2f" % (bar.getDateTime(), currPrice))
				#self.__logger.debug("%s: Open Price: $%.2f" % (bar.getDateTime(), bar.getOpen()))
				#self.__logger.debug("%s: High Price: $%.2f" % (bar.getDateTime(), bar.getHigh()))
				#self.__logger.debug("%s: Low Price: $%.2f" % (bar.getDateTime(), bar.getLow()))

				wickLen = bar.getHigh() - bar.getClose()
				candleLen = bar.getClose() - bar.getOpen()
				# Relative wick length as a percentage of the candle length
				relWickLen = (wickLen / candleLen) * 100
				# Set the entry price based on the relative wick length
				entryPrice = 0
				if "OR" in self.__inpEntry["BB_Spread_Call"] and "Long_Wick" in self.__inpEntry["BB_Spread_Call"]["OR"]:
					if abs(relWickLen) > consts.BB_LONG_WICK:
						if self.__inpEntry["BB_Spread_Call"]["OR"]["Long_Wick"] == "Half_Wick_Plus_Price_Delta":
							entryPrice = bar.getClose() +  wickLen/2 + consts.PRICE_DELTA
					else:
						entryPrice = bar.getClose() + wickLen + consts.PRICE_DELTA
				self.__logger.debug("%s: Wick Len: %.2f" % (bar.getDateTime(), wickLen))
				self.__logger.debug("%s: Candle Len: %.2f" % (bar.getDateTime(), candleLen))
				self.__logger.debug("%s: Wick Len as a percent of Candle Len: %.2f" % (bar.getDateTime(), abs(relWickLen)))
				self.__logger.debug("%s: Entry Price: %.2f" % (bar.getDateTime(), entryPrice))
				self.__adjRatio = self.__priceDS[-1] / bar.getAdjClose()
				print "=================================================================:adjRatio:=============================: ", self.__adjRatio, bar.getAdjClose(), self.__priceDS[-1], lookbackEndDate
				self.__logger.debug("Adj Ratio: %0.2f" % self.__adjRatio)
				self.__adjEntryPrice = entryPrice * self.__adjRatio
				if not self.__bandBreachOrTouch:
					self.__adjEntryPrice = self.__noBandBreachOrTouchEntryPrice * self.__adjRatio
				self.__logger.debug("%s: Adj Entry Price: %.2f" % (bar.getDateTime(), self.__adjEntryPrice))
				sharesToBuy = int((self.getBroker().getCash(includeShort=False) * consts.PERCENT_OF_CASH_BALANCE_FOR_ENTRY) / self.__adjEntryPrice)
				self.__logger.debug("Shares To Buy: %d" % sharesToBuy)
				self.__portfolioCashBefore = self.getBroker().getCash(includeShort=False)
				self.__longPos = self.enterLongStop(self.__instrumentAdj, self.__adjEntryPrice, sharesToBuy, True)
				t = bar.getDateTime()
				tInSecs = xiquantFuncs.secondsSinceEpoch(t)
				self.__entryOrderForFile = "%s,%s,Buy,%.2f\n" % (str(tInSecs), self.__instrument, self.__adjEntryPrice)
				#existingOrdersForTime = self.__orders.setdefault(tInSecs, [])
				#existingOrdersForTime.append((self.__instrument, 'Buy', entryPrice, consts.DUMMY_ADJ_RATIO, consts.DUMMY_RANK))
				#self.__orders[tInSecs] = existingOrdersForTime
				self.__entryOrderTime = tInSecs
				self.__entryOrderTuple = (self.__instrument, 'Buy', self.__adjEntryPrice, self.__adjRatio, consts.DUMMY_RANK)
				if self.__longPos == None:
					self.__logger.debug("For whatever reason, couldn't go LONG %d shares" % sharesToBuy)
				else:
					if self.__longPos.entryActive() == True:
						self.__logger.debug("The LONG order for %d shares is active" % sharesToBuy)
					else:
						self.__logger.debug("LONG on %d shares" % abs(self.__longPos.getShares()))
					self.__entryDay = xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-1])
					self.__logger.debug("Analysis Day is : %s" % self.__entryDay)
					stopPriceDelta = 0.0
					closePrice = bar.getClose()
					openPrice = bar.getOpen()
					bullishCandle = closePrice - openPrice
					self.__logger.debug("%s: Bullish Candle: %.2f" % (bar.getDateTime(), bullishCandle))
					stopPriceDelta = xiquantFuncs.computeStopPriceDelta(closePrice)
					self.__logger.debug("%s: Stop Loss Price Delta: %.2f" % (bar.getDateTime(), stopPriceDelta))
					stopPrice = xiquantFuncs.computeStopPrice(bullishCandle, "bullish", openPrice, closePrice, stopPriceDelta)
					self.__entryDayStopPrice = stopPrice * self.__adjRatio
					# Adjust the stop price based on the last day of the backtesting period
					self.__entryDayAdjStopPrice = stopPrice * self.__adjRatio
					self.__logger.debug("%s: Entry Day Stop Price: %.2f" % (bar.getDateTime(), self.__entryDayStopPrice))
			elif self.enterShortSignal(bar):
				# Bearish; enter a short position.
				self.__logger.info("Bearish; Trying to enter a SHORT position")
				self.__logger.debug("%s: Portfolio Cash: $%.2f" % (bar.getDateTime(), self.getBroker().getCash(includeShort=False)))
				currPrice = bar.getClose()
				#self.__logger.debug("%s: Close Price: $%.2f" % (bar.getDateTime(), currPrice))
				#self.__logger.debug("%s: Open Price: $%.2f" % (bar.getDateTime(), bar.getOpen()))
				#self.__logger.debug("%s: High Price: $%.2f" % (bar.getDateTime(), bar.getHigh()))
				#self.__logger.debug("%s: Low Price: $%.2f" % (bar.getDateTime(), bar.getLow()))

				wickLen = bar.getClose() - bar.getLow()
				candleLen = bar.getOpen() - bar.getClose()
				# Relative wick length as a percentage of the candle length
				relWickLen = (wickLen / candleLen) * 100
				# Set the entry price based on the relative wick length
				entryPrice = 0
				if "OR" in self.__inpEntry["BB_Spread_Put"] and "Long_Wick" in self.__inpEntry["BB_Spread_Put"]["OR"]:
					if abs(relWickLen) > consts.BB_LONG_WICK:
						if self.__inpEntry["BB_Spread_Put"]["OR"]["Long_Wick"] == "Half_Wick_Minus_Price_Delta":
							entryPrice = bar.getClose() - wickLen/2 - consts.PRICE_DELTA
					else:
						entryPrice = bar.getClose() - wickLen - consts.PRICE_DELTA
				self.__logger.debug("%s: Wick Len: %.2f" % (bar.getDateTime(), wickLen))
				self.__logger.debug("%s: Candle Len: %.2f" % (bar.getDateTime(), candleLen))
				self.__logger.debug( "%s: Wick Len as a percent of Candle Len: %.2f" % (bar.getDateTime(), abs(relWickLen)))
				self.__logger.debug( "%s: Entry Price: %.2f" % (bar.getDateTime(), entryPrice))
				self.__adjRatio = self.__priceDS[-1] / bar.getAdjClose()
				self.__logger.debug("Adj Ratio: %0.2f" % self.__adjRatio)
				self.__adjEntryPrice = entryPrice * self.__adjRatio
				if not self.__bandBreachOrTouch:
					self.__adjEntryPrice = self.__noBandBreachOrTouchEntryPrice * self.__adjRatio
				self.__logger.debug("%s: Adj Entry Price: %.2f" % (bar.getDateTime(), self.__adjEntryPrice))
				sharesToBuy = int((self.getBroker().getCash(includeShort=False) / 
								self.__adjEntryPrice) * consts.PERCENT_OF_CASH_BALANCE_FOR_ENTRY)
				self.__logger.debug( "Shares To Buy: %d" % sharesToBuy)
				self.__portfolioCashBefore = self.getBroker().getCash(includeShort=False)
				self.__shortPos = self.enterShortStop(self.__instrumentAdj, self.__adjEntryPrice, sharesToBuy, True)
				t = bar.getDateTime()
				tInSecs = xiquantFuncs.secondsSinceEpoch(t)
				self.__entryOrderForFile = "%s,%s,Sell,%.2f\n" % (str(tInSecs), self.__instrument, self.__adjEntryPrice)
				#existingOrdersForTime = self.__orders.setdefault(tInSecs, [])
				#existingOrdersForTime.append((self.__instrument, 'Sell', entryPrice, consts.DUMMY_ADJ_RATIO, consts.DUMMY_RANK))
				#self.__orders[tInSecs] = existingOrdersForTime
				self.__entryOrderTime = tInSecs
				self.__entryOrderTuple = (self.__instrument, 'Sell', self.__adjEntryPrice, self.__adjRatio, consts.DUMMY_RANK)
				if self.__shortPos == None:
					self.__logger.debug("For whatever reason, couldn't SHORT %d shares" % sharesToBuy)
				else:
					if self.__shortPos.entryActive() == True:
						self.__logger.debug("The SHORT order for %d shares is active" % sharesToBuy)
					else:
						self.__logger.debug("SHORT on %d shares" % abs(self.__shortPos.getShares()))
					self.__entryDay = xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-1])
					self.__logger.debug("Analysis Day is : %s" % self.__entryDay)
					# Enter a stop loss order to exit here
					stopPriceDelta = 0.0
					closePrice = bar.getClose()
					openPrice = bar.getOpen()
					bearishCandle = openPrice - closePrice
					self.__logger.debug("%s: Bearish Candle: %.2f" % (bar.getDateTime(), bearishCandle))
					stopPriceDelta = xiquantFuncs.computeStopPriceDelta(closePrice)
					self.__logger.debug("%s: Stop Loss Price Delta: %.2f" % (bar.getDateTime(), stopPriceDelta))
					stopPrice = xiquantFuncs.computeStopPrice(bearishCandle, "bearish", openPrice, closePrice, stopPriceDelta)
					self.__entryDayStopPrice = stopPrice * self.__adjRatio
					# Adjust the stop price based on the last day of the backtesting period
					self.__entryDayAdjStopPrice = stopPrice * self.__adjRatio
					self.__logger.debug("%s: Entry Day Stop Price: %.2f" % (bar.getDateTime(), self.__entryDayStopPrice))


	def enterLongSignal(self, bar):
		# Both the bands MUST open up like a crocodile mouth.
		if self.__inpStrategy["BB_Spread_Call"]["BB_Upper_And_BB_Lower"]["AND"][0] == "BB_Upper_Croc_Open" and self.__inpStrategy["BB_Spread_Call"]["BB_Upper_And_BB_Lower"]["AND"][1] == "BB_Lower_Croc_Open":
			if len(self.__lowerBBDataSeries) > consts.BB_SLOPE_LOOKBACK_WINDOW:
				normLowerBand = xiquantFuncs.normalize(self.__lowerBBDataSeries[-1], self.__smaLowerTiny[-1], self.__stdDevLower[-1])
				normPrevLowerBand = xiquantFuncs.normalize(self.__lowerBBDataSeries[-2], self.__smaLowerTiny[-2], self.__stdDevLower[-2])
				lowerSlope = xiquantFuncs.slope(normLowerBand, normPrevLowerBand)
				self.__logger.debug("Lower Slope: %0.2f" % lowerSlope)
		
			if len(self.__upperBBDataSeries) >= consts.BB_SLOPE_LOOKBACK_WINDOW:
				normUpperBand = xiquantFuncs.normalize(self.__upperBBDataSeries[-1], self.__smaUpperTiny[-1], self.__stdDevUpper[-1])
				normPrevUpperBand = xiquantFuncs.normalize(self.__upperBBDataSeries[-2], self.__smaUpperTiny[-2], self.__stdDevUpper[-2])
				upperSlope = xiquantFuncs.slope(normUpperBand, normPrevUpperBand)
				self.__logger.debug("Upper Slope: %0.2f" % upperSlope)
		
			##### Change the name of the delta computation function to avoid confusion
			lowerBandDelta = xiquantFuncs.computeStopPriceDelta(self.__lowerBBDataSeries[-1]) * consts.BB_SPREAD_EXIT_TIGHTEN_PRICE_FACTOR
			#if lowerSlope <= -1 * consts.BB_CROC_SLOPE and self.__lowerBBDataSeries[-1] < self.__lowerBBDataSeries[-2] and self.__lowerBBDataSeries[-2] - self.__lowerBBDataSeries[-1] > lowerBandDelta:
			if lowerSlope <= -1 * consts.BB_CROC_SLOPE and self.__lowerBBDataSeries[-1] < self.__lowerBBDataSeries[-2]:
				if (self.__bbFirstLowerCrocDay != None) and (self.__bbFirstLowerCrocDay != xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-1])):
					self.__logger.debug("Not the first day of lower band croc mouth opening")
					return False
				else:
					self.__bbFirstLowerCrocDay = xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-1])
					self.__logger.debug("First day of lower band croc mouth opening: %s" % self.__bbFirstLowerCrocDay)
		
			##### Change the name of the delta computation function to avoid confusion
			upperBandDelta = xiquantFuncs.computeStopPriceDelta(self.__upperBBDataSeries[-1]) * consts.BB_SPREAD_EXIT_TIGHTEN_PRICE_FACTOR
			#if upperSlope >= consts.BB_CROC_SLOPE and self.__upperBBDataSeries[-1] > self.__upperBBDataSeries[-2] and self.__upperBBDataSeries[-1] - self.__upperBBDataSeries[-2] > upperBandDelta:
			if upperSlope >= consts.BB_CROC_SLOPE and self.__upperBBDataSeries[-1] > self.__upperBBDataSeries[-2]:
				if (self.__bbFirstUpperCrocDay != None) and (self.__bbFirstUpperCrocDay != xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-1])):
					self.__logger.debug("Not the first day of upper band croc mouth opening")
					return False
				else:
					self.__bbFirstUpperCrocDay = xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-1])
					self.__logger.debug("First day of upper band croc mouth opening: %s" % self.__bbFirstUpperCrocDay)

			#if upperSlope < consts.BB_CROC_SLOPE or lowerSlope > -1 * consts.BB_CROC_SLOPE or self.__lowerBBDataSeries[-1] > self.__lowerBBDataSeries[-2] or self.__lowerBBDataSeries[-2] - self.__lowerBBDataSeries[-1] < lowerBandDelta or self.__upperBBDataSeries[-1] < self.__upperBBDataSeries[-2] or self.__upperBBDataSeries[-1] - self.__upperBBDataSeries[-2] < upperBandDelta:
			if upperSlope < consts.BB_CROC_SLOPE or lowerSlope > -1 * consts.BB_CROC_SLOPE or self.__lowerBBDataSeries[-1] > self.__lowerBBDataSeries[-2] or self.__upperBBDataSeries[-1] < self.__upperBBDataSeries[-2]:
				self.__logger.debug("Not a croc mouth opening")
				return False

		# This should be the first day of the Bands opening as croc mouth.
		if self.__inpStrategy["BB_Spread_Call"]["BB_Upper_And_BB_Lower"]["AND"][2] == "BB_First_Croc_Open":
			if (self.__bbFirstCrocDay != None) and (self.__bbFirstCrocDay != xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-1])):
				self.__logger.debug("Not the first day of croc mouth opening")
				return False
			if (self.__bbFirstUpperCrocDay != None) and (self.__bbFirstUpperCrocDay != xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-1])):
				self.__logger.debug("Not the first day of croc mouth opening")
				return False
			if (self.__bbFirstLowerCrocDay != None) and (self.__bbFirstLowerCrocDay != xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-1])):
				self.__logger.debug("Not the first day of croc mouth opening")
				return False

		# Set this as the first day of the croc mouth opening
		self.__bbFirstCrocDay = xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-1])
		self.__logger.debug("The first day of croc mouth opening: %s" % self.__bbFirstCrocDay)

		# Check if we will play long for this strategy or not.
		if consts.BB_SPREAD_LONG_OR_SHORT.lower() == 'short':
			self.__logger.debug("We are not playing long.")
			return False

		# Check if tomorrow is the earnings announcement, as we don't trade on the day after the earnings
		# announcement. If the earnings are announced before the market open or during, we don't trade on
		# that day. If the earnings are announced after the close of market, we don't trade the next day.
		if xiquantFuncs.isEarnings(self.__earningsCal, bar.getDateTime().date()):
			self.__logger.debug("%s: Earnings day today, so don't enter." % bar.getDateTime())
			return False

		# Check if we already hold a position in this instrument
		if self.__longPos != None:
			self.__logger.debug("We already hold a position in %s" % self.__instrument)
			return False

		# For any instrument, we trade on the same side of the market, so check the market sentiment first
		if not self.__instrument.upper() in self.__SPYExceptions:
			if consts.SPY_CHECK and self.isBearish():
				self.__logger.debug("The market is Bearish so we will not try to go LONG.")
				return False
		else:
			self.__logger.debug("%s is in the exceptions list, so we check if the tech sector is Bullish or Bearish today." % self.__instrument)
			if consts.QQQ_CHECK and self.isTechBearish():
				self.__logger.debug("The tech sector is Bearish so we will not try to go LONG.")
				return False

		# Check if close breaches or bounces off of the upper band.
		self.__bandBreachOrTouch = True
		if self.__inpStrategy["BB_Spread_Call"]["BB_Upper_And_BB_Lower"]["OR"][0] == "BB_Upper_Breach":
			if bar.getClose() > self.__bb_upper:
				self.__bandBreachOrTouch = True
				self.__logger.debug("Upper band breached.")
				self.__logger.debug("Close Price: %.2f" % bar.getClose())
				self.__logger.debug("Upper Band: %.2f" % self.__bb_upper)
			elif self.__inpStrategy["BB_Spread_Call"]["BB_Upper_And_BB_Lower"]["OR"][1] == "BB_Upper_Touch":
				# The close price may not exactly touch the upper band so we will have to
				# include some variance parameter
				if bar.getClose() == self.__bb_upper:
					self.__bandBreachOrTouch = True
					self.__logger.debug("Upper band touched.")
					self.__logger.debug("Close Price: %.2f" % bar.getClose())
					self.__logger.debug("Upper Band: %.2f" % self.__bb_upper)
				else:
					self.__bandBreachOrTouch = False
					self.__logger.debug("NO upper band breach/touch.")
					self.__noBandBreachOrTouchEntryPrice = self.__bb_upper + consts.PRICE_DELTA
					return False

		### Change to lookback window specific code.
		# Check if first breach in the lookback.
		if self.__inpStrategy["BB_Spread_Call"]["BB_Upper_And_BB_Lower"]["OR"][0] == "BB_Upper_Breach" or self.__inpStrategy["BB_Spread_Call"]["BB_Upper_And_BB_Lower"]["OR"][1] == "BB_Upper_Touch":
			if self.__closeDS[-2] > self.__upperBBDataSeries[-2]:
				self.__logger.debug("Not the first day of upper band breach/touch.")
				self.__logger.debug("Upper band: %.2f" % self.__upperBBDataSeries[-1])
				self.__logger.debug("Close price: %.2f" % self.__closeDS[-1])
				precPrevUpperBand = float("%0.2f" % self.__upperBBDataSeries[-2])
				self.__logger.debug("Previous upper band: %.4f" % precPrevUpperBand)
				#self.__logger.debug("Previous upper band: %.4f" % Decimal(self.__upperBBDataSeries[-2]))
				self.__logger.debug("Previous price: %.2f" % self.__closeDS[-2])
				return False

		# Check the price jump
		# +1 because we need one additional entry to compute the candle jump
		if (len(self.__closeDS) < consts.PRICE_JUMP_LOOKBACK_WINDOW + 1):
			self.__logger.debug("Not enough entires for Price Jump check lookback.")
			self.__logger.debug("Lookback: %d" % consts.PRICE_JUMP_LOOKBACK_WINDOW)
			self.__logger.debug("Entries: %d" % len(self.__closeDS))
			return False
		if self.__closeDS[-1] < self.__closeDS[-2]:
			self.__logger.debug("Close price not higher than the previous close.")
			self.__logger.debug("Close price: %.2f" % self.__closeDS[-1])
			self.__logger.debug("Close price: %.2f" % self.__closeDS[-2])
			return False
		openArrayInLookback = xiquantFuncs.dsToNumpyArray(self.__openDS, consts.PRICE_JUMP_LOOKBACK_WINDOW)
		closeArrayInLookback = xiquantFuncs.dsToNumpyArray(self.__closeDS, consts.PRICE_JUMP_LOOKBACK_WINDOW + 1)
		prevCloseArrayInLookback = closeArrayInLookback[:-1]
		bullishCandleJumpArray = openArrayInLookback - prevCloseArrayInLookback
		### Add the logic if more than the last day's bullish candle needs to be evaluated.
		if bullishCandleJumpArray[-1] <=0:
			self.__logger.debug("Bullish candle jump: %.2f" % bullishCandleJumpArray[-1])
			self.__logger.debug("Continue with other indicator checks")
		else:
			self.__logger.debug("Bullish candle jump: %.2f" % bullishCandleJumpArray[-1])
			prevClosePrice = self.__closeDS[-2]
			self.__logger.debug("Prev Close Price: %.2f" % prevClosePrice)
			if prevClosePrice < consts.BB_PRICE_RANGE_HIGH_1:
				if float(bullishCandleJumpArray[-1] / prevClosePrice) * 100 >= consts.BB_SPREAD_PERCENT_INCREASE_RANGE_1:
					self.__logger.debug("Bullish candle jump greater than jump range")
					self.__logger.debug("First price: %.2f" % consts.BB_PRICE_RANGE_HIGH_1)
					self.__logger.debug("First price increase: %.2f" % consts.BB_SPREAD_PERCENT_INCREASE_RANGE_1)
					self.__logger.debug("Bullish candle jump: %.2f" % bullishCandleJumpArray[-1])
					return False
			if prevClosePrice >= consts.BB_PRICE_RANGE_HIGH_1 and prevClosePrice < consts.BB_PRICE_RANGE_HIGH_2:
				if float(bullishCandleJumpArray[-1] / prevClosePrice) * 100 >= consts.BB_SPREAD_PERCENT_INCREASE_RANGE_2:
					self.__logger.debug("Bullish candle jump greater than jump range")
					self.__logger.debug("Second price: %.2f" % consts.BB_PRICE_RANGE_HIGH_2)
					self.__logger.debug("Second price increase: %.2f" % consts.BB_SPREAD_PERCENT_INCREASE_RANGE_2)
					self.__logger.debug("Bullish candle jump: %.2f" % bullishCandleJumpArray[-1])
					return False
			if prevClosePrice >= consts.BB_PRICE_RANGE_HIGH_2 and prevClosePrice < consts.BB_PRICE_RANGE_HIGH_3:
				if float(bullishCandleJumpArray[-1] / prevClosePrice) * 100 >= consts.BB_SPREAD_PERCENT_INCREASE_RANGE_3:
					self.__logger.debug("Bullish candle jump greater than jump range")
					self.__logger.debug("Third price: %.2f" % consts.BB_PRICE_RANGE_HIGH_3)
					self.__logger.debug("Third price increase: %.2f" % consts.BB_SPREAD_PERCENT_INCREASE_RANGE_3)
					self.__logger.debug("Bullish candle jump: %.2f" % bullishCandleJumpArray[-1])
					return False
			if prevClosePrice >= consts.BB_PRICE_RANGE_HIGH_3 and prevClosePrice < consts.BB_PRICE_RANGE_HIGH_4:
				if float(bullishCandleJumpArray[-1] / prevClosePrice) * 100 >= consts.BB_SPREAD_PERCENT_INCREASE_RANGE_4:
					self.__logger.debug("Bullish candle jump greater than jump range")
					self.__logger.debug("Fourth price: %.2f" % consts.BB_PRICE_RANGE_HIGH_4)
					self.__logger.debug("Fourth price increase: %.2f" % consts.BB_SPREAD_PERCENT_INCREASE_RANGE_4)
					self.__logger.debug("Bullish candle jump: %.2f" % bullishCandleJumpArray[-1])
					return False
			if prevClosePrice >= consts.BB_PRICE_RANGE_HIGH_4:
				if float(bullishCandleJumpArray[-1] / prevClosePrice) * 100 >= consts.BB_SPREAD_PERCENT_INCREASE_RANGE_5:
					self.__logger.debug("Bullish candle jump greater than jump range")
					self.__logger.debug("Fifth price, greater than: %.2f" % consts.BB_PRICE_RANGE_HIGH_4)
					self.__logger.debug("Fifth price increase: %.2f" % consts.BB_SPREAD_PERCENT_INCREASE_RANGE_5)
					self.__logger.debug("Bullish candle jump: %.2f" % bullishCandleJumpArray[-1])
					return False

		self.__logger.debug("Price Jump check passed.")

		# Check volume 
		if (len(self.__volumeDS) < consts.VOLUME_LOOKBACK_WINDOW) or (len(self.__volumeDS) < consts.VOLUME_AVG_WINDOW):
			self.__logger.debug("Not enough entries for volume lookback or for computing average volume")
			self.__logger.debug("Volume lookback: %d" % consts.VOLUME_LOOKBACK_WINDOW)
			self.__logger.debug("Avg volume lookback: %d" % consts.VOLUME_AVG_WINDOW)
			self.__logger.debug("Number of volume entries: %d" % len(self.__volumeDS))
			return False 
		volumeArrayInLookback = xiquantFuncs.dsToNumpyArray(self.__volumeDS, consts.VOLUME_LOOKBACK_WINDOW)
		volumeArrayInAvgLookback = xiquantFuncs.dsToNumpyArray(self.__volumeDS, consts.VOLUME_AVG_WINDOW)
		if volumeArrayInLookback[-1] != volumeArrayInLookback.max():
			self.__logger.debug("Volume: %.2f" % volumeArrayInLookback[-1])
			self.__logger.debug("Max volume in lookback: %.2f" % volumeArrayInLookback.max())
			self.__logger.debug("Volume NOT greater in lookback.")
			if volumeArrayInLookback[-2] >= 0 or volumeArrayInLookback[-1] <= 0:
				avgVolume = volumeArrayInAvgLookback.sum() / consts.VOLUME_AVG_WINDOW
				if volumeArrayInLookback[-1] < avgVolume and float((avgVolume - volumeArrayInLookback[-1]) / avgVolume * 100) > consts.VOLUME_DELTA:
					return False 
		self.__logger.debug("Volume check passed.")

		# Check cash flow 
		if len(self.__priceDS) < consts.CASH_FLOW_LOOKBACK_WINDOW: 
			self.__logger.debug("Not enough entries for cashflow lookback")
			self.__logger.debug("Cashflow lookback: %d" % consts.CASH_FLOW_LOOKBACK_WINDOW)
			self.__logger.debug("Number of entries: %d" % len(self.__priceDS))
			return False
		priceArrayInLookback = xiquantFuncs.dsToNumpyArray(self.__closeDS, consts.CASH_FLOW_LOOKBACK_WINDOW)
		volumeArrayInLookback = xiquantFuncs.dsToNumpyArray(self.__volumeDS, consts.CASH_FLOW_LOOKBACK_WINDOW)
		cashFlowArrayInLookback = priceArrayInLookback * volumeArrayInLookback
		'''
		if float(cashFlowArrayInLookback[(consts.CASH_FLOW_LOOKBACK_WINDOW - 1) * -1:-1].sum() / (consts.CASH_FLOW_LOOKBACK_WINDOW -1)) <= float(cashFlowArrayInLookback[consts.CASH_FLOW_LOOKBACK_WINDOW * -1:-2].sum() / (consts.CASH_FLOW_LOOKBACK_WINDOW -1)):
			self.__logger.debug("Avg Cashflow: %.2f" % float(cashFlowArrayInLookback[(consts.CASH_FLOW_LOOKBACK_WINDOW - 1) * -1:-1].sum() / (consts.CASH_FLOW_LOOKBACK_WINDOW -1))) 
			self.__logger.debug("Avg Cashflow in lookback: %.2f" % float(cashFlowArrayInLookback[consts.CASH_FLOW_LOOKBACK_WINDOW * -1:-2].sum() / (consts.CASH_FLOW_LOOKBACK_WINDOW -1))) 
			self.__logger.debug("Cashflow check failed.")
			return False
		'''
		if self.__mfi[-1] >= 70.0:
			self.__logger.debug("Cashflow: %.2f" % cashFlowArrayInLookback[-1]) 
			self.__logger.debug("Cashflow in lookback: %.2f" % float(cashFlowArrayInLookback[:-1].sum() / (consts.CASH_FLOW_LOOKBACK_WINDOW -1))) 
			self.__logger.debug("Volume: %.2f" % volumeArrayInLookback[-1])
			self.__logger.debug("Cashflow check failed.")
			return False
		if self.__mfi_tiny[-1] < self.__mfi_tiny[-2]:
			return False

		self.__logger.debug("Avg Cashflow: %.2f" % cashFlowArrayInLookback[-1]) 
		self.__logger.debug("Avg Cashflow in lookback: %.2f" % float(cashFlowArrayInLookback[:-1].sum() / (consts.CASH_FLOW_LOOKBACK_WINDOW -1))) 
		self.__logger.debug("Volume: %.2f" % volumeArrayInLookback[-1])
		self.__logger.debug("Cashflow check passed.")

		# Check resistance
		if (len(self.__priceDS) < consts.TRADE_DAYS_IN_RESISTANCE_LOOKBACK_WINDOW):
			self.__logger.debug("Not enough entries for resistance lookback")
			self.__logger.debug("Support lookback: %d" % consts.TRADE_DAYS_IN_RESISTANCE_LOOKBACK_WINDOW)
			self.__logger.debug("Number of entries: %d" % len(self.__priceDS))
			return False
		priceArrayInLookback = xiquantFuncs.dsToNumpyArray(self.__closeDS, consts.TRADE_DAYS_IN_RESISTANCE_LOOKBACK_WINDOW)
		recentResistance = priceArrayInLookback.max()

		priceJmpRange = 0
		closePrice = bar.getClose()
		if closePrice < consts.BB_PRICE_RANGE_HIGH_1:
			priceJmpRange = float((closePrice * consts.BB_SPREAD_PERCENT_INCREASE_RANGE_1) / 100)
		if closePrice >= consts.BB_PRICE_RANGE_HIGH_1 and closePrice < consts.BB_PRICE_RANGE_HIGH_2:
			priceJmpRange = float((closePrice * consts.BB_SPREAD_PERCENT_INCREASE_RANGE_2) / 100)
		if closePrice >= consts.BB_PRICE_RANGE_HIGH_2 and closePrice < consts.BB_PRICE_RANGE_HIGH_3:
			priceJmpRange = float((closePrice * consts.BB_SPREAD_PERCENT_INCREASE_RANGE_3) / 100)
		if closePrice >= consts.BB_PRICE_RANGE_HIGH_3 and closePrice < consts.BB_PRICE_RANGE_HIGH_4:
			priceJmpRange = float((closePrice * consts.BB_SPREAD_PERCENT_INCREASE_RANGE_4) / 100)
		if closePrice >= consts.BB_PRICE_RANGE_HIGH_4:
			priceJmpRange = float((closePrice * consts.BB_SPREAD_PERCENT_INCREASE_RANGE_5) / 100)

		priceArrayInHistoricalLookback = xiquantFuncs.dsToNumpyArray(self.__closeDS, consts.TRADE_DAYS_IN_RESISTANCE_LOOKBACK_WINDOW)
		historicalResistanceDeltaArray = priceArrayInHistoricalLookback - recentResistance
		deltaUp = historicalResistanceDeltaArray.max()
		deltaDown = historicalResistanceDeltaArray.min()
		if deltaUp > 0 and deltaUp <= priceJmpRange:
			# The historical resitance should be considered
			if (recentResistance + deltaUp) - closePrice < consts.RESISTANCE_DELTA:
				self.__logger.debug("Close price to recent resistance difference less than support price delta")
				return False
		elif deltaDown < 0 and abs(deltaDown) <= priceJmpRange:
			# The recent resitance should be considered
			if recentResistance - closePrice < consts.RESISTANCE_DELTA:
				self.__logger.debug("Close price to historical resistance difference less than resistance price delta")
				return False
		# Either there's enough room for the stock to move up to the resistance or the stock is at an all time high.
		self.__logger.debug("Resistance check passed.")

		# Check price against the averages
		if abs(closePrice - self.__ema1) < consts.PRICE_AVG_CHECK_DELTA:
			return False
		if abs(closePrice - self.__ema2) < consts.PRICE_AVG_CHECK_DELTA:
			return False
		if abs(closePrice - self.__ema3) < consts.PRICE_AVG_CHECK_DELTA:
			return False
		if abs(closePrice - self.__sma1) < consts.PRICE_AVG_CHECK_DELTA:
			return False
		if abs(closePrice - self.__sma2) < consts.PRICE_AVG_CHECK_DELTA:
			return False
		self.__logger.debug("Price against averages check passed.")

		# Check RSI, should be moving through the lower limit and pointing up.
		if len(self.__rsi) < consts.RSI_SETTING:
			return False
		if (len(self.__rsi) < consts.RSI_LOOKBACK_WINDOW):
			self.__logger.debug("Not enough entries for RSI lookback")
			self.__logger.debug("RSI lookback: %d" % consts.RSI_LOOKBACK_WINDOW)
			self.__logger.debug("Number of RSI entries: %d" % len(self.__rsi))
			return False
		rsiArrayInLookback = xiquantFuncs.dsToNumpyArray(self.__rsi, consts.RSI_LOOKBACK_WINDOW)
		if rsiArrayInLookback[-1] != rsiArrayInLookback.max():
			self.__logger.debug("RSI lookback check failed.")
			return False
		#if (self.__rsi[-1] >= consts.RSI_LOWER_LIMIT):
		#	self.__logger.debug("RSI still not less/equal to Oversold.")
		#	return False
		self.__logger.debug("RSI check passed.")

		# Check MACD, should show no divergence with the price chart in the lookback window
		if len(self.__priceDS) < consts.MACD_PRICE_DVX_LOOKBACK:
			self.__logger.debug("Not enough entries for MACD lookback")
			self.__logger.debug("MACD lookback: %d" % consts.MACD_PRICE_DVX_LOOKBACK)
			self.__logger.debug("Number of MACD entries: %d" % len(self.__priceDS))
			return False
		highPriceArray = xiquantFuncs.dsToNumpyArray(self.__highPriceDS, consts.MACD_PRICE_DVX_LOOKBACK)
		macdArray = self.__macd[consts.MACD_PRICE_DVX_LOOKBACK * -1:]
		#if macdArray[-1] < self.__emaSignal[-1]:
		#	return False
		#if divergence.dvx_impl(highPriceArray, macdArray, (-1 * consts.MACD_PRICE_DVX_LOOKBACK), -1, consts.MACD_CHECK_HIGHS):
		#	self.__logger.debug("Divergence in MACD and price highs detected")
		#	return False
		self.__logger.debug("MACD check passed.")

		# Check DMI+ and DMI-
		if len(self.__dmiPlus) <= consts.DMI_PERIOD or len(self.__dmiMinus) <= consts.DMI_PERIOD:
			self.__logger.debug("Not enough entries for DMI check")
			self.__logger.debug("DMI setting: %d" % consts.DMI_PERIOD)
			self.__logger.debug("Number of DMI entries: %d" % len(self.__dmiPlus))
			return False
		# Add the code to give higher priority for investment to cases when both the conditions are satisfied.
		if (self.__dmiPlus[-1] <= self.__dmiPlus[-2]):
			self.__logger.debug("DMI Plus not pointing up.")
			return False
		if (self.__dmiMinus[-1] >= self.__dmiMinus[-2]):
			self.__logger.debug("DMI Minus not pointing down.")
			return False
		self.__logger.debug("DMI check passed.")

		# Add checks for other indicators here
		############
		return True

	def enterShortSignal(self, bar):
		# Both the bands MUST open up like a crocodile mouth.
		if self.__inpStrategy["BB_Spread_Put"]["BB_Upper_And_BB_Lower"]["AND"][0] == "BB_Upper_Croc_Open" and \
			self.__inpStrategy["BB_Spread_Put"]["BB_Upper_And_BB_Lower"]["AND"][1] == "BB_Lower_Croc_Open":
			if len(self.__lowerBBDataSeries) > consts.BB_SLOPE_LOOKBACK_WINDOW:
				normLowerBand = xiquantFuncs.normalize(self.__lowerBBDataSeries[-1], self.__smaLowerTiny[-1], self.__stdDevLower[-1])
				normPrevLowerBand = xiquantFuncs.normalize(self.__lowerBBDataSeries[-2], self.__smaLowerTiny[-2], self.__stdDevLower[-2])
				lowerSlope = xiquantFuncs.slope(normLowerBand, normPrevLowerBand)
				self.__logger.debug("Lower Slope: %0.2f" % lowerSlope)
		
			if len(self.__upperBBDataSeries) >= consts.BB_SLOPE_LOOKBACK_WINDOW:
				normUpperBand = xiquantFuncs.normalize(self.__upperBBDataSeries[-1], self.__smaUpperTiny[-1], self.__stdDevUpper[-1])
				normPrevUpperBand = xiquantFuncs.normalize(self.__upperBBDataSeries[-2], self.__smaUpperTiny[-2], self.__stdDevUpper[-2])
				upperSlope = xiquantFuncs.slope(normUpperBand, normPrevUpperBand)
				self.__logger.debug("Upper Slope: %0.2f" % upperSlope)
		
			upperBandDelta = xiquantFuncs.computeStopPriceDelta(self.__upperBBDataSeries[-1]) * consts.BB_SPREAD_EXIT_TIGHTEN_PRICE_FACTOR
			#if upperSlope >= consts.BB_CROC_SLOPE and self.__upperBBDataSeries[-1] > self.__upperBBDataSeries[-2] and self.__upperBBDataSeries[-1] - self.__upperBBDataSeries[-2] > upperBandDelta:
			if upperSlope >= consts.BB_CROC_SLOPE and self.__upperBBDataSeries[-1] > self.__upperBBDataSeries[-2]:
				if (self.__bbFirstUpperCrocDay != None) and (self.__bbFirstUpperCrocDay != xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-1])):
					self.__logger.debug("Not the first day of upper band croc mouth opening")
					return False
				else:
					self.__bbFirstUpperCrocDay = xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-1])
					self.__logger.debug("First day of upper band croc mouth opening: %s" % self.__bbFirstUpperCrocDay)
		
			lowerBandDelta = xiquantFuncs.computeStopPriceDelta(self.__lowerBBDataSeries[-1]) * consts.BB_SPREAD_EXIT_TIGHTEN_PRICE_FACTOR
			#if lowerSlope <= -1 * consts.BB_CROC_SLOPE and self.__lowerBBDataSeries[-1] < self.__lowerBBDataSeries[-2] and self.__lowerBBDataSeries[-2] - self.__lowerBBDataSeries[-1] > lowerBandDelta:
			if lowerSlope <= -1 * consts.BB_CROC_SLOPE and self.__lowerBBDataSeries[-1] < self.__lowerBBDataSeries[-2]:
				if (self.__bbFirstLowerCrocDay != None) and (self.__bbFirstLowerCrocDay != xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-1])):
					self.__logger.debug("Not the first day of lower band croc mouth opening")
					return False
				else:
					self.__bbFirstLowerCrocDay = xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-1])
					self.__logger.debug("First day of lower band croc mouth opening: %s" % self.__bbFirstLowerCrocDay)
		
			#if upperSlope < consts.BB_CROC_SLOPE or lowerSlope > -1 * consts.BB_CROC_SLOPE or self.__lowerBBDataSeries[-1] > self.__lowerBBDataSeries[-2] or self.__lowerBBDataSeries[-2] - self.__lowerBBDataSeries[-1] < lowerBandDelta or self.__upperBBDataSeries[-1] < self.__upperBBDataSeries[-2] or self.__upperBBDataSeries[-1] - self.__upperBBDataSeries[-2] < upperBandDelta:
			if upperSlope < consts.BB_CROC_SLOPE or lowerSlope > -1 * consts.BB_CROC_SLOPE or self.__lowerBBDataSeries[-1] > self.__lowerBBDataSeries[-2] or self.__upperBBDataSeries[-1] < self.__upperBBDataSeries[-2]:
				self.__logger.debug("Not a croc mouth opening")
				return False

		# This should be the first day of the Bands opening as croc mouth.
		if self.__inpStrategy["BB_Spread_Put"]["BB_Upper_And_BB_Lower"]["AND"][2] == "BB_First_Croc_Open":
			if (self.__bbFirstCrocDay != None) and (self.__bbFirstCrocDay != xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-1])):
				self.__logger.debug("Not the first day of croc mouth opening")
				return False
			if (self.__bbFirstUpperCrocDay != None) and (self.__bbFirstUpperCrocDay != xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-1])):
				self.__logger.debug("Not the first day of croc mouth opening")
				return False
			if (self.__bbFirstLowerCrocDay != None) and (self.__bbFirstLowerCrocDay != xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-1])):
				self.__logger.debug("Not the first day of croc mouth opening")
				return False

		# Set this as the first day of the croc mouth opening
		self.__bbFirstCrocDay = xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-1])
		self.__logger.debug("The first day of croc mouth opening: %s" % self.__bbFirstCrocDay)

		# Check if we will play short for this strategy or not.
		if consts.BB_SPREAD_LONG_OR_SHORT.lower() == 'long':
			self.__logger.debug("We are not playing short.")
			return False

		# Check if tomorrow is the earnings announcement, as we don't trade on the day after the earnings
		# announcement. If the earnings are announced before the market open or during, we don't trade on
		# that day. If the earnings are announced after the close of market, we don't trade the next day.
		if xiquantFuncs.isEarnings(self.__earningsCal, bar.getDateTime().date()):
			self.__logger.debug("%s: Earnings day today, so don't enter." % bar.getDateTime())
			return False

		# Check if we already hold a position in this instrument
		if self.__shortPos != None:
			self.__logger.debug("We already hold a position in %s" % self.__instrument)
			return False

		# For any instrument, we trade on the same side of the market, so check the market sentiment first
		if not self.__instrument.upper() in self.__SPYExceptions:
			if consts.SPY_CHECK and self.isBullish():
				self.__logger.debug("The market is Bullish so we will not try to go short.")
				return False
		else:
			self.__logger.debug("%s is in the exceptions list, so we check if the tech sector is Bullish or Bearish today." % self.__instrument)
			if consts.QQQ_CHECK and self.isTechBullish():
				self.__logger.debug("The tech sector is Bullish so we will not try to go short.")
				return False

		# Check if close breaches or bounces off of the lower band.
		self.__bandBreachOrTouch = False
		if self.__inpStrategy["BB_Spread_Put"]["BB_Upper_And_BB_Lower"]["OR"][0] == "BB_Lower_Breach":
			if bar.getClose() < self.__bb_lower:
				self.__bandBreachOrTouch = True
				self.__logger.debug("Lower band breached.")
				self.__logger.debug("Close Price: %.2f" % bar.getClose())
				self.__logger.debug("Lower band: %.2f" % self.__bb_lower)
			elif self.__inpStrategy["BB_Spread_Put"]["BB_Upper_And_BB_Lower"]["OR"][1] == "BB_Lower_Touch":
				# The close price may not exactly touch the lower band so we will have to
				# include some variance parameter
				if bar.getClose() == self.__bb_lower:
					self.__bandBreachOrTouch = True
					self.__logger.debug("Lower band touched.")
					self.__logger.debug("Close Price: %.2f" % bar.getClose())
					self.__logger.debug("Lower band: %.2f" % self.__bb_lower)
				else:
					self.__bandBreachOrTouch = False
					self.__logger.debug("NO lower band breach/touch.")
					self.__noBandBreachOrTouchEntryPrice = self.__bb_lower - consts.PRICE_DELTA
					return False

		### Change to lookback window specific code.
		# Check if first breach in the lookback.
		if self.__inpStrategy["BB_Spread_Put"]["BB_Upper_And_BB_Lower"]["OR"][0] == "BB_Lower_Breach" or self.__inpStrategy["BB_Spread_Put"]["BB_Upper_And_BB_Lower"]["OR"][1] == "BB_Lower_Touch":
			if self.__closeDS[-2] < self.__lowerBBDataSeries[-2]:
				self.__logger.debug("Not the first day of lower band breach/touch.")
				self.__logger.debug("Lower band: %.2f" % self.__lowerBBDataSeries[-1])
				self.__logger.debug("Price: %.2f" % self.__closeDS[-1])
				precPrevLowerBand = float("%0.2f" % self.__lowerBBDataSeries[-2])
				self.__logger.debug("Previous lower band: %.4f" % precPrevLowerBand)
				#self.__logger.debug("Previous lower band: %.4f" % Decimal(self.__lowerBBDataSeries[-2]))
				self.__logger.debug("Previous price: %.2f" % self.__closeDS[-2])
				return False

		# Check the price jump
		# +1 because we need one additional entry to compute the candle jump
		if (len(self.__closeDS) < consts.PRICE_JUMP_LOOKBACK_WINDOW + 1):
			self.__logger.debug("Not enough entires for Price Jump check lookback.")
			self.__logger.debug("Lookback: %d" % consts.PRICE_JUMP_LOOKBACK_WINDOW)
			self.__logger.debug("Entries: %d" % len(self.__closeDS))
			return False
		if self.__closeDS[-1] > self.__closeDS[-2]:
			self.__logger.debug("Close price not lower than the previous close.")
			self.__logger.debug("Close price: %.2f" % self.__closeDS[-1])
			self.__logger.debug("Close price: %.2f" % self.__closeDS[-2])
			return False
		openArrayInLookback = xiquantFuncs.dsToNumpyArray(self.__openDS, consts.PRICE_JUMP_LOOKBACK_WINDOW)
		closeArrayInLookback = xiquantFuncs.dsToNumpyArray(self.__closeDS, consts.PRICE_JUMP_LOOKBACK_WINDOW + 1)
		prevCloseArrayInLookback = closeArrayInLookback[:-1]
		bearishCandleJumpArray = prevCloseArrayInLookback - openArrayInLookback 
		### Add the logic if more than the last day's bullish candle needs to be evaluated.
		if bearishCandleJumpArray[-1] <=0:
			self.__logger.debug("Bearish candle jump: %.2f" % bearishCandleJumpArray[-1])
			self.__logger.debug("Continue with other indicator checks")
		else:
			self.__logger.debug("Bearish candle jump: %.2f" % bearishCandleJumpArray[-1])
			prevClosePrice = self.__closeDS[-2]
			self.__logger.debug("Prev Close Price: %.2f" % prevClosePrice)
			if prevClosePrice < consts.BB_PRICE_RANGE_HIGH_1:
				if float(bearishCandleJumpArray[-1] / prevClosePrice) * 100 >= consts.BB_SPREAD_PERCENT_INCREASE_RANGE_1:
					self.__logger.debug("Bearish candle jump greater than jump range")
					self.__logger.debug("First price: %.2f" % consts.BB_PRICE_RANGE_HIGH_1)
					self.__logger.debug("First price increase: %.2f" % consts.BB_SPREAD_PERCENT_INCREASE_RANGE_1)
					self.__logger.debug("Bearish candle jump: %.2f" % bearishCandleJumpArray[-1])
					return False
			if prevClosePrice >= consts.BB_PRICE_RANGE_HIGH_1 and prevClosePrice < consts.BB_PRICE_RANGE_HIGH_2:
				if float(bearishCandleJumpArray[-1] / prevClosePrice) * 100 >= consts.BB_SPREAD_PERCENT_INCREASE_RANGE_2:
					self.__logger.debug("Bearish candle jump greater than jump range")
					self.__logger.debug("Second price: %.2f" % consts.BB_PRICE_RANGE_HIGH_2)
					self.__logger.debug("Second price increase: %.2f" % consts.BB_SPREAD_PERCENT_INCREASE_RANGE_2)
					self.__logger.debug("Bearish candle jump: %.2f" % bearishCandleJumpArray[-1])
					return False
			if prevClosePrice >= consts.BB_PRICE_RANGE_HIGH_2 and prevClosePrice < consts.BB_PRICE_RANGE_HIGH_3:
				if float(bearishCandleJumpArray[-1] / prevClosePrice) * 100 >= consts.BB_SPREAD_PERCENT_INCREASE_RANGE_3:
					self.__logger.debug("Bearish candle jump greater than jump range")
					self.__logger.debug("Third price: %.2f" % consts.BB_PRICE_RANGE_HIGH_3)
					self.__logger.debug("Third price increase: %.2f" % consts.BB_SPREAD_PERCENT_INCREASE_RANGE_3)
					self.__logger.debug("Bearish candle jump: %.2f" % bearishCandleJumpArray[-1])
					return False
			if prevClosePrice >= consts.BB_PRICE_RANGE_HIGH_3 and prevClosePrice < consts.BB_PRICE_RANGE_HIGH_4:
				if float(bearishCandleJumpArray[-1] / prevClosePrice) * 100 >= consts.BB_SPREAD_PERCENT_INCREASE_RANGE_4:
					self.__logger.debug("Bearish candle jump greater than jump range")
					self.__logger.debug("Fourth price: %.2f" % consts.BB_PRICE_RANGE_HIGH_4)
					self.__logger.debug("Fourth price increase: %.2f" % consts.BB_SPREAD_PERCENT_INCREASE_RANGE_4)
					self.__logger.debug("Bearish candle jump: %.2f" % bearishCandleJumpArray[-1])
					return False
			if prevClosePrice >= consts.BB_PRICE_RANGE_HIGH_4:
				if float(bearishCandleJumpArray[-1] / prevClosePrice) * 100 >= consts.BB_SPREAD_PERCENT_INCREASE_RANGE_5:
					self.__logger.debug("Bearish candle jump greater than jump range")
					self.__logger.debug("Fifth price, greater than: %.2f" % consts.BB_PRICE_RANGE_HIGH_4)
					self.__logger.debug("Fifth price increase: %.2f" % consts.BB_SPREAD_PERCENT_INCREASE_RANGE_5)
					self.__logger.debug("Bearish candle jump: %.2f" % bearishCandleJumpArray[-1])
					return False

		self.__logger.debug("Price Jump check passed.")

		# Check volume 
		if (len(self.__volumeDS) < consts.VOLUME_LOOKBACK_WINDOW) or (len(self.__volumeDS) < consts.VOLUME_AVG_WINDOW):
			self.__logger.debug("Not enough entries for volume lookback")
			self.__logger.debug("Volume lookback: %d" % consts.VOLUME_LOOKBACK_WINDOW)
			self.__logger.debug("Avg volume lookback: %d" % consts.VOLUME_AVG_WINDOW)
			self.__logger.debug("Number of volume entries: %d" % len(self.__volumeDS))
			return False 
		volumeArrayInLookback = xiquantFuncs.dsToNumpyArray(self.__volumeDS, consts.VOLUME_LOOKBACK_WINDOW)
		volumeArrayInAvgLookback = xiquantFuncs.dsToNumpyArray(self.__volumeDS, consts.VOLUME_AVG_WINDOW)
		if volumeArrayInLookback[-1] != volumeArrayInLookback.max():
			self.__logger.debug("Volume: %.2f" % volumeArrayInLookback[-1])
			self.__logger.debug("Max volume in lookback: %.2f" % volumeArrayInLookback.max())
			self.__logger.debug("Volume NOT greater in lookback.")
			if volumeArrayInLookback[-2] <= 0 or volumeArrayInLookback[-1] >= 0:
				avgVolume = volumeArrayInAvgLookback.sum() / consts.VOLUME_AVG_WINDOW
				if volumeArrayInLookback[-1] < avgVolume and float((avgVolume - volumeArrayInLookback[-1]) / avgVolume * 100) > consts.VOLUME_DELTA:
					return False 

		self.__logger.debug("Volume check passed.")
		# Check cash flow 
		if len(self.__priceDS) < consts.CASH_FLOW_LOOKBACK_WINDOW: 
			self.__logger.debug("Not enough entries for cashflow lookback")
			self.__logger.debug("Cashflow lookback: %d" % consts.CASH_FLOW_LOOKBACK_WINDOW)
			self.__logger.debug("Number of entries: %d" % len(self.__priceDS))
			return False
		priceArrayInLookback = xiquantFuncs.dsToNumpyArray(self.__closeDS, consts.CASH_FLOW_LOOKBACK_WINDOW)
		volumeArrayInLookback = xiquantFuncs.dsToNumpyArray(self.__volumeDS, consts.CASH_FLOW_LOOKBACK_WINDOW)
		cashFlowArrayInLookback = priceArrayInLookback * volumeArrayInLookback
		'''
		if float(cashFlowArrayInLookback[(consts.CASH_FLOW_LOOKBACK_WINDOW - 1) * -1:-1].sum() / (consts.CASH_FLOW_LOOKBACK_WINDOW -1)) >= float(cashFlowArrayInLookback[consts.CASH_FLOW_LOOKBACK_WINDOW * -1:-2].sum() / (consts.CASH_FLOW_LOOKBACK_WINDOW -1)):
			self.__logger.debug("Avg Cashflow: %.2f" % float(cashFlowArrayInLookback[(consts.CASH_FLOW_LOOKBACK_WINDOW - 1) * -1:-1].sum() / (consts.CASH_FLOW_LOOKBACK_WINDOW -1))) 
			self.__logger.debug("Avg Cashflow in lookback: %.2f" % float(cashFlowArrayInLookback[consts.CASH_FLOW_LOOKBACK_WINDOW * -1:-2].sum() / (consts.CASH_FLOW_LOOKBACK_WINDOW -1))) 
			self.__logger.debug("Cashflow check failed.")
			return False
		'''
		if  self.__mfi[-1] >= 30.0:
			self.__logger.debug("Cashflow: %.2f" % cashFlowArrayInLookback[-1]) 
			self.__logger.debug("Cashflow in lookback: %.2f" % float(cashFlowArrayInLookback[:-1].sum() / (consts.CASH_FLOW_LOOKBACK_WINDOW -1))) 
			self.__logger.debug("Volume: %.2f" % volumeArrayInLookback[-1])
			self.__logger.debug("Cashflow check failed.")
			return False
	
		if self.__mfi_tiny[-1] > self.__mfi_tiny[-2]:
			return False

		self.__logger.debug("Avg Cashflow: %.2f" % cashFlowArrayInLookback[-1]) 
		self.__logger.debug("Avg Cashflow in lookback: %.2f" % float(cashFlowArrayInLookback[:-1].sum() / (consts.CASH_FLOW_LOOKBACK_WINDOW -1))) 
		self.__logger.debug("Volume: %.2f" % volumeArrayInLookback[-1])
		self.__logger.debug("Cashflow check passed.")

		# Check support
		if (len(self.__priceDS) < consts.SUPPORT_LOOKBACK_WINDOW):
			self.__logger.debug("Not enough entries for support lookback")
			self.__logger.debug("Support lookback: %d" % consts.SUPPORT_LOOKBACK_WINDOW)
			self.__logger.debug("Number of entries: %d" % len(self.__priceDS))
			return False
		priceArrayInLookback = xiquantFuncs.dsToNumpyArray(self.__closeDS, consts.SUPPORT_RECENT_LOOKBACK_WINDOW)
		recentSupport = priceArrayInLookback.min()

		priceJmpRange = 0
		closePrice = bar.getClose()
		if closePrice < consts.BB_PRICE_RANGE_HIGH_1:
			priceJmpRange = float((closePrice * consts.BB_SPREAD_PERCENT_INCREASE_RANGE_1) / 100)
		if closePrice >= consts.BB_PRICE_RANGE_HIGH_1 and closePrice < consts.BB_PRICE_RANGE_HIGH_2:
			priceJmpRange = float((closePrice * consts.BB_SPREAD_PERCENT_INCREASE_RANGE_2) / 100)
		if closePrice >= consts.BB_PRICE_RANGE_HIGH_2 and closePrice < consts.BB_PRICE_RANGE_HIGH_3:
			priceJmpRange = float((closePrice * consts.BB_SPREAD_PERCENT_INCREASE_RANGE_3) / 100)
		if closePrice >= consts.BB_PRICE_RANGE_HIGH_3 and closePrice < consts.BB_PRICE_RANGE_HIGH_4:
			priceJmpRange = float((closePrice * consts.BB_SPREAD_PERCENT_INCREASE_RANGE_4) / 100)
		if closePrice >= consts.BB_PRICE_RANGE_HIGH_4:
			priceJmpRange = float((closePrice * consts.BB_SPREAD_PERCENT_INCREASE_RANGE_5) / 100)

		priceArrayInHistoricalLookback = xiquantFuncs.dsToNumpyArray(self.__closeDS, consts.SUPPORT_LOOKBACK_WINDOW)
		historicalSupportDeltaArray = priceArrayInHistoricalLookback - recentSupport
		deltaUp = historicalSupportDeltaArray.max()
		deltaDown = historicalSupportDeltaArray.min()
		if deltaUp > 0 and deltaUp <= priceJmpRange:
			# The recent support should be considered
			if closePrice - recentSupport < consts.SUPPORT_DELTA:
				self.__logger.debug("Close price to recent support difference less than support price delta")
				return False
		elif deltaDown < 0 and abs(deltaDown) <= priceJmpRange:
			# The historical support should be considered
			if closePrice - (recentSupport + deltaDown) < consts.SUPPORT_DELTA:
				self.__logger.debug("Close price to historical support difference less than support price delta")
				return False
		# Either there's enough room for the stock to move down to the support or the stock is at an all time low.
		self.__logger.debug("Support check passed.")

		# Check price against the averages
		if abs(closePrice - self.__ema1) < consts.PRICE_AVG_CHECK_DELTA:
			return False
		if abs(closePrice - self.__ema2) < consts.PRICE_AVG_CHECK_DELTA:
			return False
		if abs(closePrice - self.__ema3) < consts.PRICE_AVG_CHECK_DELTA:
			return False
		if abs(closePrice - self.__sma1) < consts.PRICE_AVG_CHECK_DELTA:
			return False
		if abs(closePrice - self.__sma2) < consts.PRICE_AVG_CHECK_DELTA:
			return False
		self.__logger.debug("Price against averages check passed.")

		# Check RSI, should be moving through the upper limit and pointing down.
		if len(self.__rsi) < consts.RSI_SETTING:
			return False
		if (len(self.__rsi) < consts.RSI_LOOKBACK_WINDOW):
			self.__logger.debug("Not enough entries for RSI lookback")
			self.__logger.debug("RSI lookback: %d" % consts.RSI_LOOKBACK_WINDOW)
			self.__logger.debug("Number of RSI entries: %d" % len(self.__rsi))
			return False
		rsiArrayInLookback = xiquantFuncs.dsToNumpyArray(self.__rsi, consts.RSI_LOOKBACK_WINDOW)
		if rsiArrayInLookback[-1] != rsiArrayInLookback.min():
			self.__logger.debug("RSI lookback check failed.")
			return False
		#if (self.__rsi[-1] <= consts.RSI_UPPER_LIMIT):
		#	self.__logger.debug("RSI still not greater/equal to Overbought.")
		#	return False
		self.__logger.debug("RSI check passed.")

		# Check MACD, should show no divergence with the price chart in the lookback window
		if len(self.__priceDS) < consts.MACD_PRICE_DVX_LOOKBACK:
			self.__logger.debug("Not enough entries for MACD lookback")
			self.__logger.debug("MACD lookback: %d" % consts.MACD_PRICE_DVX_LOOKBACK)
			self.__logger.debug("Number of MACD entries: %d" % len(self.__priceDS))
			return False
		lowPriceArray = xiquantFuncs.dsToNumpyArray(self.__lowPriceDS, consts.MACD_PRICE_DVX_LOOKBACK)
		macdArray = self.__macd[consts.MACD_PRICE_DVX_LOOKBACK * -1:]
		#if macdArray[-1] > self.__emaSignal[-1]:
		#	return False
		#if divergence.dvx_impl(lowPriceArray, macdArray, (-1 * consts.MACD_PRICE_DVX_LOOKBACK), -1, consts.MACD_CHECK_LOWS):
		#	self.__logger.debug("Divergence in MACD and price lows detected")
		#	return False
		#self.__logger.debug("MACD check passed.")

		# Check DMI+ and DMI-
		if len(self.__dmiPlus) <= consts.DMI_PERIOD or len(self.__dmiMinus) <= consts.DMI_PERIOD:
			self.__logger.debug("Not enough entries for DMI check")
			self.__logger.debug("DMI setting: %d" % consts.DMI_PERIOD)
			self.__logger.debug("Number of DMI entries: %d" % len(self.__dmiPlus))
			return False
		# Add the code to give higher priority for investment to cases when both the conditions are satisfied.
		if (self.__dmiPlus[-1] >= self.__dmiPlus[-2]):
			self.__logger.debug("DMI Plus not pointing down.")
			return False
		if (self.__dmiMinus[-1] <= self.__dmiMinus[-2]):
			self.__logger.debug("DMI Minus not pointing up.")
			return False
		self.__logger.debug("DMI check passed.")

		# Add checks for other indicators here
		############

		return True

	def exitLongSignal(self, bar):
		if len(self.__lowerBBDataSeries) >= consts.BB_SLOPE_LOOKBACK_WINDOW:
			lowerBand = self.__lowerBBDataSeries[-1]
			prevLowerBand = self.__lowerBBDataSeries[-2]
			self.__logger.debug("Previous lower band: %.4f" % prevLowerBand)
			normLowerBand = xiquantFuncs.normalize(lowerBand, self.__smaLowerTiny[-1], self.__stdDevLower[-1])
			normPrevLowerBand = xiquantFuncs.normalize(prevLowerBand, self.__smaLowerTiny[-2], self.__stdDevLower[-2])
			lowerSlope = xiquantFuncs.slope(normLowerBand, normPrevLowerBand)
			self.__logger.debug("Lower Slope: %0.2f" % lowerSlope)
			lowerBandDelta = xiquantFuncs.computeStopPriceDelta(lowerBand) * consts.BB_SPREAD_EXIT_TIGHTEN_PRICE_FACTOR
			#if lowerBand > prevLowerBand or prevLowerBand - lowerBand < lowerBandDelta:
			if lowerBand > prevLowerBand:
				# Reset the first croc mouth opening marker as the mouth is begin to close
				self.__logger.debug("Reset first croc opening day")
				self.__bbFirstCrocDay = None
				self.__logger.debug("Reset first lower croc opening day")
				self.__bbFirstLowerCrocDay = None

		# Check if we hold a position in this instrument or not
		if self.__longPos == None or self.__longPos.getShares() == 0:
				return False
		self.__logger.debug("We hold a position in %s" % self.__instrument)
		self.__portfolioCashBefore = self.getBroker().getCash(includeShort=False)

		# We don't explicitly exit but based on the indicators we just tighten the stop loss orders.
		# The only exception to that rule is the earnings date -- we exit at the market open if earnings
		# will be announced after the close of market or before the open of, or during, the next day.
		if xiquantFuncs.isEarnings(self.__earningsCal, bar.getDateTime().date()):
			self.__logger.debug("%s: Earnings day today, so exit." % bar.getDateTime())
			return True

		exitPriceDelta = 0
		closePrice = bar.getClose()
		if closePrice < consts.BB_SPREAD_EXIT_PRICE_RANGE_HIGH_1:
			exitPriceDelta = consts.BB_SPREAD_EXIT_PRICE_DELTA_1
		if closePrice >= consts.BB_SPREAD_EXIT_PRICE_RANGE_HIGH_1 and closePrice < consts.BB_SPREAD_EXIT_PRICE_RANGE_HIGH_2:
			exitPriceDelta = consts.BB_SPREAD_EXIT_PRICE_DELTA_2
		if closePrice >= consts.BB_SPREAD_EXIT_PRICE_RANGE_HIGH_2 and closePrice < consts.BB_SPREAD_EXIT_PRICE_RANGE_HIGH_3:
			exitPriceDelta = consts.BB_SPREAD_EXIT_PRICE_DELTA_3
		if closePrice >= consts.BB_SPREAD_EXIT_PRICE_RANGE_HIGH_3 and closePrice < consts.BB_SPREAD_EXIT_PRICE_RANGE_HIGH_4:
			exitPriceDelta = consts.BB_SPREAD_EXIT_PRICE_DELTA_4
		if closePrice >= consts.BB_SPREAD_EXIT_PRICE_RANGE_HIGH_4:
			exitPriceDelta = consts.BB_SPREAD_EXIT_PRICE_DELTA_5

		# Since we are tightening the stop losses, a factor needs to be applied to
		# the stop loss price deltas.
		exitPriceDelta = float(exitPriceDelta * consts.BB_SPREAD_EXIT_TIGHTEN_PRICE_FACTOR)
		self.__adjRatio = self.__priceDS[-1] / bar.getAdjClose()

		#if Decimal(lowerBand) > Decimal(prevLowerBand):
		#if precLowerBand > precPrevLowerBand:
		#if lowerSlope > consts.BB_SLOPE_LIMIT_FOR_CURVING:
		if lowerBand > prevLowerBand:
			# Tighten the stop loss order
			if bar.getOpen() <= bar.getClose():
				# Bullish candle
				stopPrice = bar.getOpen() - exitPriceDelta
			else:
				# Bearish candle
				stopPrice = bar.getClose() - exitPriceDelta
			# Cancel the exiting stop loss order before placing a new one
			self.__longPos.cancelExit()
			# Adjust the stop price based on the last day of the backtesting period
			self.__adjStopPrice = stopPrice * self.__adjRatio
			self.__longPos.exitStop(self.__adjStopPrice, True)
			t = bar.getDateTime()
			tInSecs = xiquantFuncs.secondsSinceEpoch(t + datetime.timedelta(seconds=2))
			existingOrdersForTime = self.__orders.setdefault(tInSecs, [])
			existingOrdersForTime.append((self.__instrument, 'Tightened-Stop-Sell', self.__adjStopPrice, consts.DUMMY_ADJ_RATIO, consts.DUMMY_RANK))
			self.__orders[tInSecs] = existingOrdersForTime
			self.__logger.info("%s: Tightened Stop Loss SELL order, due to lower band curving in, of %d %s shares set to %.2f" % (self.getCurrentDateTime(), self.__longPos.getShares(), self.__instrument, self.__adjStopPrice))
			self.__entryDayStopPrice = self.__adjStopPrice
			#return False
		else:
			stopPrice = self.__entryDayStopPrice
			# No need to adjust the stop price as the entry was based on the adjusted price.
			self.__adjStopPrice = stopPrice

			self.__longPos.cancelExit()
			self.__longPos.exitStop(self.__adjStopPrice, True)
			t = bar.getDateTime()
			tInSecs = xiquantFuncs.secondsSinceEpoch(t + datetime.timedelta(seconds=2))
			existingOrdersForTime = self.__orders.setdefault(tInSecs, [])
			existingOrdersForTime.append((self.__instrument, 'Stop-Sell', self.__adjStopPrice, consts.DUMMY_ADJ_RATIO, consts.DUMMY_RANK))
			self.__orders[tInSecs] = existingOrdersForTime
			self.__logger.info("%s: New Stop Loss SELL order for %d %s shares set to %.2f" % (self.getCurrentDateTime(), self.__longPos.getShares(), self.__instrument, self.__adjStopPrice))

		if (self.__entryDay == xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-1])) or (self.__entryDay == xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-2])):
			# The stop loss order for the entry day and the day after has already been set.
			self.__logger.debug("Analysis Day in %s" % self.__instrument)
			return False
		# Not the entry or the next day, so reset entry day
		self.__entryDay = None
		return False
		
	def exitShortSignal(self, bar):
		if len(self.__upperBBDataSeries) >= consts.BB_SLOPE_LOOKBACK_WINDOW:
			upperBand = self.__upperBBDataSeries[-1]
			prevUpperBand = self.__upperBBDataSeries[-2]
			self.__logger.debug("Previous upper band: %.4f" % prevUpperBand)
			normUpperBand = xiquantFuncs.normalize(upperBand, self.__smaUpperTiny[-1], self.__stdDevUpper[-1])
			normPrevUpperBand = xiquantFuncs.normalize(prevUpperBand, self.__smaUpperTiny[-2], self.__stdDevUpper[-2])
			upperSlope = xiquantFuncs.slope(normUpperBand, normPrevUpperBand)
			self.__logger.debug("Upper Slope: %0.2f" % upperSlope)
			upperBandDelta = xiquantFuncs.computeStopPriceDelta(upperBand) * consts.BB_SPREAD_EXIT_TIGHTEN_PRICE_FACTOR
			#if upperBand < prevUpperBand or upperBand - prevUpperBand < upperBandDelta:
			if upperBand < prevUpperBand:
				# Reset the first croc mouth opening marker as the mouth is begin to close
				self.__logger.debug("Reset first croc opening day")
				self.__bbFirstCrocDay = None
				self.__logger.debug("Reset first upper croc opening day")
				self.__bbFirstUpperCrocDay = None

		# Check if we hold a position in this instrument or not
		if self.__shortPos == None or self.__shortPos.getShares() == 0:
			return False
		self.__logger.debug("We hold a position in %s" % self.__instrument)
		self.__portfolioCashBefore = self.getBroker().getCash(includeShort=False)

		# We don't explicitly exit but based on the indicators we just tighten the stop loss orders.
		# The only exception to that rule is the earnings date -- we exit at the market open if earnings
		# will be announced after the close of market or before the open of, or during, the next day.
		if xiquantFuncs.isEarnings(self.__earningsCal, bar.getDateTime().date()):
			self.__logger.debug("%s: Earnings day today, so exit." % bar.getDateTime())
			return True

		# We don't explicitly exit but based on the indicators we just tighten the stop loss orders.
		exitPriceDelta = 0
		closePrice = bar.getClose()
		if closePrice < consts.BB_SPREAD_EXIT_PRICE_RANGE_HIGH_1:
			exitPriceDelta = consts.BB_SPREAD_EXIT_PRICE_DELTA_1
		if closePrice >= consts.BB_SPREAD_EXIT_PRICE_RANGE_HIGH_1 and closePrice < consts.BB_SPREAD_EXIT_PRICE_RANGE_HIGH_2:
			exitPriceDelta = consts.BB_SPREAD_EXIT_PRICE_DELTA_2
		if closePrice >= consts.BB_SPREAD_EXIT_PRICE_RANGE_HIGH_2 and closePrice < consts.BB_SPREAD_EXIT_PRICE_RANGE_HIGH_3:
			exitPriceDelta = consts.BB_SPREAD_EXIT_PRICE_DELTA_3
		if closePrice >= consts.BB_SPREAD_EXIT_PRICE_RANGE_HIGH_3 and closePrice < consts.BB_SPREAD_EXIT_PRICE_RANGE_HIGH_4:
			exitPriceDelta = consts.BB_SPREAD_EXIT_PRICE_DELTA_4
		if closePrice >= consts.BB_SPREAD_EXIT_PRICE_RANGE_HIGH_4:
			exitPriceDelta = consts.BB_SPREAD_EXIT_PRICE_DELTA_5

		# Since we are tightening the stop losses, a factor needs to be applied to
		# the stop loss price deltas.
		exitPriceDelta = float(exitPriceDelta * consts.BB_SPREAD_EXIT_TIGHTEN_PRICE_FACTOR)
		self.__adjRatio = self.__priceDS[-1] / bar.getAdjClose()

		#if Decimal(upperBand) < Decimal(prevUpperBand):
		#if precUpperBand < precPrevUpperBand:
		#if upperSlope < consts.BB_SLOPE_LIMIT_FOR_CURVING:
		if upperBand < prevUpperBand:
			# Tighten the stop loss order
			if bar.getOpen() <= bar.getClose():
				# Bullish candle
				stopPrice = bar.getClose() + exitPriceDelta
			else:
				# Bearish candle
				stopPrice = bar.getOpen() + exitPriceDelta
			# Cancel the exiting stop loss order before placing a new one
			self.__shortPos.cancelExit()
			# Adjust the stop price based on the last day of the backtesting period
			self.__adjStopPrice = stopPrice * self.__adjRatio
			self.__shortPos.exitStop(self.__adjStopPrice, True)
			t = bar.getDateTime()
			tInSecs = xiquantFuncs.secondsSinceEpoch(t + datetime.timedelta(seconds=2))
			existingOrdersForTime = self.__orders.setdefault(tInSecs, [])
			existingOrdersForTime.append((self.__instrument, 'Tightened-Stop-Buy', self.__adjStopPrice, consts.DUMMY_ADJ_RATIO, consts.DUMMY_RANK))
			self.__orders[tInSecs] = existingOrdersForTime
			self.__logger.info("%s: Tightened Stop Loss BUY order, due to upper band curving in, of %d %s shares set to %.2f" % (self.getCurrentDateTime(), self.__shortPos.getShares(), self.__instrument, self.__adjStopPrice))
			self.__entryDayStopPrice = self.__adjStopPrice
			#return False
		else:
			stopPrice = self.__entryDayStopPrice
			# No need to adjust the stop price as the entry was based on the adjusted price.
			self.__adjStopPrice = stopPrice

			self.__shortPos.cancelExit()
			self.__shortPos.exitStop(self.__adjStopPrice, True)
			t = bar.getDateTime()
			tInSecs = xiquantFuncs.secondsSinceEpoch(t + datetime.timedelta(seconds=2))
			existingOrdersForTime = self.__orders.setdefault(tInSecs, [])
			existingOrdersForTime.append((self.__instrument, 'Stop-Buy', self.__adjStopPrice, consts.DUMMY_ADJ_RATIO, consts.DUMMY_RANK))
			self.__orders[tInSecs] = existingOrdersForTime
			self.__logger.info("%s: New Stop Loss BUY order for %d %s shares set to %.2f" % (self.getCurrentDateTime(), self.__shortPos.getShares(), self.__instrument, self.__adjStopPrice))

		if (self.__entryDay == xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-1])) and (self.__entryDay == xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-2])):
			# The stop loss order for the entry or the next day has already been set.
			self.__logger.debug("Analysis Day for %s" % self.__instrument)
			return False
		# Not the entry day or the next day, so reset entry day
		self.__entryDay = None
		return False

def run_strategy(bBandsPeriod, instrument, startPortfolio, startPeriod, endPeriod, plot=False):
	# Download the bars
	feed = xiquantPlatform.redis_build_feed_EOD_RAW(instrument, startPeriod, endPeriod)

	# Add the SPY and QQQ bars, which are used to determine if the market is Bullish or Bearish
	# on a particular day.
	feed = xiquantPlatform.add_feeds_EODRAW_CSV(feed, 'SPY', startPeriod, endPeriod)
	feed = xiquantPlatform.add_feeds_EODRAW_CSV(feed, 'QQQ', startPeriod, endPeriod)
	barsDictForCurrAdj = {}
	barsDictForCurrAdj[instrument] = feed.getBarSeries(instrument)
	barsDictForCurrAdj['SPY'] = feed.getBarSeries('SPY')
	barsDictForCurrAdj['QQQ'] = feed.getBarSeries('QQQ')
	feedAdjustedToEndDate = xiquantPlatform.adjustBars(barsDictForCurrAdj, startPeriod, endPeriod)

	# Get the earnings calendar for the period
	earningsCalList = xiquantFuncs.getEarningsCalendar(instrument, startPeriod, endPeriod)

	strat = BBSpread(feedAdjustedToEndDate, feed, instrument, bBandsPeriod, earningsCalList, startPortfolio)
	strat.run()
	print strat.getOrders()

	'''
	if plot:
		plt = plotter.StrategyPlotter(strat, True, True, True)
		plt.getInstrumentSubplot(instrument).addDataSeries("upper", strat.getBollingerBands().getUpperBand())
		plt.getInstrumentSubplot(instrument).addDataSeries("middle", strat.getBollingerBands().getMiddleBand())
		plt.getInstrumentSubplot(instrument).addDataSeries("lower", strat.getBollingerBands().getLowerBand())
		plt1 = plotter.StrategyPlotter(strat, True, True, True)
		plt1.getInstrumentSubplot(instrument).addDataSeries("RSI", strat.getRSI())
		plt1.getInstrumentSubplot(instrument).addDataSeries("EMA Fast", strat.getEMAFast())
		plt1.getInstrumentSubplot(instrument).addDataSeries("EMA Slow", strat.getEMASlow())
		plt1.getInstrumentSubplot(instrument).addDataSeries("EMA Signal", strat.getEMASignal())

		strat.run()
		print strat.getOrders()

		if plot:
			plt.plot()
			plt1.plot()
			fileNameRoot = 'BB_spread_' + instrument
			(plt.buildFigure()).savefig(fileNameRoot + '_1_' + '.png', dpi=800)
			Image.open(fileNameRoot + '_1_' + '.png').save(fileNameRoot + '_1_' + '.jpg', 'JPEG')
			(plt1.buildFigure()).savefig(fileNameRoot + '_2_' + '.png', dpi=800)
			Image.open(fileNameRoot + '_2_' + '.png').save(fileNameRoot + '_2_' + '.jpg', 'JPEG')
		'''

def main(plot):
	import dateutil.parser
	startDate = dateutil.parser.parse('2005-06-30T08:00:00.000Z')
	endDate = dateutil.parser.parse('2014-12-31T08:00:00.000Z')

	instruments = ["NEE"]
	bBandsPeriod = 20
	startPortfolio = 1000000
	for inst in instruments:
		run_strategy(bBandsPeriod, inst, startPortfolio, startDate, endDate, plot)


if __name__ == "__main__":
	main(True)
