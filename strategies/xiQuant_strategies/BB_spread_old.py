#!/usr/bin/python
from pyalgotrade import strategy
from pyalgotrade import plotter
from pyalgotrade.tools import yahoofinance
from pyalgotrade.technical import bollinger
from pyalgotrade.technical import ma
from pyalgotrade.technical import stats
#from pyalgotrade.technical import linreg
from pyalgotrade.stratanalyzer import sharpe
import talib
from pyalgotrade.talibext import indicator
#from pyalgotrade.technical import cross
from pyalgotrade.technical import rsi

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

#import os
#from utils import util
#module_dir = os.path.dirname(__file__)  # get current directory

class BBSpread(strategy.BacktestingStrategy):
	def __init__(self, feed, instrument, bBandsPeriod, earningsCal, startPortfolio):
		strategy.BacktestingStrategy.__init__(self, feed, startPortfolio)

		print "########Length@@@@@@@@@@: ", len(feed[instrument].getCloseDataSeries())

		# We want to use adjusted prices.
		self.setUseAdjustedValues(True)
		self.__feed = feed
		self.__bullishOrBearish = 0
		self.__longPos = None
		self.__shortPos = None
		self.__entryDay = None
		self.__entryDayStopPrice = 0.0
		self.__instrument = instrument
		#self.__priceDS = feed[instrument].getAdjCloseDataSeries()
		self.__spyDS = feed["SPY"].getCloseDataSeries()
		self.__priceDS = feed[instrument].getCloseDataSeries()
		self.__openDS = feed[instrument].getOpenDataSeries()
		self.__closeDS = feed[instrument].getCloseDataSeries()
		self.__volumeDS = feed[instrument].getVolumeDataSeries()
		self.__bbands = bollinger.BollingerBands(feed[instrument].getCloseDataSeries(), bBandsPeriod, 2)
		self.__spyBBands = bollinger.BollingerBands(self.__spyDS, bBandsPeriod, 2)
		self.__lowerBBDataSeries = self.__bbands.getLowerBand()
		self.__upperBBDataSeries = self.__bbands.getUpperBand()
		self.__lowerSPYBBDataSeries = self.__spyBBands.getLowerBand()
		self.__upperSPYBBDataSeries = self.__spyBBands.getUpperBand()
		self.__bb_lower = 0
		self.__bb_middle = 0
		self.__bb_upper = 0
		self.__bb_period = bBandsPeriod
		self.__rsi = rsi.RSI(feed[instrument].getPriceDataSeries(), consts.RSI_SETTING)
		self.__lowPriceDS = feed[instrument].getLowDataSeries()
		self.__highPriceDS = feed[instrument].getHighDataSeries()
		self.__emaFast = ma.EMA(self.__priceDS, consts.MACD_FAST_FASTPERIOD)
		self.__emaSlow = ma.EMA(self.__priceDS, consts.MACD_FAST_SLOWPERIOD)
		self.__emaSignal = ma.EMA(self.__priceDS, consts.MACD_FAST_SIGNALPERIOD)
		self.__emaShort1 = ma.EMA(self.__priceDS, consts.EMA_SHORT_1)
		self.__emaShort2 = ma.EMA(self.__priceDS, consts.EMA_SHORT_2)
		self.__emaShort3 = ma.EMA(self.__priceDS, consts.EMA_SHORT_3)
		self.__smaSPYShort1 = ma.SMA(self.__spyDS, consts.SMA_SHORT_1)
		self.__smaLowerTiny = ma.SMA(self.__lowerBBDataSeries, consts.SMA_TINY)
		self.__smaUpperTiny = ma.SMA(self.__upperBBDataSeries, consts.SMA_TINY)
		self.__smaLong1 = ma.SMA(self.__spyDS, consts.SMA_LONG_1)
		self.__smaLong2 = ma.SMA(self.__spyDS, consts.SMA_LONG_2)
		self.__stdDevLower = stats.StdDev(self.__lowerBBDataSeries, consts.SMA_TINY)
		self.__stdDevUpper = stats.StdDev(self.__upperBBDataSeries, consts.SMA_TINY)
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
		self.__inpStrategy = None
		self.__inpEntry = None
		self.__inpExit = None
		self.__logger = None
		self.__earningsCal = earningsCal
		# Orders are stored in a dictionary with datetime as the key and a list of orders
		# as the value. Each item in the list is a tuple of (instrument, action, price) or
		# (instrument, action) kinds.
		self.__orders = {} 
		self.__entryOrderForFile = None
		self.__entryOrder = None
		self._entryOrderTime = None
		self._entryOrderTuple = None
		self.__SPYExceptions = consts.SPY_EXCEPTIONS
		self.__portfolioCashBefore = 0.0

	def initLogging(self):
		logger = logging.getLogger("xiQuant")
		logger.propagate = True # stop the logs from going to the console
		logger.setLevel(logging.DEBUG)
		logFileName = "BB_Spread_" + self.__instrument + "__old.log"
		handler = logging.FileHandler(logFileName, delay=True)
		handler.setLevel(logging.DEBUG)
		formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
		handler.setFormatter(formatter)
		logger.addHandler(handler)
		return logger
		
	def stopLogging(self):
		logging.shutdown()
		return
		
	def isBullish(self):
		self.__logger.debug("SPY Close: $%.2f" % self.__spyDS[-1])
		self.__logger.debug("SPY 20 SMA: $%.2f" % self.__smaSPYShort1[-1])
		self.__logger.debug("SPY Upper BBand: $%.2f" % self.__upperSPYBBDataSeries[-1])
		if self.__spyDS[-1] > self.__smaSPYShort1[-1] and self.__spyDS[-1] < self.__upperSPYBBDataSeries[-1]:
			self.__logger.debug("The market is Bullish today.")
			return True
		else:
			self.__logger.debug("The market is NOT Bullish today.")
			return False

	def isBearish(self):
		self.__logger.debug("SPY Close: $%.2f" % self.__spyDS[-1])
		self.__logger.debug("SPY 20 SMA: $%.2f" % self.__smaSPYShort1[-1])
		self.__logger.debug("SPY Lower BBand: $%.2f" % self.__lowerSPYBBDataSeries[-1])
		if self.__spyDS[-1] < self.__smaSPYShort1[-1] and self.__spyDS[-1] > self.__lowerSPYBBDataSeries[-1]:
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
		jsonStrategies = open('json_strategies')
		self.__inpStrategy = json.load(jsonStrategies)
		print "Load the input JSON entry price file."
		jsonEntryPrice = open('json_entry_price')
		self.__inpEntry = json.load(jsonEntryPrice)
		print "Load the input JSON exit price file."
		jsonExitPrice = open('json_exit_price')
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
			dataRows.append(row)

		# This is for ordering orders by timestamp and rank....
		dataRows.sort(key = operator.itemgetter(0, 1))
		fake_csv = xiquantFuncs.make_fake_csv(dataRows)
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
			existingOrdersForTime = self.__orders.setdefault(self._entryOrderTime, [])
			existingOrdersForTime.append(self._entryOrderTuple)
			self.__orders[self._entryOrderTime] = existingOrdersForTime
			self.__logger.info("Portfolio cash after BUY: $%.2f" % self.getBroker().getCash(includeShort=False))
		elif self.__shortPos == position:
			self.__logger.info("%s: SOLD %d at $%.2f" % (execInfo.getDateTime(), execInfo.getQuantity(), execInfo.getPrice()))
			existingOrdersForTime = self.__orders.setdefault(self._entryOrderTime, [])
			existingOrdersForTime.append(self._entryOrderTuple)
			self.__orders[self._entryOrderTime] = existingOrdersForTime
			self.__logger.info("Portfolio cash after SELL: $%.2f" % self.getBroker().getCash(includeShort=False))

		# Enter a stop loss order for the entry day
		if self.__longPos == position:
			self.__longPos.exitStop(self.__entryDayStopPrice, True)
			# Adding a second to the stop loss order to ensure that the stop loss order
			# gets picked up ONLY after the initial order is picked up during the order
			# processing phase.
			tInSecs = xiquantFuncs.secondsSinceEpoch(t + datetime.timedelta(seconds=1))
			existingOrdersForTime = self.__orders.setdefault(tInSecs, [])
			existingOrdersForTime.append((self.__instrument, 'Stop-Sell', self.__entryDayStopPrice, consts.DUMMY_RANK))
			self.__orders[tInSecs] = existingOrdersForTime
			self.__logger.info("%s: Stop Loss SELL order of %d %s shares set at %.2f" % (self.getCurrentDateTime(), self.__longPos.getShares(), self.__instrument, self.__entryDayStopPrice))
		elif self.__shortPos == position: 
			self.__shortPos.exitStop(self.__entryDayStopPrice, True)
			# Adding a second to the stop loss order to ensure that the stop loss order
			# gets picked up ONLY after the initial order is picked up during the order
			# processing phase.
			tInSecs = xiquantFuncs.secondsSinceEpoch(t + datetime.timedelta(seconds=1))
			existingOrdersForTime = self.__orders.setdefault(tInSecs, [])
			existingOrdersForTime.append((self.__instrument, 'Stop-Buy', self.__entryDayStopPrice, consts.DUMMY_RANK))
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

	def getSPYBollingerBands(self):
		return self.__spyBBands

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
		if len(self.__priceDS) < consts.RESISTANCE_LOOKBACK_WINDOW:
		#if len(self.__priceDS) < 540: #######KIRAN...........#############
			return
		#print "########Length@@@@@@@@@@: ", len(self.__priceDS)
		self.__logger.debug("=====================================================================")
		# Cancel any existing entry orders from yesterday.
		if self.__longPos and self.__longPos.entryActive():
			self.__longPos.cancelEntry()
		if self.__shortPos and self.__shortPos.entryActive():
			self.__shortPos.cancelEntry()

		# Ensure that enough BB entries exist in the data series for running the
		# strategy.
		if len(self.__priceDS) < self.__bb_period + consts.BB_SLOPE_LOOKBACK_WINDOW:
			self.__logger.debug("Not enough bar entries for the BB bands.")
			self.__logger.debug("BB Period: %d" % self.__bb_period)
			self.__logger.debug("BB Slope Lookback Window: %d" % consts.BB_SLOPE_LOOKBACK_WINDOW)
			return

		lower = self.__bbands.getLowerBand()[-1]
		middle = self.__bbands.getMiddleBand()[-1]
		upper = self.__bbands.getUpperBand()[-1]
		if lower is None:
			return

		if len(self.__priceDS) < consts.MACD_PRICE_DVX_LOOKBACK:
			self.__logger.debug("Not enough bar entries for MACD price divergence check.")
			self.__logger.debug("MACD Price Dvx Lookback Window: %d" % consts.MACD_PRICE_DVX_LOOKBACK)
			return
		self.__macd = xiquantFuncs.dsToNumpyArray(self.__emaFast, consts.MACD_PRICE_DVX_LOOKBACK) - xiquantFuncs.dsToNumpyArray(self.__emaSlow, consts.MACD_PRICE_DVX_LOOKBACK)

		if len(self.__priceDS) <= consts.DMI_PERIOD:
			self.__logger.debug("Not enough bar entries for DMI computations.")
			self.__logger.debug("DMI Period: %d" % consts.DMI_PERIOD)
			return
		self.__adx = indicator.ADX(self.__feed[self.__instrument], consts.ADX_COUNT, consts.ADX_PERIOD)
		self.__dmiPlus = indicator.PLUS_DI(self.__feed[self.__instrument], consts.DMI_COUNT, consts.DMI_PERIOD)
		self.__dmiMinus = indicator.MINUS_DI(self.__feed[self.__instrument], consts.DMI_COUNT, consts.DMI_PERIOD)

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
		bar = bars[self.__instrument]
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
			existingOrdersForTime.append((self.__instrument, 'Sell-Market', consts.DUMMY_MARKET_PRICE, consts.DUMMY_RANK))
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
			existingOrdersForTime.append((self.__instrument, 'Buy-Market' , consts.DUMMY_MARKET_PRICE, consts.DUMMY_RANK))
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
				sharesToBuy = int((self.getBroker().getCash(includeShort=False) * consts.PERCENT_OF_CASH_BALANCE_FOR_ENTRY) / entryPrice)
				self.__logger.debug("Shares To Buy: %d" % sharesToBuy)
				print "$$$$$$$$$$$$$$$$$@@@@@@@@@@@@@####################@@@@@@@@@@@@@@: ", sharesToBuy
				self.__portfolioCashBefore = self.getBroker().getCash(includeShort=False)
				self.__longPos = self.enterLongStop(self.__instrument, entryPrice, sharesToBuy, True)
				t = bar.getDateTime()
				tInSecs = xiquantFuncs.secondsSinceEpoch(t)
				self.__entryOrderForFile = "%s,%s,Buy,%.2f\n" % (str(tInSecs), self.__instrument, entryPrice)
				#existingOrdersForTime = self.__orders.setdefault(tInSecs, [])
				#existingOrdersForTime.append((self.__instrument, 'Buy', entryPrice, consts.DUMMY_RANK))
				#self.__orders[tInSecs] = existingOrdersForTime
				self._entryOrderTime = tInSecs
				self._entryOrderTuple = (self.__instrument, 'Buy', entryPrice, consts.DUMMY_RANK)
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
					if closePrice < consts.BB_SPREAD_EXIT_PRICE_RANGE_HIGH_1:
						stopPriceDelta = consts.BB_SPREAD_EXIT_PRICE_DELTA_1
					if closePrice < consts.BB_SPREAD_EXIT_PRICE_RANGE_HIGH_2:
						stopPriceDelta = consts.BB_SPREAD_EXIT_PRICE_DELTA_2
					if closePrice < consts.BB_SPREAD_EXIT_PRICE_RANGE_HIGH_3:
						stopPriceDelta = consts.BB_SPREAD_EXIT_PRICE_DELTA_3
					if closePrice < consts.BB_SPREAD_EXIT_PRICE_RANGE_HIGH_4:
						stopPriceDelta = consts.BB_SPREAD_EXIT_PRICE_DELTA_4
					if closePrice >= consts.BB_SPREAD_EXIT_PRICE_RANGE_HIGH_4:
						stopPriceDelta = consts.BB_SPREAD_EXIT_PRICE_DELTA_5
					self.__logger.debug("%s: Stop Loss Price Delta: %.2f" % (bar.getDateTime(), stopPriceDelta))

					if bullishCandle <= consts.BB_SPREAD_TRADE_DAY_STOP_LOSS_DELTA_1:
						stopPrice = openPrice - stopPriceDelta
					if bullishCandle > consts.BB_SPREAD_TRADE_DAY_STOP_LOSS_DELTA_1 and bullishCandle <= consts.BB_SPREAD_TRADE_DAY_STOP_LOSS_DELTA_2:
						stopPrice = openPrice + bullishCandle / 3
					if bullishCandle > consts.BB_SPREAD_TRADE_DAY_STOP_LOSS_DELTA_2 and bullishCandle <= consts.BB_SPREAD_TRADE_DAY_STOP_LOSS_DELTA_3:
						stopPrice = openPrice + bullishCandle / 2
					if bullishCandle > consts.BB_SPREAD_TRADE_DAY_STOP_LOSS_DELTA_3:
						stopPrice = openPrice + (bullishCandle * 2) / 3

					self.__entryDayStopPrice = stopPrice
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
				sharesToBuy = int((self.getBroker().getCash(includeShort=False) / 
								entryPrice) * consts.PERCENT_OF_CASH_BALANCE_FOR_ENTRY)
				self.__logger.debug( "Shares To Buy: %d" % sharesToBuy)
				self.__portfolioCashBefore = self.getBroker().getCash(includeShort=False)
				self.__shortPos = self.enterShortStop(self.__instrument, entryPrice, sharesToBuy, True)
				t = bar.getDateTime()
				tInSecs = xiquantFuncs.secondsSinceEpoch(t)
				self.__entryOrderForFile = "%s,%s,Sell,%.2f\n" % (str(tInSecs), self.__instrument, entryPrice)
				#existingOrdersForTime = self.__orders.setdefault(tInSecs, [])
				#existingOrdersForTime.append((self.__instrument, 'Sell', entryPrice, consts.DUMMY_RANK))
				#self.__orders[tInSecs] = existingOrdersForTime
				self._entryOrderTime = tInSecs
				self._entryOrderTuple = (self.__instrument, 'Sell', entryPrice, consts.DUMMY_RANK)
				if self.__shortPos == None:
					self.__logger.debug("For whatever reason, couldn't SHORT %d shares" % sharesToBuy)
				else:
					if self.__shortPos.entryActive() == True:
						self.__logger.debug("The SHORT order for %d shares is active" % sharesToBuy)
					else:
						self.__logger.debug("SHORT on %d shares" % abs(self.__shortPos.getShares()))
					self.__entryDay = xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-1])
					self.__logger.debug("Analysis Day is : %s" % self.__entryDay)
					# Enter a stop limit order to exit here
					stopPriceDelta = 0.0
					closePrice = bar.getClose()
					openPrice = bar.getOpen()
					bearishCandle = openPrice - closePrice
					self.__logger.debug("%s: Bearish Candle: %.2f" % (bar.getDateTime(), bearishCandle))
					if closePrice < consts.BB_SPREAD_EXIT_PRICE_RANGE_HIGH_1:
						stopPriceDelta = consts.BB_SPREAD_EXIT_PRICE_DELTA_1
					if closePrice < consts.BB_SPREAD_EXIT_PRICE_RANGE_HIGH_2:
						stopPriceDelta = consts.BB_SPREAD_EXIT_PRICE_DELTA_2
					if closePrice < consts.BB_SPREAD_EXIT_PRICE_RANGE_HIGH_3:
						stopPriceDelta = consts.BB_SPREAD_EXIT_PRICE_DELTA_3
					if closePrice < consts.BB_SPREAD_EXIT_PRICE_RANGE_HIGH_4:
						stopPriceDelta = consts.BB_SPREAD_EXIT_PRICE_DELTA_4
					if closePrice >= consts.BB_SPREAD_EXIT_PRICE_RANGE_HIGH_4:
						stopPriceDelta = consts.BB_SPREAD_EXIT_PRICE_DELTA_5
					self.__logger.debug("%s: Stop Loss Price Delta: %.2f" % (bar.getDateTime(), stopPriceDelta))

					if bearishCandle <= consts.BB_SPREAD_TRADE_DAY_STOP_LOSS_DELTA_1:
						stopPrice = closePrice - stopPriceDelta
					if bearishCandle > consts.BB_SPREAD_TRADE_DAY_STOP_LOSS_DELTA_1 and bearishCandle <= consts.BB_SPREAD_TRADE_DAY_STOP_LOSS_DELTA_2:
						stopPrice = closePrice + (bearishCandle * 2) / 3
					if bearishCandle > consts.BB_SPREAD_TRADE_DAY_STOP_LOSS_DELTA_2 and bearishCandle <= consts.BB_SPREAD_TRADE_DAY_STOP_LOSS_DELTA_3:
						stopPrice = closePrice + bearishCandle / 2
					if bearishCandle > consts.BB_SPREAD_TRADE_DAY_STOP_LOSS_DELTA_3:
						stopPrice = closePrice + bearishCandle / 3

					self.__entryDayStopPrice = stopPrice
					self.__logger.debug("%s: Entry Day Stop Price: %.2f" % (bar.getDateTime(), self.__entryDayStopPrice))

	def enterLongSignal(self, bar):
		# Both the bands MUST open up like a crocodile mouth.
		if self.__inpStrategy["BB_Spread_Call"]["BB_Upper_And_BB_Lower"]["AND"][0] == "BB_Upper_Croc_Open" and self.__inpStrategy["BB_Spread_Call"]["BB_Upper_And_BB_Lower"]["AND"][1] == "BB_Lower_Croc_Open":
			if len(self.__bbands.getLowerBand()) > consts.BB_SLOPE_LOOKBACK_WINDOW:
				normLowerBand = xiquantFuncs.normalize(self.__bbands.getLowerBand()[-1], self.__smaLowerTiny[-1], self.__stdDevLower[-1])
				normPrevLowerBand = xiquantFuncs.normalize(self.__bbands.getLowerBand()[-2], self.__smaLowerTiny[-2], self.__stdDevLower[-2])
				lowerSlope = xiquantFuncs.slope(normLowerBand, normPrevLowerBand)
				self.__logger.debug("Lower Slope: %d" % lowerSlope)
		
			if len(self.__bbands.getUpperBand()) >= consts.BB_SLOPE_LOOKBACK_WINDOW:
				normUpperBand = xiquantFuncs.normalize(self.__bbands.getUpperBand()[-1], self.__smaUpperTiny[-1], self.__stdDevUpper[-1])
				normPrevUpperBand = xiquantFuncs.normalize(self.__bbands.getUpperBand()[-2], self.__smaUpperTiny[-2], self.__stdDevUpper[-2])
				upperSlope = xiquantFuncs.slope(normUpperBand, normPrevUpperBand)
				self.__logger.debug("Upper Slope: %d" % upperSlope)
		
			if lowerSlope <= -1 * consts.BB_CROC_SLOPE:
				if (self.__bbFirstLowerCrocDay != None) and (self.__bbFirstLowerCrocDay != xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-1])):
					self.__logger.debug("Not the first day of lower band croc mouth opening")
					return False
				else:
					self.__bbFirstLowerCrocDay = xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-1])
					self.__logger.debug("First day of lower band croc mouth opening: %s" % self.__bbFirstLowerCrocDay)
		
			if upperSlope >= consts.BB_CROC_SLOPE:
				if (self.__bbFirstUpperCrocDay != None) and (self.__bbFirstUpperCrocDay != xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-1])):
					self.__logger.debug("Not the first day of upper band croc mouth opening")
					return False
				else:
					self.__bbFirstUpperCrocDay = xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-1])
					self.__logger.debug("First day of upper band croc mouth opening: %s" % self.__bbFirstUpperCrocDay)

			if upperSlope < consts.BB_CROC_SLOPE or lowerSlope > -1 * consts.BB_CROC_SLOPE:
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
			if self.isBearish():
				self.__logger.debug("The market is Bearish so we will not try to go LONG.")
				return False
		else:
			self.__logger.debug("%s is in the exceptions list, so we don't check if the market is Bullish or Bearish today." % self.__instrument)

		# The close MUST breach or bounce off of the upper band.
		if self.__inpStrategy["BB_Spread_Call"]["BB_Upper_And_BB_Lower"]["OR"][0] == "BB_Upper_Breach":
			if bar.getClose() > self.__bb_upper:
				self.__logger.debug("Upper band breached.")
				self.__logger.debug("Close Price: %.2f" % bar.getClose())
				self.__logger.debug("Upper Band: %.2f" % self.__bb_upper)
			elif self.__inpStrategy["BB_Spread_Call"]["BB_Upper_And_BB_Lower"]["OR"][1] == "BB_Upper_Touch":
				# The close price may not exactly touch the upper band so we will have to
				# include some variance parameter
				if bar.getClose() == self.__bb_upper:
					self.__logger.debug("Upper band touched.")
					self.__logger.debug("Close Price: %.2f" % bar.getClose())
					self.__logger.debug("Upper Band: %.2f" % self.__bb_upper)
				else:
					self.__logger.debug("NO upper band breach/touch.")
					return False

		### Change to lookback window specific code.
		# Check if first breach in the lookback.
		if self.__inpStrategy["BB_Spread_Call"]["BB_Upper_And_BB_Lower"]["OR"][0] == "BB_Upper_Breach" or self.__inpStrategy["BB_Spread_Call"]["BB_Upper_And_BB_Lower"]["OR"][1] == "BB_Upper_Touch":
			if self.__priceDS[-2] > self.__bbands.getUpperBand()[-2]:
				self.__logger.debug("Not the first day of upper band breach/touch.")
				self.__logger.debug("Upper band: %.2f" % self.__bbands.getUpperBand()[-1])
				self.__logger.debug("Close price: %.2f" % self.__priceDS[-1])
				precPrevUpperBand = float("%0.2f" % self.__bbands.getUpperBand()[-2])
				self.__logger.debug("Previous upper band: %.4f" % precPrevUpperBand)
				#self.__logger.debug("Previous upper band: %.4f" % Decimal(self.__bbands.getUpperBand()[-2]))
				self.__logger.debug("Previous price: %.2f" % self.__priceDS[-2])
				return False

		# Check the price jump
		# +1 because we need one additional entry to compute the candle jump
		if (len(self.__priceDS) < consts.PRICE_JUMP_LOOKBACK_WINDOW + 1):
			self.__logger.debug("Not enough entires for Price Jump check lookback.")
			self.__logger.debug("Lookback: %d" % consts.PRICE_JUMP_LOOKBACK_WINDOW)
			self.__logger.debug("Entries: %d" % len(self.__priceDS))
			return False
		if self.__priceDS[-1] < self.__priceDS[-2]:
			self.__logger.debug("Close price not higher than the previous close.")
			self.__logger.debug("Close price: %.2f" % self.__priceDS[-1])
			self.__logger.debug("Close price: %.2f" % self.__priceDS[-2])
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
			prevClosePrice = self.__priceDS[-2]
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
			self.__logger.debug("Volume not greater in lookback.")
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
		priceArrayInLookback = xiquantFuncs.dsToNumpyArray(self.__priceDS, consts.CASH_FLOW_LOOKBACK_WINDOW)
		volumeArrayInLookback = xiquantFuncs.dsToNumpyArray(self.__volumeDS, consts.CASH_FLOW_LOOKBACK_WINDOW)
		cashFlowArrayInLookback = priceArrayInLookback * volumeArrayInLookback
		if cashFlowArrayInLookback[-1] <= float(cashFlowArrayInLookback[:-1].sum() / (consts.CASH_FLOW_LOOKBACK_WINDOW -1)):
			self.__logger.debug("Cashflow: %.2f" % cashFlowArrayInLookback[-1]) 
			self.__logger.debug("Cashflow in lookback: %.2f" % float(cashFlowArrayInLookback[:-1].sum() / (consts.CASH_FLOW_LOOKBACK_WINDOW -1))) 
			self.__logger.debug("Volume: %.2f" % volumeArrayInLookback[-1])
			self.__logger.debug("Cashflow check failed.")
			return False

		self.__logger.debug("Cashflow: %.2f" % cashFlowArrayInLookback[-1]) 
		self.__logger.debug("Cashflow in lookback: %.2f" % float(cashFlowArrayInLookback[:-1].sum() / (consts.CASH_FLOW_LOOKBACK_WINDOW -1))) 
		self.__logger.debug("Volume: %.2f" % volumeArrayInLookback[-1])
		self.__logger.debug("Cashflow check passed.")

		# Check resistance
		if (len(self.__priceDS) < consts.RESISTANCE_LOOKBACK_WINDOW):
			self.__logger.debug("Not enough entries for resistance lookback")
			self.__logger.debug("Support lookback: %d" % consts.RESISTANCE_LOOKBACK_WINDOW)
			self.__logger.debug("Number of entries: %d" % len(self.__priceDS))
			return False
		priceArrayInLookback = xiquantFuncs.dsToNumpyArray(self.__priceDS, consts.RESISTANCE_RECENT_LOOKBACK_WINDOW)
		recentResistance = priceArrayInLookback.max()

		priceJmpRange = 0
		closePrice = bar.getClose()
		if closePrice < consts.BB_PRICE_RANGE_HIGH_1:
			priceJmpRange = float((closePrice * consts.BB_SPREAD_PERCENT_INCREASE_RANGE_1) / 100)
		if closePrice < consts.BB_PRICE_RANGE_HIGH_2:
			priceJmpRange = float((closePrice * consts.BB_SPREAD_PERCENT_INCREASE_RANGE_2) / 100)
		if closePrice < consts.BB_PRICE_RANGE_HIGH_3:
			priceJmpRange = float((closePrice * consts.BB_SPREAD_PERCENT_INCREASE_RANGE_3) / 100)
		if closePrice < consts.BB_PRICE_RANGE_HIGH_4:
			priceJmpRange = float((closePrice * consts.BB_SPREAD_PERCENT_INCREASE_RANGE_4) / 100)
		if closePrice >= consts.BB_PRICE_RANGE_HIGH_4:
			priceJmpRange = float((closePrice * consts.BB_SPREAD_PERCENT_INCREASE_RANGE_5) / 100)

		priceArrayInHistoricalLookback = xiquantFuncs.dsToNumpyArray(self.__priceDS, consts.RESISTANCE_LOOKBACK_WINDOW)
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
		#if (self.__rsi[-1] <= consts.RSI_LOWER_LIMIT):
		#	self.__logger.debug("RSI lower limit check failed.")
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
			if len(self.__bbands.getLowerBand()) > consts.BB_SLOPE_LOOKBACK_WINDOW:
				normLowerBand = xiquantFuncs.normalize(self.__bbands.getLowerBand()[-1], self.__smaLowerTiny[-1], self.__stdDevLower[-1])
				normPrevLowerBand = xiquantFuncs.normalize(self.__bbands.getLowerBand()[-2], self.__smaLowerTiny[-2], self.__stdDevLower[-2])
				lowerSlope = xiquantFuncs.slope(normLowerBand, normPrevLowerBand)
				self.__logger.debug("Lower Slope: %d" % lowerSlope)
		
			if len(self.__bbands.getUpperBand()) >= consts.BB_SLOPE_LOOKBACK_WINDOW:
				#upperSlope = xiquantFuncs.slope(self.__bbands.getUpperBand(), consts.BB_SLOPE_LOOKBACK_WINDOW)
				normUpperBand = xiquantFuncs.normalize(self.__bbands.getUpperBand()[-1], self.__smaUpperTiny[-1], self.__stdDevUpper[-1])
				normPrevUpperBand = xiquantFuncs.normalize(self.__bbands.getUpperBand()[-2], self.__smaUpperTiny[-2], self.__stdDevUpper[-2])
				upperSlope = xiquantFuncs.slope(normUpperBand, normPrevUpperBand)
				self.__logger.debug("Upper Slope: %d" % upperSlope)
		
			if upperSlope >= consts.BB_CROC_SLOPE:
				if (self.__bbFirstUpperCrocDay != None) and (self.__bbFirstUpperCrocDay != xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-1])):
					self.__logger.debug("Not the first day of upper band croc mouth opening")
					return False
				else:
					self.__bbFirstUpperCrocDay = xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-1])
					self.__logger.debug("First day of upper band croc mouth opening: %s" % self.__bbFirstUpperCrocDay)
		
			if lowerSlope <= -1 * consts.BB_CROC_SLOPE:
				if (self.__bbFirstLowerCrocDay != None) and (self.__bbFirstLowerCrocDay != xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-1])):
					self.__logger.debug("Not the first day of lower band croc mouth opening")
					return False
				else:
					self.__bbFirstLowerCrocDay = xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-1])
					self.__logger.debug("First day of lower band croc mouth opening: %s" % self.__bbFirstLowerCrocDay)
		
			if  upperSlope < consts.BB_CROC_SLOPE or lowerSlope > -1 * consts.BB_CROC_SLOPE:
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
			if self.isBullish():
				self.__logger.debug("The market is Bullish so we will not try to go short.")
				return False
		else:
			self.__logger.debug("%s is in the exceptions list, so we don't check if the market is Bullish or Bearish today." % self.__instrument)

		# The close MUST breach or bounce off of the lower band.
		if self.__inpStrategy["BB_Spread_Put"]["BB_Upper_And_BB_Lower"]["OR"][0] == "BB_Lower_Breach":
			if bar.getClose() < self.__bb_lower:
				self.__logger.debug("Lower band breached.")
				self.__logger.debug("Close Price: %.2f" % bar.getClose())
				self.__logger.debug("Lower band: %.2f" % self.__bb_lower)
			elif self.__inpStrategy["BB_Spread_Put"]["BB_Upper_And_BB_Lower"]["OR"][1] == "BB_Lower_Touch":
				# The close price may not exactly touch the lower band so we will have to
				# include some variance parameter
				if bar.getClose() == self.__bb_lower:
					self.__logger.debug("Lower band touched.")
					self.__logger.debug("Close Price: %.2f" % bar.getClose())
					self.__logger.debug("Lower band: %.2f" % self.__bb_lower)
				else:
					self.__logger.debug("NO lower band breach/touch.")
					return False

		### Change to lookback window specific code.
		# Check if first breach in the lookback.
		if self.__inpStrategy["BB_Spread_Put"]["BB_Upper_And_BB_Lower"]["OR"][0] == "BB_Lower_Breach" or self.__inpStrategy["BB_Spread_Put"]["BB_Upper_And_BB_Lower"]["OR"][1] == "BB_Lower_Touch":
			if self.__priceDS[-2] < self.__bbands.getLowerBand()[-2]:
				self.__logger.debug("Not the first day of lower band breach/touch.")
				self.__logger.debug("Lower band: %.2f" % self.__bbands.getLowerBand()[-1])
				self.__logger.debug("Price: %.2f" % self.__priceDS[-1])
				precPrevLowerBand = float("%0.2f" % self.__bbands.getLowerBand()[-2])
				self.__logger.debug("Previous lower band: %.4f" % precPrevLowerBand)
				#self.__logger.debug("Previous lower band: %.4f" % Decimal(self.__bbands.getLowerBand()[-2]))
				self.__logger.debug("Previous price: %.2f" % self.__priceDS[-2])
				return False

		# Check the price jump
		# +1 because we need one additional entry to compute the candle jump
		if (len(self.__priceDS) < consts.PRICE_JUMP_LOOKBACK_WINDOW + 1):
			self.__logger.debug("Not enough entires for Price Jump check lookback.")
			self.__logger.debug("Lookback: %d" % consts.PRICE_JUMP_LOOKBACK_WINDOW)
			self.__logger.debug("Entries: %d" % len(self.__priceDS))
			return False
		if self.__priceDS[-1] > self.__priceDS[-2]:
			self.__logger.debug("Close price not lower than the previous close.")
			self.__logger.debug("Close price: %.2f" % self.__priceDS[-1])
			self.__logger.debug("Close price: %.2f" % self.__priceDS[-2])
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
			prevClosePrice = self.__priceDS[-2]
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
			self.__logger.debug("Volume check failed.")
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
		priceArrayInLookback = xiquantFuncs.dsToNumpyArray(self.__priceDS, consts.CASH_FLOW_LOOKBACK_WINDOW)
		volumeArrayInLookback = xiquantFuncs.dsToNumpyArray(self.__volumeDS, consts.CASH_FLOW_LOOKBACK_WINDOW)
		cashFlowArrayInLookback = priceArrayInLookback * volumeArrayInLookback
		if cashFlowArrayInLookback[-1] <= float(cashFlowArrayInLookback[:-1].sum() / (consts.CASH_FLOW_LOOKBACK_WINDOW -1)):
			self.__logger.debug("Cashflow: %.2f" % cashFlowArrayInLookback[-1]) 
			self.__logger.debug("Cashflow in lookback: %.2f" % float(cashFlowArrayInLookback[:-1].sum() / (consts.CASH_FLOW_LOOKBACK_WINDOW -1))) 
			self.__logger.debug("Volume: %.2f" % volumeArrayInLookback[-1])
			self.__logger.debug("Cashflow check failed.")
			return False

		self.__logger.debug("Cashflow: %.2f" % cashFlowArrayInLookback[-1]) 
		self.__logger.debug("Cashflow in lookback: %.2f" % float(cashFlowArrayInLookback[:-1].sum() / (consts.CASH_FLOW_LOOKBACK_WINDOW -1))) 
		self.__logger.debug("Volume: %.2f" % volumeArrayInLookback[-1])
		self.__logger.debug("Cashflow check passed.")

		# Check support
		if (len(self.__priceDS) < consts.SUPPORT_LOOKBACK_WINDOW):
			self.__logger.debug("Not enough entries for support lookback")
			self.__logger.debug("Support lookback: %d" % consts.SUPPORT_LOOKBACK_WINDOW)
			self.__logger.debug("Number of entries: %d" % len(self.__priceDS))
			return False
		priceArrayInLookback = xiquantFuncs.dsToNumpyArray(self.__priceDS, consts.SUPPORT_RECENT_LOOKBACK_WINDOW)
		recentSupport = priceArrayInLookback.min()

		priceJmpRange = 0
		closePrice = bar.getClose()
		if closePrice < consts.BB_PRICE_RANGE_HIGH_1:
			priceJmpRange = float((closePrice * consts.BB_SPREAD_PERCENT_INCREASE_RANGE_1) / 100)
		if closePrice < consts.BB_PRICE_RANGE_HIGH_2:
			priceJmpRange = float((closePrice * consts.BB_SPREAD_PERCENT_INCREASE_RANGE_2) / 100)
		if closePrice < consts.BB_PRICE_RANGE_HIGH_3:
			priceJmpRange = float((closePrice * consts.BB_SPREAD_PERCENT_INCREASE_RANGE_3) / 100)
		if closePrice < consts.BB_PRICE_RANGE_HIGH_4:
			priceJmpRange = float((closePrice * consts.BB_SPREAD_PERCENT_INCREASE_RANGE_4) / 100)
		if closePrice >= consts.BB_PRICE_RANGE_HIGH_4:
			priceJmpRange = float((closePrice * consts.BB_SPREAD_PERCENT_INCREASE_RANGE_5) / 100)

		priceArrayInHistoricalLookback = xiquantFuncs.dsToNumpyArray(self.__priceDS, consts.SUPPORT_LOOKBACK_WINDOW)
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
		#	self.__logger.debug("RSI upper limit check failed.")
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
		if len(self.__bbands.getLowerBand()) >= consts.BB_SLOPE_LOOKBACK_WINDOW:
			lowerBand = self.__bbands.getLowerBand()[-1]
			prevLowerBand = self.__bbands.getLowerBand()[-2]
			self.__logger.debug("Previous lower band: %.4f" % prevLowerBand)
			normLowerBand = xiquantFuncs.normalize(lowerBand, self.__smaLowerTiny[-1], self.__stdDevLower[-1])
			normPrevLowerBand = xiquantFuncs.normalize(prevLowerBand, self.__smaLowerTiny[-2], self.__stdDevLower[-2])
			lowerSlope = xiquantFuncs.slope(normLowerBand, normPrevLowerBand)
			self.__logger.debug("Lower Slope: %d" % lowerSlope)
			if lowerSlope > 0:
				# Reset the first croc mouth opening marker as the mouth is begin to close
				self.__logger.debug("Reset first croc opening day")
				self.__bbFirstCrocDay = None
				self.__logger.debug("Reset first lower croc opening day")
				self.__bbFirstLowerCrocDay = None

		# Check if we hold a position in this instrument or not
		if self.__longPos == None:
				return False
		self.__logger.debug("We hold a position in %s" % self.__instrument)
		self.__portfolioCashBefore = self.getBroker().getCash(includeShort=False)

		# We don't explicitly exit but based on the indicators we just tighten the stop limit orders.
		# The only exception to that rule is the earnings date -- we exit at the market open if earnings
		# will be announced after the close of market or before the open of, or during, the next day.
		if xiquantFuncs.isEarnings(self.__earningsCal, bar.getDateTime().date()):
			self.__logger.debug("%s: Earnings day today, so exit." % bar.getDateTime())
			return True

		exitPriceDelta = 0
		closePrice = bar.getClose()
		if closePrice < consts.BB_SPREAD_EXIT_PRICE_RANGE_HIGH_1:
			exitPriceDelta = consts.BB_SPREAD_EXIT_PRICE_DELTA_1
		if closePrice < consts.BB_SPREAD_EXIT_PRICE_RANGE_HIGH_2:
			exitPriceDelta = consts.BB_SPREAD_EXIT_PRICE_DELTA_2
		if closePrice < consts.BB_SPREAD_EXIT_PRICE_RANGE_HIGH_3:
			exitPriceDelta = consts.BB_SPREAD_EXIT_PRICE_DELTA_3
		if closePrice < consts.BB_SPREAD_EXIT_PRICE_RANGE_HIGH_4:
			exitPriceDelta = consts.BB_SPREAD_EXIT_PRICE_DELTA_4
		if closePrice >= consts.BB_SPREAD_EXIT_PRICE_RANGE_HIGH_4:
			exitPriceDelta = consts.BB_SPREAD_EXIT_PRICE_DELTA_5

		# Since we are tightening the stop losses, a factor needs to be applied to
		# the stop loss price deltas.
		exitPriceDelta = float(exitPriceDelta * consts.BB_SPREAD_EXIT_TIGHTEN_PRICE_FACTOR)

		#if Decimal(lowerBand) > Decimal(prevLowerBand):
		#if precLowerBand > precPrevLowerBand:
		if lowerSlope > consts.BB_SLOPE_LIMIT_FOR_CURVING:
			# Tighten the stop loss order
			if bar.getOpen() <= bar.getClose():
				# Bullish candle
				stopPrice = bar.getOpen() - exitPriceDelta
			else:
				# Bearish candle
				stopPrice = bar.getClose() - exitPriceDelta
			# Cancel the exiting stop limit order before placing a new one
			self.__longPos.cancelExit()
			self.__longPos.exitStop(stopPrice, True)
			t = bar.getDateTime()
			tInSecs = xiquantFuncs.secondsSinceEpoch(t + datetime.timedelta(seconds=2))
			existingOrdersForTime = self.__orders.setdefault(tInSecs, [])
			existingOrdersForTime.append((self.__instrument, 'Tightened-Stop-Sell', stopPrice, consts.DUMMY_RANK))
			self.__orders[tInSecs] = existingOrdersForTime
			self.__logger.info("%s: Tightened Stop Loss SELL order, due to lower band curving in, of %d %s shares set to %.2f" % (self.getCurrentDateTime(), self.__longPos.getShares(), self.__instrument, stopPrice))
			#return False
		else:
			# Set the stop loss order if the profit is at least consts.PROFIT_LOCK
			pnlPerShare = float(self.__longPos.getPnL()/self.__longPos.getShares())
			if pnlPerShare >= consts.PROFIT_LOCK:
				stopPrice = bar.getClose() - pnlPerShare + consts.PROFIT_LOCK
				self.__longPos.cancelExit()
				self.__longPos.exitStop(stopPrice, True)
				t = bar.getDateTime()
				tInSecs = xiquantFuncs.secondsSinceEpoch(t + datetime.timedelta(seconds=2))
				existingOrdersForTime = self.__orders.setdefault(tInSecs, [])
				existingOrdersForTime.append((self.__instrument, 'Stop-Sell', stopPrice, consts.DUMMY_RANK))
				self.__orders[tInSecs] = existingOrdersForTime
				self.__logger.info("%s: New Stop Loss SELL order to lock profit, of %d %s shares set to %.2f" % (self.getCurrentDateTime(), self.__longPos.getShares(), self.__instrument, stopPrice))

		if (self.__entryDay == xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-1])) or (self.__entryDay == xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-3])):
			# The stop limit order for the entry day and the day after has already been set.
			self.__logger.debug("Analysis Day in %s" % self.__instrument)
			return False
		# Not the entry or the next day, so reset entry day
		self.__entryDay = None
		return False
		
	def exitShortSignal(self, bar):
		if len(self.__bbands.getUpperBand()) >= consts.BB_SLOPE_LOOKBACK_WINDOW:
			upperBand = self.__bbands.getUpperBand()[-1]
			prevUpperBand = self.__bbands.getUpperBand()[-2]
			self.__logger.debug("Previous upper band: %.4f" % prevUpperBand)
			normUpperBand = xiquantFuncs.normalize(upperBand, self.__smaUpperTiny[-1], self.__stdDevUpper[-1])
			normPrevUpperBand = xiquantFuncs.normalize(prevUpperBand, self.__smaUpperTiny[-2], self.__stdDevUpper[-2])
			upperSlope = xiquantFuncs.slope(normUpperBand, normPrevUpperBand)
			self.__logger.debug("Upper Slope: %d" % upperSlope)
			if upperSlope < 0:
				# Reset the first croc mouth opening marker as the mouth is begin to close
				self.__logger.debug("Reset first croc opening day")
				self.__bbFirstCrocDay = None
				self.__logger.debug("Reset first upper croc opening day")
				self.__bbFirstUpperCrocDay = None

		# Check if we hold a position in this instrument or not
		if self.__shortPos == None:
			return False
		self.__logger.debug("We hold a position in %s" % self.__instrument)
		self.__portfolioCashBefore = self.getBroker().getCash(includeShort=False)

		# We don't explicitly exit but based on the indicators we just tighten the stop limit orders.
		# The only exception to that rule is the earnings date -- we exit at the market open if earnings
		# will be announced after the close of market or before the open of, or during, the next day.
		if xiquantFuncs.isEarnings(self.__earningsCal, bar.getDateTime().date()):
			self.__logger.debug("%s: Earnings day today, so exit." % bar.getDateTime())
			return True

		# We don't explicitly exit but based on the indicators we just tighten the stop limit orders.
		exitPriceDelta = 0
		closePrice = bar.getClose()
		if closePrice < consts.BB_SPREAD_EXIT_PRICE_RANGE_HIGH_1:
			exitPriceDelta = consts.BB_SPREAD_EXIT_PRICE_DELTA_1
		if closePrice < consts.BB_SPREAD_EXIT_PRICE_RANGE_HIGH_2:
			exitPriceDelta = consts.BB_SPREAD_EXIT_PRICE_DELTA_2
		if closePrice < consts.BB_SPREAD_EXIT_PRICE_RANGE_HIGH_3:
			exitPriceDelta = consts.BB_SPREAD_EXIT_PRICE_DELTA_3
		if closePrice < consts.BB_SPREAD_EXIT_PRICE_RANGE_HIGH_4:
			exitPriceDelta = consts.BB_SPREAD_EXIT_PRICE_DELTA_4
		if closePrice >= consts.BB_SPREAD_EXIT_PRICE_RANGE_HIGH_4:
			exitPriceDelta = consts.BB_SPREAD_EXIT_PRICE_DELTA_5

		# Since we are tightening the stop losses, a factor needs to be applied to
		# the stop loss price deltas.
		exitPriceDelta = float(exitPriceDelta * consts.BB_SPREAD_EXIT_TIGHTEN_PRICE_FACTOR)

		#if Decimal(upperBand) < Decimal(prevUpperBand):
		#if precUpperBand < precPrevUpperBand:
		if upperSlope < consts.BB_SLOPE_LIMIT_FOR_CURVING:
			# Tighten the stop loss order
			if bar.getOpen() <= bar.getClose():
				# Bullish candle
				stopPrice = bar.getClose() + exitPriceDelta
			else:
				# Bearish candle
				stopPrice = bar.getOpen() + exitPriceDelta
			# Cancel the exiting stop limit order before placing a new one
			self.__shortPos.cancelExit()
			self.__shortPos.exitStop(stopPrice, True)
			t = bar.getDateTime()
			tInSecs = xiquantFuncs.secondsSinceEpoch(t + datetime.timedelta(seconds=2))
			existingOrdersForTime = self.__orders.setdefault(tInSecs, [])
			existingOrdersForTime.append((self.__instrument, 'Tightened-Stop-Buy', stopPrice, consts.DUMMY_RANK))
			self.__orders[tInSecs] = existingOrdersForTime
			self.__logger.info("%s: Tightened Stop Loss BUY order, due to upper band curving in, of %d %s shares set to %.2f" % (self.getCurrentDateTime(), self.__shortPos.getShares(), self.__instrument, stopPrice))
			#return False
		else:
			# Set the stop loss order if the profit is at least consts.PROFIT_LOCK
			pnlPerShare = float(self.__shortPos.getPnL()/self.__shortPos.getShares())
			if pnlPerShare >= consts.PROFIT_LOCK:
				stopPrice = bar.getClose() - pnlPerShare + consts.PROFIT_LOCK
				self.__shortPos.cancelExit()
				self.__shortPos.exitStop(stopPrice, True)
				t = bar.getDateTime()
				tInSecs = xiquantFuncs.secondsSinceEpoch(t + datetime.timedelta(seconds=2))
				existingOrdersForTime = self.__orders.setdefault(tInSecs, [])
				existingOrdersForTime.append((self.__instrument, 'Stop-Buy', stopPrice, consts.DUMMY_RANK))
				self.__orders[tInSecs] = existingOrdersForTime
				self.__logger.info("%s: New Stop Loss BUY order to lock profit, of %d %s shares set to %.2f" % (self.getCurrentDateTime(), self.__shortPos.getShares(), self.__instrument, stopPrice))

		if (self.__entryDay == xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-1])) and (self.__entryDay == xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-3])):
			# The stop limit order for the entry or the next day has already been set.
			self.__logger.debug("Analysis Day for %s" % self.__instrument)
			return False
		# Not the entry day or the next day, so reset entry day
		self.__entryDay = None
		return False

