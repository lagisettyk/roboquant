#!/usr/bin/python
from pyalgotrade import strategy
from pyalgotrade import plotter
from pyalgotrade.tools import yahoofinance
from pyalgotrade.technical import bollinger
from pyalgotrade.technical import ma
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
#import Image
from matplotlib import pyplot

import logging
import json
import jsonschema

import xiquantFuncs
import xiquantStrategyParams as consts
import divergence

########Kiran's additions
import logging.handlers
import os
module_dir = os.path.dirname(__file__)  # get current directory

class BBSpread(strategy.BacktestingStrategy):
	def __init__(self, feed, instrument, bBandsPeriod, startPortfolio):
		strategy.BacktestingStrategy.__init__(self, feed, startPortfolio)

		# We want to use adjusted prices.
		self.setUseAdjustedValues(True)
		self.__feed = feed
		self.__bullishOrBearish = 0
		self.__longPos = None
		self.__shortPos = None
		self.__entryDay = None
		self.__entryDayStopPrice = 0.0
		self.__instrument = instrument
		self.setUseAdjustedValues(True)
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
		self.__smaLong1 = ma.SMA(self.__spyDS, consts.SMA_LONG_1)
		self.__smaLong2 = ma.SMA(self.__spyDS, consts.SMA_LONG_2)
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
		self.__ordersFile = None
		self.__logger = None

	def initLogging(self):
		logger = logging.getLogger("xiQuant")
		logger.setLevel(logging.INFO)
		logFileName = "BB_Spread_" + self.__instrument + ".log"
		handler = logging.handlers.RotatingFileHandler(
              logFileName, maxBytes=1024 * 1024, backupCount=5)
		#handler = logging.FileHandler(logFileName)
		handler.setLevel(logging.INFO)
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
			return True
		else:
			return False

	def isBearish(self):
		self.__logger.debug("SPY Close: $%.2f" % self.__spyDS[-1])
		self.__logger.debug("SPY 20 SMA: $%.2f" % self.__smaSPYShort1[-1])
		self.__logger.debug("SPY Lower BBand: $%.2f" % self.__lowerSPYBBDataSeries[-1])
		if self.__spyDS[-1] < self.__smaSPYShort1[-1] and self.__spyDS[-1] > self.__lowerSPYBBDataSeries[-1]:
			return True
		else:
			return False

	def onStart(self):
		self.__logger = self.initLogging()
		self.__logger.info("Initial portfolio value: $%.2f" % self.getBroker().getEquity())
		self.__logger.debug("Load the input JSON strategy file.")
		file_json_strategies = os.path.join(module_dir, 'json_strategies')
		jsonStrategies = open(file_json_strategies)
		self.__inpStrategy = json.load(jsonStrategies)
		self.__logger.debug("Load the input JSON entry price file.")
		file_json_entry_price = os.path.join(module_dir, 'json_entry_price')
		jsonEntryPrice = open(file_json_entry_price)
		self.__inpEntry = json.load(jsonEntryPrice)
		self.__logger.debug("Load the input JSON exit price file.")
		file_json_exit_price = os.path.join(module_dir, 'json_exit_price')
		jsonExitPrice = open(file_json_exit_price)
		self.__ordersFile = open(consts.ORDERS_FILE, 'w')


	def onFinish(self, bars):
		self.stopLogging()
		self.__ordersFile.close()
		return

	def onEnterOk(self, position):
		execInfo = position.getEntryOrder().getExecutionInfo()
		t = self.__priceDS.getDateTimes()[-1]
		if self.__longPos == position:
			self.__logger.info("%s: BOUGHT %d at $%.2f" % (execInfo.getDateTime(), execInfo.getQuantity(), execInfo.getPrice()))
			self.__ordersFile.write("%s,%s,%s,%s,Buy,%.2f,%d\n" % (str(t.year), str(t.month), str(t.day), self.__instrument, execInfo.getPrice(), execInfo.getQuantity()))
			self.__logger.info("Portfolio cash after BUY: $%.2f" % self.getBroker().getCash())
		elif self.__shortPos == position:
			self.__logger.info("%s: SOLD %d at $%.2f" % (execInfo.getDateTime(), execInfo.getQuantity(), execInfo.getPrice()))
			self.__ordersFile.write("%s,%s,%s,%s,Sell,%.2f,%d\n" % (str(t.year), str(t.month), str(t.day), self.__instrument, execInfo.getPrice(), execInfo.getQuantity()))
			self.__logger.info("Portfolio cash after SELL: $%.2f" % self.getBroker().getCash())

		# Enter a stop loss order for the entry day
		if self.__longPos == position:
			self.__longPos.exitStop(self.__entryDayStopPrice, True)
			self.__ordersFile.write("%s,%s,%s,%s,Stop-Sell,%.2f,%d\n" % (str(t.year), str(t.month), str(t.day), self.__instrument, self.__entryDayStopPrice, self.__longPos.getShares()))
			self.__logger.info("%s: Stop Loss SELL order of %d %s shares set at %.2f" % (self.getCurrentDateTime(), self.__longPos.getShares(), self.__instrument, self.__entryDayStopPrice))
		elif self.__shortPos == position: 
			self.__shortPos.exitStop(self.__entryDayStopPrice, True)
			self.__ordersFile.write("%s,%s,%s,%s,Stop-Buy,%.2f,%d\n" % (str(t.year), str(t.month), str(t.day), self.__instrument, self.__entryDayStopPrice, self.__shortPos.getShares()))
			self.__logger.info("%s: Stop Loss BUY order of %d %s shares set at %.2f" % (self.getCurrentDateTime(), self.__shortPos.getShares(), self.__instrument, self.__entryDayStopPrice))

	def onEnterCanceled(self, position):
		# This would have to be revisited as we would like to try and renter with
		# a higher price for options, as long as the entry point is within the
		# range that the tech. analysis has come up with.
		if self.__longPos == position:
			self.__longPos = None 
			self.__entryDay = None
		elif self.__shortPos == position: 
			self.__shortPos = None 
			self.__entryDay = None
		else: 
			assert(False)

	def onExitOk(self, position):
		execInfo = position.getExitOrder().getExecutionInfo()
		t = self.__priceDS.getDateTimes()[-1]
		if self.__longPos == position: 
			self.__logger.info("%s: SOLD %d at $%.2f" % (execInfo.getDateTime(), execInfo.getQuantity(), execInfo.getPrice()))
			self.__ordersFile.write("%s,%s,%s,%s,Sell,%.2f,%d\n" % (str(t.year), str(t.month), str(t.day), self.__instrument, execInfo.getPrice(), execInfo.getQuantity()))
			self.__logger.info("Portfolio after SELL: $%.2f" % self.getBroker().getCash())
			self.__longPos = None 
		elif self.__shortPos == position: 
			self.__logger.info("%s: COVER BUY %d at $%.2f" % (execInfo.getDateTime(), execInfo.getQuantity(), execInfo.getPrice()))
			self.__ordersFile.write("%s,%s,%s,%s,Cover-Buy,%.2f,%d\n" % (str(t.year), str(t.month), str(t.day), self.__instrument, execInfo.getPrice(), execInfo.getQuantity()))
			self.__logger.info("Portfolio after COVER BUY: $%.2f" % self.getBroker().getCash())
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
		# Cancel any existing entry orders from yesterday.
		if self.__longPos:
			self.__longPos.cancelEntry()
		if self.__shortPos:
			self.__shortPos.cancelEntry()

		# Ensure that enough BB entries exist in the data series for running the
		# strategy.
		if len(self.__priceDS) < self.__bb_period + consts.BB_SLOPE_LOOKBACK_WINDOW:
			return

		lower = self.__bbands.getLowerBand()[-1]
		middle = self.__bbands.getMiddleBand()[-1]
		upper = self.__bbands.getUpperBand()[-1]
		if lower is None:
			return

		if len(self.__priceDS) < consts.MACD_PRICE_DVX_LOOKBACK:
			return
		self.__macd = xiquantFuncs.dsToNumpyArray(self.__emaFast, consts.MACD_PRICE_DVX_LOOKBACK) - xiquantFuncs.dsToNumpyArray(self.__emaSlow, consts.MACD_PRICE_DVX_LOOKBACK)

		if len(self.__priceDS) <= consts.DMI_PERIOD:
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
		self.__logger.debug("%s: Lower: $%.2f" % (bar.getDateTime(), lower))
		self.__logger.debug("%s: Middle: $%.2f" % (bar.getDateTime(), middle))
		self.__logger.debug("%s: Upper: $%.2f" % (bar.getDateTime(), upper))
		self.__logger.debug("%s: Close Price: $%.2f" % (bar.getDateTime(), bar.getClose()))
		self.__logger.debug("%s: Open Price: $%.2f" % (bar.getDateTime(), bar.getOpen()))
		self.__logger.debug("%s: High Price: $%.2f" % (bar.getDateTime(), bar.getHigh()))
		self.__logger.debug("%s: Low Price: $%.2f" % (bar.getDateTime(), bar.getLow()))
		sharesToBuy = 0
	
		###### This needs to be fixed because we never explicitly exit from a position,
		###### we do so by setting the stop loss orders and let the market force us
		##### out of a position.
		if self.exitLongSignal(bar):
			if not self.__longPos.exitActive():
				self.__longPos.exitMarket()
				self.__logger.info("Exiting a LONG position")
				self.__logger.info("Portfolio: $%.2f" % self.getBroker().getCash())
		elif self.exitShortSignal(bar):
			if not self.__shortPos.exitActive():
				self.__shortPos.exitMarket()
				self.__logger.debug("Exiting a SHORT position")
				self.__logger.debug("Portfolio: $%.2f" % self.getBroker().getCash())
		else:
			if self.enterLongSignal(bar):
				# Bullish; enter a long position.
				self.__logger.info("Bullish; Trying to enter a LONG position")
				currPrice = bar.getClose()
				self.__logger.debug("%s: Close Price: $%.2f" % (bar.getDateTime(), currPrice))
				self.__logger.debug("%s: Open Price: $%.2f" % (bar.getDateTime(), bar.getOpen()))
				self.__logger.debug("%s: High Price: $%.2f" % (bar.getDateTime(), bar.getHigh()))
				self.__logger.debug("%s: Low Price: $%.2f" % (bar.getDateTime(), bar.getLow()))
				self.__logger.debug("%s: Portfolio: $%.2f" % (bar.getDateTime(), self.getBroker().getCash()))

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
				sharesToBuy = int((self.getBroker().getCash() * consts.PERCENT_OF_CASH_BALANCE_FOR_ENTRY) / entryPrice)
				self.__logger.debug("Shares To Buy: %d" % sharesToBuy)
				self.__longPos = self.enterLongStop(self.__instrument, entryPrice, sharesToBuy, True)
				if self.__longPos == None:
					self.__logger.debug("Couldn't go LONG %d shares" % sharesToBuy)
				else:
					if self.__longPos.entryActive() == True:
						self.__logger.debug("The LONG order for %d shares is active" % sharesToBuy)
					else:
						self.__logger.debug("LONG on %d shares" % abs(self.__longPos.getShares()))
					self.__entryDay = xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-1])
					self.__logger.debug("Analysis Day is : %s" % self.__entryDay)
					stopPriceDelta = 0
					closePrice = bar.getClose()
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

					stopPrice = bar.getOpen() - stopPriceDelta
					self.__entryDayStopPrice = stopPrice
			elif self.enterShortSignal(bar):
				# Bearish; enter a short position.
				self.__logger.info("Bearish; Trying to enter a SHORT position")
				currPrice = bar.getClose()
				self.__logger.debug("%s: Close Price: $%.2f" % (bar.getDateTime(), currPrice))
				self.__logger.debug("%s: Open Price: $%.2f" % (bar.getDateTime(), bar.getOpen()))
				self.__logger.debug("%s: High Price: $%.2f" % (bar.getDateTime(), bar.getHigh()))
				self.__logger.debug("%s: Low Price: $%.2f" % (bar.getDateTime(), bar.getLow()))
				self.__logger.debug("%s: Portfolio: $%.2f" % (bar.getDateTime(), self.getBroker().getCash()))

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
				sharesToBuy = int((self.getBroker().getCash() / 
								entryPrice) * consts.PERCENT_OF_CASH_BALANCE_FOR_ENTRY)
				self.__logger.debug( "Shares To Buy: %d" % sharesToBuy)
				self.__shortPos = self.enterShortStop(self.__instrument, entryPrice, sharesToBuy, True)
				if self.__shortPos == None:
					self.__logger.debug("Couldn't SHORT %d shares" % sharesToBuy)
				else:
					if self.__shortPos.entryActive() == True:
						self.__logger.debug("The SHORT order for %d shares is active" % sharesToBuy)
					else:
						self.__logger.debug("SHORT on %d shares" % abs(self.__shortPos.getShares()))
					self.__entryDay = xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-1])
					self.__logger.debug("Analysis Day is : %s" % self.__entryDay)
					# Enter a stop limit order to exit here
					stopPriceDelta = 0
					closePrice = bar.getClose()
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

					stopPrice = bar.getOpen() + stopPriceDelta
					self.__entryDayStopPrice = stopPrice

	def enterLongSignal(self, bar):
		# For any instrument, we trade on the same side of the market, so check the market sentiment first
		if self.isBearish():
			self.__logger.debug("The market is Bearish so we will not try to go long.")
			return False

		# Both the bands MUST open up like a crocodile mouth.
		if self.__inpStrategy["BB_Spread_Call"]["BB_Upper_And_BB_Lower"]["AND"][0] == "BB_Upper_Croc_Open" and self.__inpStrategy["BB_Spread_Call"]["BB_Upper_And_BB_Lower"]["AND"][1] == "BB_Lower_Croc_Open":
			if len(self.__bbands.getLowerBand()) > consts.BB_SLOPE_LOOKBACK_WINDOW:
				lowerSlope = xiquantFuncs.slope(self.__bbands.getLowerBand(), consts.BB_SLOPE_LOOKBACK_WINDOW)
				self.__logger.debug("Lower Slope: %d" % lowerSlope)
		
			if len(self.__bbands.getUpperBand()) >= consts.BB_SLOPE_LOOKBACK_WINDOW:
				upperSlope = xiquantFuncs.slope(self.__bbands.getUpperBand(), consts.BB_SLOPE_LOOKBACK_WINDOW)
				self.__logger.debug("Upper Slope: %d" % upperSlope)
		
			if lowerSlope <= -1 * consts.BB_CROC_SLOPE:
				if (self.__bbFirstLowerCrocDay != None) and (self.__bbFirstLowerCrocDay != xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-1])):
					self.__logger.debug("Not the first day of lower band croc mouth opening")
				else:
					self.__logger.debug("First day of lower band croc mouth opening")
					self.__bbFirstLowerCrocDay = xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-1])
		
			if upperSlope >= consts.BB_CROC_SLOPE:
				if (self.__bbFirstUpperCrocDay != None) and (self.__bbFirstUpperCrocDay != xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-1])):
					self.__logger.debug("Not the first day of upper band croc mouth opening")
					return False
				else:
					self.__logger.debug("First day of upper band croc mouth opening")
					self.__bbFirstUpperCrocDay = xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-1])

			if upperSlope < consts.BB_CROC_SLOPE or lowerSlope > -1 * consts.BB_CROC_SLOPE:
				return False

		# This should be the first day of the Bands opening as croc mouth.
		if self.__inpStrategy["BB_Spread_Call"]["BB_Upper_And_BB_Lower"]["AND"][2] == "BB_First_Croc_Open":
			if (self.__bbFirstCrocDay != None) and (self.__bbFirstCrocDay != xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-1])):
				self.__logger.debug("Not the first day of croc mouth opening")
				return False

		# Set this as the first day of the croc mouth opening
		self.__logger.debug("The first day of croc mouth opening")
		self.__bbFirstCrocDay = xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-1])

		# Check if we already hold a position in this instrument
		if self.__longPos != None:
			self.__logger.debug("We already hold a position in %s" % self.__instrument)
			return False

		# The close MUST breach or bounce off of the upper band.
		if self.__inpStrategy["BB_Spread_Call"]["BB_Upper_And_BB_Lower"]["OR"][0] == "BB_Upper_Breach":
			if bar.getClose() > self.__bb_upper:
				self.__logger.debug("Upper band breached.")
			elif self.__inpStrategy["BB_Spread_Call"]["BB_Upper_And_BB_Lower"]["OR"][1] == "BB_Upper_Touch":
				# The close price may not exactly touch the upper band so we will have to
				# include some variance parameter
				if bar.getClose() == self.__bb_upper:
					self.__logger.debug("Upper band touched.")
				else:
					return False

		### Change to lookback window specific code.
		# Check if first breach in the lookback.
		if self.__inpStrategy["BB_Spread_Call"]["BB_Upper_And_BB_Lower"]["OR"][0] == "BB_Upper_Breach" or self.__inpStrategy["BB_Spread_Call"]["BB_Upper_And_BB_Lower"]["OR"][1] == "BB_Upper_Touch":
			if self.__priceDS[-2] > self.__bbands.getUpperBand()[-2]:
				self.__logger.debug("Upper band: %.2f" % self.__bbands.getUpperBand()[-1])
				self.__logger.debug("Price: %.2f" % self.__priceDS[-1])
				self.__logger.debug("Previous upper band: %.2f" % self.__bbands.getUpperBand()[-2])
				self.__logger.debug("Previous price: %.2f" % self.__priceDS[-2])
				self.__logger.debug("Not the first day of upper band breach/touch.")
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
		# For any instrument, we trade on the same side of the market, so check the market sentiment first
		if self.isBullish():
			self.__logger.debug("The market is Bullish so we will not try to go short.")
			return False

		# Both the bands MUST open up like a crocodile mouth.
		if self.__inpStrategy["BB_Spread_Put"]["BB_Upper_And_BB_Lower"]["AND"][0] == "BB_Upper_Croc_Open" and \
			self.__inpStrategy["BB_Spread_Put"]["BB_Upper_And_BB_Lower"]["AND"][1] == "BB_Lower_Croc_Open":
			if len(self.__bbands.getLowerBand()) > consts.BB_SLOPE_LOOKBACK_WINDOW:
				lowerSlope = xiquantFuncs.slope(self.__bbands.getLowerBand(), consts.BB_SLOPE_LOOKBACK_WINDOW)
				self.__logger.debug("Lower Slope: %d" % lowerSlope)
		
			if len(self.__bbands.getUpperBand()) >= consts.BB_SLOPE_LOOKBACK_WINDOW:
				upperSlope = xiquantFuncs.slope(self.__bbands.getUpperBand(), consts.BB_SLOPE_LOOKBACK_WINDOW)
				self.__logger.debug("Upper Slope: %d" % upperSlope)
		
			if upperSlope >= consts.BB_CROC_SLOPE:
				if (self.__bbFirstUpperCrocDay != None) and (self.__bbFirstUpperCrocDay != xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-1])):
					self.__logger.debug("Not the first day of upper band croc mouth opening")
				else:
					self.__logger.debug("First day of upper band croc mouth opening")
					self.__bbFirstUpperCrocDay = xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-1])
		
			if lowerSlope <= -1 * consts.BB_CROC_SLOPE:
				if (self.__bbFirstLowerCrocDay != None) and (self.__bbFirstLowerCrocDay != xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-1])):
					self.__logger.debug("Not the first day of lower band croc mouth opening")
					return False
				else:
					self.__logger.debug("First day of lower band croc mouth opening")
					self.__bbFirstLowerCrocDay = xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-1])
		
			if  upperSlope < consts.BB_CROC_SLOPE or lowerSlope > -1 * consts.BB_CROC_SLOPE:
				return False

		# This should be the first day of the Bands opening as croc mouth.
		if self.__inpStrategy["BB_Spread_Put"]["BB_Upper_And_BB_Lower"]["AND"][2] == "BB_First_Croc_Open":
			if (self.__bbFirstCrocDay != None) and (self.__bbFirstCrocDay != xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-1])):
				self.__logger.debug("Not the first day of croc mouth opening")
				return False

		# Set this as the first day of the croc mouth opening
		self.__logger.debug("The first day of croc mouth opening")
		self.__bbFirstCrocDay = xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-1])

		# Check if we already hold a position in this instrument
		if self.__shortPos != None:
			self.__logger.debug("We already hold a position in %s" % self.__instrument)
			return False

		# The close MUST breach or bounce off of the lower band.
		if self.__inpStrategy["BB_Spread_Put"]["BB_Upper_And_BB_Lower"]["OR"][0] == "BB_Lower_Breach":
			if bar.getClose() < self.__bb_lower:
				self.__logger.debug("Lower band breached.")
			elif self.__inpStrategy["BB_Spread_Put"]["BB_Upper_And_BB_Lower"]["OR"][1] == "BB_Lower_Touch":
				# The close price may not exactly touch the lower band so we will have to
				# include some variance parameter
				if bar.getClose() == self.__bb_lower:
					self.__logger.debug("Lower band touched.")
				else:
					return False

		### Change to lookback window specific code.
		# Check if first breach in the lookback.
		if self.__inpStrategy["BB_Spread_Put"]["BB_Upper_And_BB_Lower"]["OR"][0] == "BB_Lower_Breach" or self.__inpStrategy["BB_Spread_Put"]["BB_Upper_And_BB_Lower"]["OR"][1] == "BB_Lower_Touch":
			if self.__priceDS[-2] < self.__bbands.getLowerBand()[-2]:
				self.__logger.debug("Lower band: %.2f" % self.__bbands.getLowerBand()[-1])
				self.__logger.debug("Price: %.2f" % self.__priceDS[-1])
				self.__logger.debug("Previous lower band: %.2f" % self.__bbands.getLowerBand()[-2])
				self.__logger.debug("Previous price: %.2f" % self.__priceDS[-2])
				self.__logger.debug("Not the first day of lower band breach/touch.")
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
			self.__logger.debug("Prev Lower Band: %.2f" % prevLowerBand)
			if lowerBand > prevLowerBand:
				# Reset the first croc mouth opening marker as the mouth is begin to close
				self.__logger.debug("Reset first croc opening day")
				self.__bbFirstCrocDay = None
				self.__bbFirstLowerCrocDay = None

		# Check if we hold a position in this instrument or not
		if self.__longPos == None:
				return False

		self.__logger.debug("We hold a position in %s" % self.__instrument)
		# We don't explicitly exit but based on the indicators we just tighten the stop limit orders.
		# Set the stop loss order if the profit is at least consts.PROFIT_LOCK
		pnlPerShare = float(self.__longPos.getPnL()/self.__longPos.getShares())
		if pnlPerShare >= consts.PROFIT_LOCK:
			stopPrice = bar.getClose() - pnlPerShare + consts.PROFIT_LOCK
			self.__longPos.cancelExit()
			self.__longPos.exitStop(stopPrice, True)
			t = bar.getDateTime()
			self.__ordersFile.write("%s,%s,%s,%s,Stop-Sell,%.2f,%d\n" % (str(t.year), str(t.month), str(t.day), self.__instrument, stopPrice, self.__longPos.getShares()))
			self.__logger.info("%s: New Stop Loss SELL order to lock profit, of %d %s shares set to %.2f" % (self.getCurrentDateTime(), self.__longPos.getShares(), self.__instrument, stopPrice))

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

		if lowerBand > prevLowerBand:
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
			self.__ordersFile.write("%s,%s,%s,%s,Tightened-Stop-Sell,%.2f,%d\n" % (str(t.year), str(t.month), str(t.day), self.__instrument, stopPrice, self.__longPos.getShares()))
			self.__logger.info("%s: Tightened Stop Loss SELL order, due to lower band curving in, of %d %s shares set to %.2f" % (self.getCurrentDateTime(), self.__longPos.getShares(), self.__instrument, stopPrice))
			return False

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
			self.__logger.debug("Prev Upper Band: %.2f" % prevUpperBand)
			if upperBand < prevUpperBand:
				# Reset the first croc mouth opening marker as the mouth is begin to close
				self.__logger.debug("Reset first croc opening day")
				self.__bbFirstCrocDay = None
				self.__bbFirstUpperCrocDay = None

		# Check if we hold a position in this instrument or not
		if self.__shortPos == None:
			return False

		self.__logger.debug("We hold a position in %s" % self.__instrument)
		# We don't explicitly exit but based on the indicators we just tighten the stop limit orders.
		# Set the stop loss order if the profit is at least consts.PROFIT_LOCK
		pnlPerShare = float(self.__shortPos.getPnL()/self.__shortPos.getShares())
		if pnlPerShare >= consts.PROFIT_LOCK:
			stopPrice = bar.getClose() - pnlPerShare + consts.PROFIT_LOCK
			self.__shortPos.cancelExit()
			self.__shortPos.exitStop(stopPrice, True)
			t = bar.getDateTime()
			self.__ordersFile.write("%s,%s,%s,%s,Stop-Buy,%.2f,%d\n" % (str(t.year), str(t.month), str(t.day), self.__instrument, stopPrice, self.__shortPos.getShares()))
			self.__logger.info("%s: New Stop Loss BUY order to lock profit, of %d %s shares set to %.2f" % (self.getCurrentDateTime(), self.__shortPos.getShares(), self.__instrument, stopPrice))

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

		if upperBand < prevUpperBand:
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
			self.__ordersFile.write("%s,%s,%s,%s,Tightened-Stop-Buy,%.2f,%d\n" % (str(t.year), str(t.month), str(t.day), self.__instrument, stopPrice, self.__shortPos.getShares()))
			self.__logger.info("%s: Tightened Stop Loss BUY order, due to upper band curving in, of %d %s shares set to %.2f" % (self.getCurrentDateTime(), self.__shortPos.getShares(), self.__instrument, stopPrice))
			return False

		if (self.__entryDay == xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-1])) and (self.__entryDay == xiquantFuncs.timestamp_from_datetime(self.__priceDS.getDateTimes()[-3])):
			# The stop limit order for the entry or the next day has already been set.
			self.__logger.debug("Analysis Day for %s" % self.__instrument)
			return False
		# Not the entry day or the next day, so reset entry day
		self.__entryDay = None
		return False

