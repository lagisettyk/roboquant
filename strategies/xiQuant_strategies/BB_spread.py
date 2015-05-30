#!/usr/bin/python
from pyalgotrade import strategy
from pyalgotrade import plotter
from pyalgotrade.tools import yahoofinance
from pyalgotrade.technical import bollinger
from pyalgotrade.technical import ma
#from pyalgotrade.technical import linreg
from pyalgotrade.stratanalyzer import sharpe
#import talib
from pyalgotrade.talibext import indicator
#from pyalgotrade.technical import cross
from pyalgotrade.technical import rsi

import numpy
#import Image
from matplotlib import pyplot

import logging
import json
#import jsonschema

import xiquantFuncs
import xiquantStrategyParams as consts
import divergence

#########Kiran's additions
import logging.handlers
import os
module_dir = os.path.dirname(__file__)  # get current directory

class BBands(strategy.BacktestingStrategy):
	def __init__(self, feed, instrument, bBandsPeriod, startPortfolio):
		strategy.BacktestingStrategy.__init__(self, feed, startPortfolio)
		self.__feed = feed
		self.__longPos = None
		self.__shortPos = None
		self.__entryDay = None
		self.__entryDayStopPrice = None
		self.__instrument = instrument
		self.setUseAdjustedValues(True)
		self.__priceDS = feed[instrument].getAdjCloseDataSeries()
		self.__openDS = feed[instrument].getOpenDataSeries()
		self.__closeDS = feed[instrument].getCloseDataSeries()
		self.__volumeDS = feed[instrument].getVolumeDataSeries()
		self.__bbands = bollinger.BollingerBands(feed[instrument].getCloseDataSeries(), bBandsPeriod, 2)
		self.__lowerBBDataSeries = self.__bbands.getLowerBand()
		self.__upperBBDataSeries = self.__bbands.getUpperBand()
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
		self.__macd = None
		self.__adx = None
		self.__dmiPlus = None
		self.__dmiMinus = None
		# Count used to pick up the first day of the croc mouth opening
		self.__bbFirstCrocDay = 0
		self.__inpStrategy = None
		self.__inpEntry = None
		self.__inpExit = None
		self.__logger = None

	def initLogging(self):
		logger = logging.getLogger("xiQuant")
		logger.setLevel(logging.INFO)
		file_BB_Spread = os.path.join(module_dir, 'BB_Spread.log')
		### replaced with rotating file handler...
		handler = logging.handlers.RotatingFileHandler(
              file_BB_Spread, maxBytes=1024 * 1024, backupCount=5)
		#handler = logging.FileHandler("BB_Spread.log")
		handler.setLevel(logging.INFO)
		formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
		handler.setFormatter(formatter)
		logger.addHandler(handler)
		return logger
		
	def stopLogging(self):
		logging.shutdown()
		return
		
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
		self.__inpExit = json.load(jsonExitPrice)

	def onFinish(self, bars):
		self.stopLogging()
		return

	def onEnterOk(self, position):
		execInfo = position.getEntryOrder().getExecutionInfo()
		self.__logger.info("%s: BOUGHT %d at $%.2f" % (execInfo.getDateTime(), execInfo.getQuantity(), execInfo.getPrice()))
		self.__logger.info("Portfolio cash after BUY: $%.2f" % self.getBroker().getCash())

		# Enter a stop loss order for the entry day
		if self.__longPos == position:
			self.__longPos.exitStop(self.__entryDayStopPrice, True)
			self.__logger.info("Stop Loss SELL order of %d %s shares set at %.2f" % (self.__longPos.getShares(), self.__instrument, self.__entryDayStopPrice))
		elif self.__shortPos == position: 
			self.__shortPos.exitStop(self.__entryDayStopPrice, True)
			self.__logger.info("Stop Loss BUY order of %d %s shares set at %.2f" % (self.__shortPos.getShares(), self.__instrument, self.__entryDayStopPrice))

	def onEnterCanceled(self, position):
		# This would have to be revisited as we would like to try and renter with
		# a higher price for options, as long as the entry point is within the
		# range that the tech. analysis has come up with.
		if self.__longPos == position:
			self.__longPos = None 
		elif self.__shortPos == position: 
			self.__shortPos = None 
		else: 
			assert(False)

	def onExitOk(self, position):
		execInfo = position.getExitOrder().getExecutionInfo()
		self.__logger.info("%s: SOLD %d at $%.2f" % (execInfo.getDateTime(), execInfo.getQuantity(), execInfo.getPrice()))
		self.__logger.info("Portfolio after SELL: $%.2f" % self.getBroker().getCash())
		if self.__longPos == position: 
			self.__longPos = None 
		elif self.__shortPos == position: 
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

		if len(self.__priceDS) < consts.DMI_SETTING:
			return
		self.__adx = indicator.ADX(self.__feed[self.__instrument], consts.ADX_SETTING)
		self.__dmiPlus = indicator.PLUS_DI(self.__feed[self.__instrument], consts.DMI_SETTING)
		self.__dmiMinus = indicator.MINUS_DI(self.__feed[self.__instrument], consts.DMI_SETTING)

		self.__bb_lower = lower
		self.__bb_middle = middle
		self.__bb_upper = upper
		bar = bars[self.__instrument]
		self.__logger.debug("%s: Lower: $%.2f" % (bar.getDateTime(), lower))
		self.__logger.debug("%s: Middle: $%.2f" % (bar.getDateTime(), middle))
		self.__logger.debug("%s: Upper: $%.2f" % (bar.getDateTime(), upper))
		self.__logger.debug("%s: Adj Close Price: $%.2f" % (bar.getDateTime(), bar.getAdjClose()))
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
				self.__logger.info("Bullish; ENTERING a LONG position")
				currPrice = bar.getAdjClose()
				self.__logger.debug("%s: Close Price: $%.2f" % (bar.getDateTime(), currPrice))
				self.__logger.debug("%s: Open Price: $%.2f" % (bar.getDateTime(), bar.getOpen()))
				self.__logger.debug("%s: High Price: $%.2f" % (bar.getDateTime(), bar.getHigh()))
				self.__logger.debug("%s: Low Price: $%.2f" % (bar.getDateTime(), bar.getLow()))
				self.__logger.debug("%s: Portfolio: $%.2f" % (bar.getDateTime(), self.getBroker().getCash()))

				wickLen = bar.getHigh() - bar.getAdjClose()
				candleLen = bar.getAdjClose() - bar.getOpen()
				# Relative wick length as a percentage of the candle length
				relWickLen = (wickLen / candleLen) * 100
				# Set the limit price based on the relative wick length
				limitPrice = 0
				if "OR" in self.__inpEntry["BB_Spread_Call"] and "Long_Wick" in self.__inpEntry["BB_Spread_Call"]["OR"]:
					if abs(relWickLen) > consts.BB_LONG_WICK:
						if self.__inpEntry["BB_Spread_Call"]["OR"]["Long_Wick"] == "Half_Wick_Plus_Price_Delta":
							limitPrice = bar.getAdjClose() +  wickLen/2 + consts.PRICE_DELTA
					else:
						limitPrice = bar.getAdjClose() + wickLen + consts.PRICE_DELTA
				self.__logger.debug("%s: Wick Len: %.2f" % (bar.getDateTime(), wickLen))
				self.__logger.debug("%s: Candle Len: %.2f" % (bar.getDateTime(), candleLen))
				self.__logger.debug("%s: Wick Len as a percent of Candle Len: %.2f" % (bar.getDateTime(), abs(relWickLen)))
				self.__logger.debug("%s: Limit Price: %.2f" % (bar.getDateTime(), limitPrice))
				sharesToBuy = int((self.getBroker().getCash() * consts.PERCENT_OF_CASH_BALANCE_FOR_ENTRY) / limitPrice)
				self.__logger.debug("Shares To Buy: %d" % sharesToBuy)
				self.__longPos = self.enterLongLimit(self.__instrument, 
									limitPrice,
									sharesToBuy, True)
				if self.__longPos == None:
					self.__logger.debug("Couldn't go LONG %d shares" % sharesToBuy)
				else:
					if self.__longPos.entryActive() == True:
						self.__logger.debug("The LONG order for %d shares is active" % sharesToBuy)
					else:
						self.__logger.debug("LONG on %d shares" % abs(self.__longPos.getShares()))
					self.__entryDay = len(self.__priceDS) -1
					stopPrice = (bar.getOpen() + bar.getAdjClose()) / 2
					self.__entryDayStopPrice = stopPrice
			elif self.enterShortSignal(bar):
				# Bearish; enter a short position.
				self.__logger.info("Bearish; ENTERING a SHORT position")
				currPrice = bar.getAdjClose()
				self.__logger.debug("%s: Close Price: $%.2f" % (bar.getDateTime(), currPrice))
				self.__logger.debug("%s: Open Price: $%.2f" % (bar.getDateTime(), bar.getOpen()))
				self.__logger.debug("%s: High Price: $%.2f" % (bar.getDateTime(), bar.getHigh()))
				self.__logger.debug("%s: Low Price: $%.2f" % (bar.getDateTime(), bar.getLow()))
				self.__logger.debug("%s: Portfolio: $%.2f" % (bar.getDateTime(), self.getBroker().getCash()))

				wickLen = bar.getAdjClose() - bar.getLow()
				candleLen = bar.getOpen() - bar.getAdjClose()
				# Relative wick length as a percentage of the candle length
				relWickLen = (wickLen / candleLen) * 100
				# Set the limit price based on the relative wick length
				if "OR" in self.__inpEntry["BB_Spread_Put"] and "Long_Wick" in self.__inpEntry["BB_Spread_Put"]["OR"]:
					if abs(relWickLen) > consts.BB_LONG_WICK:
						if self.__inpEntry["BB_Spread_Put"]["OR"]["Long_Wick"] == "Half_Wick_Minus_Price_Delta":
							limitPrice = bar.getAdjClose() - wickLen/2 - consts.PRICE_DELTA
					else:
						limitPrice = bar.getAdjClose() - wickLen - consts.PRICE_DELTA
				self.__logger.debug("%s: Wick Len: %.2f" % (bar.getDateTime(), wickLen))
				self.__logger.debug("%s: Candle Len: %.2f" % (bar.getDateTime(), candleLen))
				self.__logger.debug( "%s: Wick Len as a percent of Candle Len: %.2f" % (bar.getDateTime(), abs(relWickLen)))
				self.__logger.debug( "%s: Limit Price: %.2f" % (bar.getDateTime(), limitPrice))
				sharesToBuy = int((self.getBroker().getCash() / 
								limitPrice) * consts.PERCENT_OF_CASH_BALANCE_FOR_ENTRY)
				self.__logger.debug( "Shares To Buy: %d" % sharesToBuy)
				self.__shortPos = self.enterShortLimit(self.__instrument, 
											limitPrice,
											sharesToBuy, True)
				if self.__shortPos == None:
					self.__logger.debug("Couldn't SHORT %d shares" % sharesToBuy)
				else:
					self.__logger.debug("SHORT on %d shares" % abs(self.__shortPos.getShares()))
					self.__entryDay = len(self.__priceDS) -1
					# Enter a stop limit order to exit here
					stopPrice = (bar.getOpen() + bar.getAdjClose()) / 2
					self.__entryDayStopPrice = stopPrice

	def enterLongSignal(self, bar):
		# Both the bands MUST open up like a crocodile mouth.
		if self.__inpStrategy["BB_Spread_Call"]["BB_Upper_And_BB_Lower"]["AND"][0] == "BB_Upper_Croc_Open" and self.__inpStrategy["BB_Spread_Call"]["BB_Upper_And_BB_Lower"]["AND"][1] == "BB_Lower_Croc_Open":
			if len(self.__bbands.getLowerBand()) > consts.BB_SLOPE_LOOKBACK_WINDOW:
				lowerSlope = xiquantFuncs.slope(self.__bbands.getLowerBand(), consts.BB_SLOPE_LOOKBACK_WINDOW)
				self.__logger.debug("Lower Slope: %d" % lowerSlope)
		
			if len(self.__bbands.getUpperBand()) >= consts.BB_SLOPE_LOOKBACK_WINDOW:
				upperSlope = xiquantFuncs.slope(self.__bbands.getUpperBand(), consts.BB_SLOPE_LOOKBACK_WINDOW)
				self.__logger.debug("Upper Slope: %d" % upperSlope)
		
			if  upperSlope < consts.BB_CROC_SLOPE or lowerSlope > -1 * consts.BB_CROC_SLOPE:
				return False

		# This should be the first day of the Bands opening as croc mouth.
		if self.__inpStrategy["BB_Spread_Call"]["BB_Upper_And_BB_Lower"]["AND"][2] == "BB_First_Croc_Open":
			if (self.__bbFirstCrocDay != 0) and (self.__bbFirstCrocDay != len(self.__priceDS) -1):
				self.__logger.debug("Not the first day of croc mouth opening")
				return False

		# Set this as the first day of the croc mouth opening
		self.__logger.debug("The first day of croc mouth opening")
		self.__bbFirstCrocDay = len(self.__priceDS) -1

		# Check if we already hold a position in this instrument
		if self.__longPos != None:
			return False

		# The close MUST breach or bounce off of the upper band.
		if self.__inpStrategy["BB_Spread_Call"]["BB_Upper_And_BB_Lower"]["OR"][0] == "BB_Upper_Breach":
			if bar.getAdjClose() > self.__bb_upper:
				self.__logger.debug("Upper band breached.")
			elif self.__inpStrategy["BB_Spread_Call"]["BB_Upper_And_BB_Lower"]["OR"][1] == "BB_Upper_Touch":
				# The close price may not exactly touch the upper band so we will have to
				# include some variance parameter
				if bar.getAdjClose() == self.__bb_upper:
					self.__logger.debug("Upper band touched.")
				else:
					return False

		# Check the price jump
		# +1 because we need one additional entry to compute the candle jump
		if (len(self.__priceDS) < consts.PRICE_JUMP_LOOKBACK_WINDOW + 1):
			return False
		if self.__priceDS[-1] < self.__priceDS[-2]:
			return False
		openArrayInLookback = xiquantFuncs.dsToNumpyArray(self.__openDS, consts.PRICE_JUMP_LOOKBACK_WINDOW)
		closeArrayInLookback = xiquantFuncs.dsToNumpyArray(self.__closeDS, consts.PRICE_JUMP_LOOKBACK_WINDOW + 1)
		prevCloseArrayInLookback = closeArrayInLookback[:-1]
		bullishCandleJumpArray = openArrayInLookback - prevCloseArrayInLookback
		### Add the logic if more than the last day's bullish candle needs to be evaluated.
		if bullishCandleJumpArray[-1] <=0:
			return False

		closePrice = bar.getAdjClose()
		if closePrice < consts.BB_PRICE_RANGE_HIGH_1:
			if float(bullishCandleJumpArray[-1] / closePrice) * 100 >= consts.BB_SPREAD_PERCENT_INCREASE_RANGE_1:
				return False
		if closePrice < consts.BB_PRICE_RANGE_HIGH_2:
			if float(bullishCandleJumpArray[-1] / closePrice) * 100 >= consts.BB_SPREAD_PERCENT_INCREASE_RANGE_2:
				return False
		if closePrice < consts.BB_PRICE_RANGE_HIGH_3:
			if float(bullishCandleJumpArray[-1] / closePrice) * 100 >= consts.BB_SPREAD_PERCENT_INCREASE_RANGE_3:
				return False
		if closePrice >= consts.BB_PRICE_RANGE_HIGH_3:
			if float(bullishCandleJumpArray[-1] / closePrice) * 100 >= consts.BB_SPREAD_PERCENT_INCREASE_RANGE_4:
				return False

		# Check volume 
		if (len(self.__volumeDS) < consts.VOLUME_LOOKBACK_WINDOW): 
			return False 
		volumeArrayInLookback = xiquantFuncs.dsToNumpyArray(self.__volumeDS, consts.VOLUME_LOOKBACK_WINDOW)
		if volumeArrayInLookback[-1] != volumeArrayInLookback.max():
			return False 
		
		# Check cash flow 
		if len(self.__priceDS) < consts.CASH_FLOW_LOOKBACK_WINDOW: 
			return False
		priceArrayInLookback = xiquantFuncs.dsToNumpyArray(self.__priceDS, consts.CASH_FLOW_LOOKBACK_WINDOW)
		volumeArrayInLookback = xiquantFuncs.dsToNumpyArray(self.__volumeDS, consts.CASH_FLOW_LOOKBACK_WINDOW)
		cashFlowArrayInLookback = priceArrayInLookback * volumeArrayInLookback
		if cashFlowArrayInLookback[-1] <= float(cashFlowArrayInLookback[:-1].sum() / (consts.CASH_FLOW_LOOKBACK_WINDOW -1)):
			return False

		# Check resistance
		if (len(self.__priceDS) < consts.RESISTANCE_LOOKBACK_WINDOW):
			return False
		priceArrayInLookback = xiquantFuncs.dsToNumpyArray(self.__priceDS, consts.RESISTANCE_RECENT_LOOKBACK_WINDOW)
		recentResistance = priceArrayInLookback.max()

		priceJmpRange = 0
		closePrice = bar.getAdjClose()
		if closePrice < consts.BB_PRICE_RANGE_HIGH_1:
			priceJmpRange = float((closePrice * consts.BB_SPREAD_PERCENT_INCREASE_RANGE_1) / 100)
		if closePrice < consts.BB_PRICE_RANGE_HIGH_2:
			priceJmpRange = float((closePrice * consts.BB_SPREAD_PERCENT_INCREASE_RANGE_2) / 100)
		if closePrice < consts.BB_PRICE_RANGE_HIGH_3:
			priceJmpRange = float((closePrice * consts.BB_SPREAD_PERCENT_INCREASE_RANGE_3) / 100)
		if closePrice >= consts.BB_PRICE_RANGE_HIGH_3:
			priceJmpRange = float((closePrice * consts.BB_SPREAD_PERCENT_INCREASE_RANGE_4) / 100)

		priceArrayInHistoricalLookback = xiquantFuncs.dsToNumpyArray(self.__priceDS, consts.RESISTANCE_LOOKBACK_WINDOW)
		historicalResistanceDeltaArray = priceArrayInHistoricalLookback - recentResistance
		deltaUp = historicalResistanceDeltaArray.max()
		deltaDown = historicalResistanceDeltaArray.min()
		if deltaUp > 0 and deltaUp <= priceJmpRange:
			# The historical resitance should be considered
			if (recentResistance + deltaUp) - closePrice < consts.RESISTANCE_DELTA:
				return False
		elif deltaDown < 0 and abs(deltaDown) <= priceJmpRange:
			# The recent resitance should be considered
			if recentResistance - closePrice < consts.RESISTANCE_DELTA:
				return False
		# Either there's enough room for the stock to move up to the resistance or the stock is at an all time high.

		# Check RSI, should be moving through the lower limit and pointing up.
		if len(self.__rsi) < consts.RSI_SETTING:
			return False
		if (len(self.__rsi) < consts.RSI_LOOKBACK_WINDOW):
			return False
		rsiArrayInLookback = xiquantFuncs.dsToNumpyArray(self.__rsi, consts.RSI_LOOKBACK_WINDOW)
		if rsiArrayInLookback[-1] != rsiArrayInLookback.max():
			return False
		if (self.__rsi[-1] <= consts.RSI_LOWER_LIMIT):
			return False

		# Check MACD, should show no divergence with the price chart in the lookback window
		if len(self.__priceDS) < consts.MACD_PRICE_DVX_LOOKBACK:
			return False
		highPriceArray = xiquantFuncs.dsToNumpyArray(self.__highPriceDS, consts.MACD_PRICE_DVX_LOOKBACK)
		macdArray = self.__macd[consts.MACD_PRICE_DVX_LOOKBACK * -1:]
		#if divergence.dvx_impl(highPriceArray, macdArray, (-1 * consts.MACD_PRICE_DVX_LOOKBACK), -1, consts.MACD_CHECK_HIGHS):
		#	self.__logger.debug("Divergence in MACD and price highs detected")
		#	return False

		# Check DMI+ and DMI-
		if len(self.__dmiPlus) < consts.DMI_SETTING or len(self.__dmiMinus) < consts.DMI_SETTING:
			return False
		if (self.__dmiPlus[-1] <= self.__dmiMinus[-1]):
			# Add the code to give higher priority for investment to cases when both the conditions are satisfied.
			if (self.__dmiPlus[-1] <= self.__dmiPlus[-2]):
				return False
			if (self.__dmiMinus[-1] >= self.__dmiMinus[-2]):
				return False

		# Add checks for other indicators here
		############
		return True

	def enterShortSignal(self, bar):
		# Both the bands MUST open up like a crocodile mouth.
		if self.__inpStrategy["BB_Spread_Put"]["BB_Upper_And_BB_Lower"]["AND"][0] == "BB_Upper_Croc_Open" and \
			self.__inpStrategy["BB_Spread_Put"]["BB_Upper_And_BB_Lower"]["AND"][1] == "BB_Lower_Croc_Open":
			if len(self.__bbands.getLowerBand()) > consts.BB_SLOPE_LOOKBACK_WINDOW:
				lowerSlope = xiquantFuncs.slope(self.__bbands.getLowerBand(), consts.BB_SLOPE_LOOKBACK_WINDOW)
				self.__logger.debug("Lower Slope: %d" % lowerSlope)
		
			if len(self.__bbands.getUpperBand()) >= consts.BB_SLOPE_LOOKBACK_WINDOW:
				upperSlope = xiquantFuncs.slope(self.__bbands.getUpperBand(), consts.BB_SLOPE_LOOKBACK_WINDOW)
				self.__logger.debug("Upper Slope: %d" % upperSlope)
		
			if  upperSlope < consts.BB_CROC_SLOPE or lowerSlope > -1 * consts.BB_CROC_SLOPE:
				return False

		# This should be the first day of the Bands opening as croc mouth.
		if self.__inpStrategy["BB_Spread_Put"]["BB_Upper_And_BB_Lower"]["AND"][2] == "BB_First_Croc_Open":
			if (self.__bbFirstCrocDay != 0) and (self.__bbFirstCrocDay != len(self.__priceDS) -1):
				self.__logger.debug("Not the first day of croc mouth opening")
				return False

		# Set this as the first day of the croc mouth opening
		self.__logger.debug("The first day of croc mouth opening")
		self.__bbFirstCrocDay = len(self.__priceDS) -1

		# Check if we already hold a position in this instrument
		if self.__shortPos != None:
			return False

		# The close MUST breach or bounce off of the lower band.
		if self.__inpStrategy["BB_Spread_Put"]["BB_Upper_And_BB_Lower"]["OR"][0] == "BB_Lower_Breach":
			if bar.getAdjClose() < self.__bb_lower:
				self.__logger.debug("Lower band breached.")
			elif self.__inpStrategy["BB_Spread_Put"]["BB_Upper_And_BB_Lower"]["OR"][1] == "BB_Lower_Touch":
				# The close price may not exactly touch the lower band so we will have to
				# include some variance parameter
				if bar.getAdjClose() == self.__bb_lower:
					self.__logger.debug("Lower band touched.")
				else:
					return False

		# Check the price jump
		# +1 because we need one additional entry to compute the candle jump
		if (len(self.__priceDS) < consts.PRICE_JUMP_LOOKBACK_WINDOW + 1):
			return False
		if self.__priceDS[-1] > self.__priceDS[-2]:
			return False
		openArrayInLookback = xiquantFuncs.dsToNumpyArray(self.__openDS, consts.PRICE_JUMP_LOOKBACK_WINDOW)
		closeArrayInLookback = xiquantFuncs.dsToNumpyArray(self.__closeDS, consts.PRICE_JUMP_LOOKBACK_WINDOW + 1)
		prevCloseArrayInLookback = closeArrayInLookback[:-1]
		bearishCandleJumpArray = prevCloseArrayInLookback - openArrayInLookback
		### Add the logic if more than the last day's bullish candle needs to be evaluated.
		if bearishCandleJumpArray[-1] <=0:
			return False

		closePrice = bar.getAdjClose()
		if closePrice < consts.BB_PRICE_RANGE_HIGH_1:
			if float(bearishCandleJumpArray[-1] / closePrice) * 100 >= consts.BB_SPREAD_PERCENT_INCREASE_RANGE_1:
				return False
		if closePrice < consts.BB_PRICE_RANGE_HIGH_2:
			if float(bearishCandleJumpArray[-1] / closePrice) * 100 >= consts.BB_SPREAD_PERCENT_INCREASE_RANGE_2:
				return False
		if closePrice < consts.BB_PRICE_RANGE_HIGH_3:
			if float(bearishCandleJumpArray[-1] / closePrice) * 100 >= consts.BB_SPREAD_PERCENT_INCREASE_RANGE_3:
				return False
		if closePrice >= consts.BB_PRICE_RANGE_HIGH_3:
			if float(bearishCandleJumpArray[-1] / closePrice) * 100 >= consts.BB_SPREAD_PERCENT_INCREASE_RANGE_4:
				return False

		# Check volume 
		if (len(self.__volumeDS) < consts.VOLUME_LOOKBACK_WINDOW): 
			return False 
		volumeArrayInLookback = xiquantFuncs.dsToNumpyArray(self.__volumeDS, consts.VOLUME_LOOKBACK_WINDOW)
		if volumeArrayInLookback[-1] != volumeArrayInLookback.max():
			return False 

		# Check cash flow 
		if len(self.__priceDS) < consts.CASH_FLOW_LOOKBACK_WINDOW: 
			return False
		priceArrayInLookback = xiquantFuncs.dsToNumpyArray(self.__priceDS, consts.CASH_FLOW_LOOKBACK_WINDOW)
		volumeArrayInLookback = xiquantFuncs.dsToNumpyArray(self.__volumeDS, consts.CASH_FLOW_LOOKBACK_WINDOW)
		cashFlowArrayInLookback = priceArrayInLookback * volumeArrayInLookback
		if cashFlowArrayInLookback[-1] <= float(cashFlowArrayInLookback[:-1].sum() / (consts.CASH_FLOW_LOOKBACK_WINDOW -1)):
			return False

		# Check support
		if (len(self.__priceDS) < consts.SUPPORT_LOOKBACK_WINDOW):
			return False
		priceArrayInLookback = xiquantFuncs.dsToNumpyArray(self.__priceDS, consts.SUPPORT_RECENT_LOOKBACK_WINDOW)
		recentSupport = priceArrayInLookback.min()

		priceJmpRange = 0
		closePrice = bar.getAdjClose()
		if closePrice < consts.BB_PRICE_RANGE_HIGH_1:
			priceJmpRange = float((closePrice * consts.BB_SPREAD_PERCENT_INCREASE_RANGE_1) / 100)
		if closePrice < consts.BB_PRICE_RANGE_HIGH_2:
			priceJmpRange = float((closePrice * consts.BB_SPREAD_PERCENT_INCREASE_RANGE_2) / 100)
		if closePrice < consts.BB_PRICE_RANGE_HIGH_3:
			priceJmpRange = float((closePrice * consts.BB_SPREAD_PERCENT_INCREASE_RANGE_3) / 100)
		if closePrice >= consts.BB_PRICE_RANGE_HIGH_3:
			priceJmpRange = float((closePrice * consts.BB_SPREAD_PERCENT_INCREASE_RANGE_4) / 100)

		priceArrayInHistoricalLookback = xiquantFuncs.dsToNumpyArray(self.__priceDS, consts.SUPPORT_LOOKBACK_WINDOW)
		historicalSupportDeltaArray = priceArrayInHistoricalLookback - recentSupport
		deltaUp = historicalSupportDeltaArray.max()
		deltaDown = historicalSupportDeltaArray.min()
		if deltaUp > 0 and deltaUp <= priceJmpRange:
			# The recent support should be considered
			if closePrice - recentSupport < consts.SUPPORT_DELTA:
				return False
		elif deltaDown < 0 and abs(deltaDown) <= priceJmpRange:
			# The historical resitance should be considered
			if closePrice - (recentSupport + deltaDown) < consts.SUPPORT_DELTA:
				return False
		# Either there's enough room for the stock to move down to the support or the stock is at an all time low.

		# Check RSI, should be moving through the upper limit and pointing down.
		if len(self.__rsi) < consts.RSI_SETTING:
			return False
		if (len(self.__rsi) < consts.RSI_LOOKBACK_WINDOW):
			return False
		rsiArrayInLookback = xiquantFuncs.dsToNumpyArray(self.__rsi, consts.RSI_LOOKBACK_WINDOW)
		if rsiArrayInLookback[-1] != rsiArrayInLookback.min():
			return False
		if (self.__rsi[-1] <= consts.RSI_UPPER_LIMIT):
			return False

		# Check MACD, should show no divergence with the price chart in the lookback window
		if len(self.__priceDS) < consts.MACD_PRICE_DVX_LOOKBACK:
			return False
		lowPriceArray = xiquantFuncs.dsToNumpyArray(self.__lowPriceDS, consts.MACD_PRICE_DVX_LOOKBACK)
		macdArray = self.__macd[consts.MACD_PRICE_DVX_LOOKBACK * -1:]
		#if divergence.dvx_impl(lowPriceArray, macdArray, (-1 * consts.MACD_PRICE_DVX_LOOKBACK), -1, consts.MACD_CHECK_LOWS):
		#	self.__logger.debug("Divergence in MACD and price lows detected")
		#	return False

		# Check DMI+ and DMI-
		if len(self.__dmiPlus) < consts.DMI_SETTING or len(self.__dmiMinus) < consts.DMI_SETTING:
			return False
		if (self.__dmiPlus[-1] >= self.__dmiMinus[-1]):
			# Add the code to give higher priority for investment to cases when both the conditions are satisfied.
			if (self.__dmiPlus[-1] >= self.__dmiPlus[-2]):
				return False
			if (self.__dmiMinus[-1] <= self.__dmiMinus[-2]):
				return False

		# Add checks for other indicators here
		############

		return True

	def exitLongSignal(self, bar):
		if len(self.__bbands.getLowerBand()) >= consts.BB_SLOPE_LOOKBACK_WINDOW:
			lowerSlope = xiquantFuncs.slope(self.__bbands.getLowerBand(), consts.BB_SLOPE_LOOKBACK_WINDOW)
			self.__logger.debug("Lower Slope: %d" % lowerSlope)
			if lowerSlope >= consts.BB_SLOPE_LIMIT_FOR_CURVING:
				# Reset the first croc mouth opening marker as the mouth is begin to close
				self.__logger.debug("Reset first croc opening day")
				self.__bbFirstCrocDay = 0

		# Check if we hold a position in this instrument or not
		if self.__longPos == None:
			return False

		# We don't explicitly exit but based on the indicators we just tighten the stop limit orders.
		if self.__entryDay == len(self.__priceDS) -1:
			# The stop limit order for the entry day has already been set.
			return False

		if lowerSlope >= consts.BB_SLOPE_LIMIT_FOR_CURVING:
			# Tighten the stop loss order
			stopPrice = ((100 - consts.BB_BAND_CURVES_IN_PRICE_TIGHTEN_PERCENT)/ 100) * bar.getAdjClose()
			# Cancel the exiting stop limit order before placing a new one
			self.__longPos.cancelExit()
			self.__longPos.exitStop(stopPrice, True)
			self.__logger.info("Tightened Stop Loss SELL order, due to lower band curving in, of %d %s shares set to %.2f" % (self.__longPos.getShares(), self.__instrument, stopPrice))
			return False
		# Tighten the stop loss order
		stopPrice = bar.getLow() - consts.BB_BAND_SECOND_DAY_BELOW
		# Cancel the exiting stop limit order before placing a new one
		self.__longPos.cancelExit()
		self.__longPos.exitStop(stopPrice, True)
		self.__logger.info("Tightened Stop Loss SELL order of %d %s shares set to %.2f" % (self.__longPos.getShares(), self.__instrument, stopPrice))
		return False
		
	def exitShortSignal(self, bar):
		if len(self.__bbands.getUpperBand()) >= consts.BB_SLOPE_LOOKBACK_WINDOW:
			upperSlope = xiquantFuncs.slope(self.__bbands.getUpperBand(), consts.BB_SLOPE_LOOKBACK_WINDOW)
			self.__logger.debug("Upper Slope: %d" % upperSlope)
			if upperSlope <= consts.BB_SLOPE_LIMIT_FOR_CURVING:
				# Reset the first croc mouth opening marker as the mouth is begin to close
				self.__logger.debug("Reset first croc opening day")
				self.__bbFirstCrocDay = 0

		# Check if we hold a position in this instrument or not
		if self.__shortPos == None:
			return False

		# We don't explicitly exit but based on the indicators we just tighten the stop limit orders.
		if self.__entryDay == len(self.__priceDS) -1:
			# The stop limit order for the entry day has already been set.
			return False

		if upperSlope <= consts.BB_SLOPE_LIMIT_FOR_CURVING:
			# Tighten the stop loss order
			stopPrice = ((100 + consts.BB_BAND_CURVES_IN_PRICE_TIGHTEN_PERCENT)/ 100) * bar.getOpen()
			# Cancel the exiting stop limit order before placing a new one
			self.__shortPos.cancelExit()
			self.__shortPos.exitStop(stopPrice, True)
			self.__logger.info("Tightened Stop Loss BUY order, due to upper band curving in, of %d %s shares set to %.2f" % (self.__shortPos.getShares(), self.__instrument, stopPrice))
			return False
		# Tighten the stop loss order
		stopPrice = bar.getHigh() + consts.BB_BAND_SECOND_DAY_BELOW
		# Cancel the exiting stop limit order before placing a new one
		self.__shortPos.cancelExit()
		self.__shortPos.exitStop(stopPrice, True)
		self.__logger.info("Tightened Stop Loss BUY order of %d %s shares set to %.2f" % (self.__shortPos.getShares(), self.__instrument, stopPrice))
		return False

def run_strategy(bBandsPeriod, instrument, startPortfolio, plot=False):

	# Download the bars
	feed = yahoofinance.build_feed([instrument], 2007, 2014, ".")

	strat = BBands(feed, instrument, bBandsPeriod, startPortfolio)

	if plot:
		plt = plotter.StrategyPlotter(strat, True, True, True)
		plt.getInstrumentSubplot(instrument).addDataSeries("upper", strat.getBollingerBands().getUpperBand())
		plt.getInstrumentSubplot(instrument).addDataSeries("middle", strat.getBollingerBands().getMiddleBand())
		plt.getInstrumentSubplot(instrument).addDataSeries("lower", strat.getBollingerBands().getLowerBand())

		strat.run()

		if plot:
			plt.plot()
			fileNameRoot = 'BB_spread_' + instrument
			(plt.buildFigure()).savefig(fileNameRoot + '.png', dpi=800)
			Image.open(fileNameRoot + '.png').save(fileNameRoot + '.jpg', 'JPEG')

def main(plot):
	instruments = ["nflx"]
	bBandsPeriod = 20
	startPortfolio = 1000000
	for inst in instruments:
		run_strategy(bBandsPeriod, inst, startPortfolio, plot)


if __name__ == "__main__":
	main(True)