def run_strategy(bBandsPeriod, instrument, startPortfolio, startPeriod, endPeriod, plot=False):
	# Download the bars
	feed = xiquantPlatform.redis_build_feed_EOD_RAW(instrument, startPeriod, endPeriod)

	# Add the SPY bars, which are used to determine if the market is Bullish or Bearish
	# on a particular day.
	feed = xiquantPlatform.add_feeds_EODRAW_CSV(feed, 'SPY', startPeriod, endPeriod)
	#barsDictForCurrAdj = {}
	#barsDictForCurrAdj[instrument] = feed.getBarSeries(instrument)
	#barsDictForCurrAdj['SPY'] = feed.getBarSeries('SPY')
	#feedAdjustedToEndDate = xiquantPlatform.adjustBars(barsDictForCurrAdj, startPeriod, endPeriod)

	# Get the earnings calendar for the period
	earningsCalList = xiquantFuncs.getEarningsCalendar(instrument, startPeriod, endPeriod)

	strat = BBSpread(feed , instrument, bBandsPeriod, earningsCalList, startPortfolio)
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

	instruments = ["NFLX"]
	bBandsPeriod = 20
	startPortfolio = 1000000
	for inst in instruments:
		run_strategy(bBandsPeriod, inst, startPortfolio, startDate, endDate, plot)


if __name__ == "__main__":
	main(True)