def run_strategy(bBandsPeriod, instrument, startPortfolio, startPeriod, endPeriod, plot=False):

	# Download the bars
	feed = yahoofinance.build_feed([instrument], startPeriod, endPeriod, ".")

	# Add the SPY bars, which are used to determine if the market is Bullish or Bearish
	# on a particular day.
	for year in range(startPeriod, endPeriod + 1):
		csvFileName = "spy-" + str(year) + "-yahoofinance.csv"
		feed.addBarsFromCSV("spy", csvFileName)

	strat = BBSpread(feed, instrument, bBandsPeriod, startPortfolio)

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

		if plot:
			plt.plot()
			plt1.plot()
			fileNameRoot = 'BB_spread_' + instrument
			(plt.buildFigure()).savefig(fileNameRoot + '_1_' + '.png', dpi=800)
			Image.open(fileNameRoot + '_1_' + '.png').save(fileNameRoot + '_1_' + '.jpg', 'JPEG')
			(plt1.buildFigure()).savefig(fileNameRoot + '_2_' + '.png', dpi=800)
			Image.open(fileNameRoot + '_2_' + '.png').save(fileNameRoot + '_2_' + '.jpg', 'JPEG')

def main(plot):
	instruments = ["fdx"]
	bBandsPeriod = 20
	startPortfolio = 1000000
	for inst in instruments:
		run_strategy(bBandsPeriod, inst, startPortfolio, 2005, 2014, plot)


if __name__ == "__main__":
	main(True)
