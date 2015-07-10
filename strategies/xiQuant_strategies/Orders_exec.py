#!/usr/bin/python
import csv
import datetime
import os

from pyalgotrade.tools import yahoofinance
from pyalgotrade.barfeed import yahoofeed
from pyalgotrade.barfeed import csvfeed
from pyalgotrade import strategy
from pyalgotrade.utils import stats
from pyalgotrade.stratanalyzer import returns
from pyalgotrade.stratanalyzer import sharpe
from pyalgotrade.broker import backtesting
from pyalgotrade.broker import Order

import xiquantFuncs
import xiquantStrategyParams as consts

class OrdersFile:
	def __init__(self, ordersFile, fakecsv=False):
		self.__orders = {}
		self.__firstDate = 0
		self.__lastDate = 0
		self.__instruments = []

		# Load orders from the file.
		if fakecsv:
			reader = csv.DictReader(ordersFile, fieldnames=["timeSinceEpoch", "symbol", "action", "stopPrice"])
		else:
			reader = csv.DictReader(open(ordersFile, "r"), fieldnames=["timeSinceEpoch", "symbol", "action", "stopPrice"])
		for row in reader:
			timeSinceEpoch = int(row["timeSinceEpoch"])
			ordersList = self.__orders.setdefault(timeSinceEpoch, [])
			order = (row["symbol"], row["action"], float(row["stopPrice"]))
			print "Order being processed from the file: "
			print order
			print "Time of the order: "
			print timeSinceEpoch
			ordersList.append(order)
			self.__orders[timeSinceEpoch] = ordersList

			# As we process the file, store instruments, first date, and last date.
			if row["symbol"] not in self.__instruments:
				self.__instruments.append(row["symbol"])

			if self.__firstDate is 0:
				self.__firstDate = timeSinceEpoch
			else:
				self.__firstDate = min(self.__firstDate, timeSinceEpoch)
			if self.__lastDate is 0:
				self.__lastDate = timeSinceEpoch
			else:
				self.__lastDate = max(self.__lastDate, timeSinceEpoch)

	def getFirstDate(self):
		return self.__firstDate

	def getLastDate(self):
		return self.__lastDate

	def getInstruments(self):
		return self.__instruments

	def getOrders(self, dateTime):
		return self.__orders.get(dateTime, [])

def yearFromTimeSinceEpoch(secs):
	t = datetime.timedelta(seconds=secs)
	return t.days / 365 + 1970

class MyStrategy(strategy.BacktestingStrategy):
	def __init__(self, feed, cash, ordersFile, useAdjustedClose):
		strategy.BacktestingStrategy.__init__(self, feed, cash)
		self.__ordersFile = ordersFile
		self.__longPos = {}
		self.__shortPos = {}
		self.__results = {}
		self.__portfolioCashBefore = 0.0
		self.__portfolioBefore = 0.0
		self.setUseAdjustedValues(useAdjustedClose)
		self.getBroker().setCommission(backtesting.NoCommission())

	def onStart(self):
		self.__resultsFile = open(consts.RESULTS_FILE, 'w')
		self.__resultsFile.write("Instrument,Trade-Type,Entry-Date,Entry-Price,Portfolio-Value-Before,Portfolio-Cash-Before,Portfolio-Value-After,Portfolio-Cash-After,Exit-Date,Exit-Price,Portfolio-Value-Before,Portfolio-Cash-Before,Portfolio-Value-After,Portfolio-Cash-After\n")

	def onFinish(self, bars):
		self.__resultsFile.close()

	def onEnterOk(self, position):
		instrument = position.getEntryOrder().getInstrument()
		execInfo = position.getEntryOrder().getExecutionInfo()
		execTime = execInfo.getDateTime()
		cashBefore = "%0.2f" % self.__portfolioCashBefore
		portfolioBefore = "%0.2f" % self.__portfolioBefore
		cashAfter = "%0.2f" % self.getBroker().getCash(includeShort=False)
		portfolioAfter = "%0.2f" % self.getBroker().getEquity()
		buyPrice = "%0.2f" % execInfo.getPrice()
		if position.getEntryOrder().getAction() == Order.Action.BUY:
			action = "LONG"
		elif position.getEntryOrder().getAction() == Order.Action.SELL:
			action = "SHORT"
		elif position.getEntryOrder().getAction() == Order.Action.BUY_TO_COVER:
			action = "BUY_TO_COVER"
		elif position.getEntryOrder().getAction() == Order.Action.SELL_SHORT:
			action = "SHORT"
		else:
			action = "ERROR"
		self.__results[instrument] = instrument + ',' + action + ',' + str(execTime.date()) + ',' + buyPrice + ',' + portfolioBefore + ',' + cashBefore + ',' + portfolioAfter + ',' + cashAfter + ','
		
	def onExitOk(self, position):
		instrument = position.getExitOrder().getInstrument()
		execInfo = position.getExitOrder().getExecutionInfo()
		execTime = execInfo.getDateTime()
		cashBefore = "%0.2f" % self.__portfolioCashBefore
		portfolioBefore = "%0.2f" % self.__portfolioBefore
		cashAfter = "%0.2f" % self.getBroker().getCash(includeShort=False)
		portfolioAfter = "%0.2f" % self.getBroker().getEquity()
		sellPrice = "%0.2f" % execInfo.getPrice()
		profiOrLoss = "%0.2f" % position.getPnL()
		exitStr = str(execTime.date()) + ',' + sellPrice + ',' + portfolioBefore + ',' + cashBefore + ',' + portfolioAfter + ',' + cashAfter + ',' + profiOrLoss + '\n'
		self.__results[instrument] += exitStr
		self.__resultsFile.write(self.__results[instrument])
		self.__results[instrument] = None

	def onOrderUpdated(self, order):
		if order.isCanceled():
			#raise Exception("Order canceled. Ran out of cash?")
			pass

	def onBars(self, bars):
		self.__portfolioCashBefore = self.getBroker().getCash(includeShort=False)
		self.__portfolioBefore = self.getBroker().getEquity()
		# Cancel all outstanding entry orders from yesterday
		for instrument in self.__ordersFile.getInstruments():
			if self.__longPos.get(instrument, None) and self.__longPos[instrument]:
				self.__longPos[instrument].cancelEntry()
			if self.__shortPos.get(instrument, None) and self.__shortPos[instrument]:
				self.__shortPos[instrument].cancelEntry()

		#bar = bars[self.__instrument]
		#barDateTimeinSecs = int((bars.getDateTime() - datetime.datetime(1970,1,1,0,0,0)).total_seconds())
		barDateTimeinSecs = xiquantFuncs.secondsSinceEpoch(bars.getDateTime())
		self.info("Bar Time: %.2f" % (barDateTimeinSecs))
		self.info(self.__ordersFile.getOrders(barDateTimeinSecs))
		# The available cash is split equally among all the orders for the day
		noOfOrders = len(self.__ordersFile.getOrders(barDateTimeinSecs))
		self.info("Total no. of orders: %d" % noOfOrders)
		# Some of the orders could be stop loss orders so we shouldn't be allocating any money
		# to those orders.
		for (instrument, action, price) in self.__ordersFile.getOrders(barDateTimeinSecs):
			if action.lower() != "buy" and action.lower() != "sell":
				noOfOrders -= 1
		for instrument, action, stopPrice in self.__ordersFile.getOrders(barDateTimeinSecs):
			cashAvailable = float(self.getBroker().getCash(includeShort=False) * consts.PERCENT_OF_CASH_BALANCE_FOR_ENTRY)
			self.info("Available cash: %.2f" % cashAvailable)
			if action.lower() == "buy":
				cashForInstrument = float(cashAvailable / noOfOrders)
				if cashForInstrument > float(cashAvailable * consts.MAX_ALLOCATED_MONEY_FOR_EACH_TRADE):
					cashForInstrument = float(cashAvailable * consts.MAX_ALLOCATED_MONEY_FOR_EACH_TRADE)
				sharesToBuy = int(cashForInstrument / stopPrice)
				self.info("Shares to buy: %d" % sharesToBuy)
				if sharesToBuy < 1:
					# Buy at least 1 share
					if stopPrice < cashAvailable:
						self.info("%s %s of %s at $%.2f" % (action, '1', instrument, stopPrice))
						self.__longPos[instrument] = self.enterLongStop(instrument, stopPrice, 1, True)
						cashAvailable -= stopPrice
						noOfOrders -= 1
						continue
					else:
						# Though there isn't enough money to buy one share of this
						# instrument, the money could be sufficient to buy shares of
						# other instruments.
						continue 
				self.info("%s %d of %s at $%.2f" % (action, sharesToBuy, instrument, stopPrice))
				self.__longPos[instrument] = self.enterLongStop(instrument, stopPrice, sharesToBuy, True)
			elif action.lower() == "sell":
				cashForInstrument = float(cashAvailable / noOfOrders)
				if cashForInstrument > float(cashAvailable * consts.MAX_ALLOCATED_MONEY_FOR_EACH_TRADE):
					cashForInstrument = float(cashAvailable * consts.MAX_ALLOCATED_MONEY_FOR_EACH_TRADE)
				sharesToBuy = int(cashForInstrument / stopPrice)
				if sharesToBuy < 1:
					# Buy at least 1 share
					if stopPrice < cashAvailable:
						self.info("%s %s of %s at $%.2f" % (action, '1', instrument, stopPrice))
						self.__shortPos[instrument] = self.enterShortStop(instrument, stopPrice, 1, True)
						cashAvailable -= stopPrice
						noOfOrders -= 1
						continue
					else:
						# Though there isn't enough money to buy one share of this
						# instrument, the money could be sufficient to buy shares of
						# other instruments.
						continue 
				self.info("%s %d of %s at $%.2f" % (action, sharesToBuy, instrument, stopPrice))
				self.__shortPos[instrument] = self.enterShortStop(instrument, stopPrice, sharesToBuy, True)
			elif action.lower() == "tightened-stop-buy" or action.lower() == "stop-buy":
				if self.__shortPos.get(instrument, None) and self.__shortPos[instrument]:
					self.__shortPos[instrument].cancelExit()
					self.__shortPos[instrument].exitStop(stopPrice, True)
			elif action.lower() == "tightened-stop-sell" or action.lower() == "stop-sell":
				if self.__longPos.get(instrument, None) and self.__longPos[instrument]:
					self.__longPos[instrument].cancelExit()
					self.__longPos[instrument].exitStop(stopPrice, True)
			elif action.lower() == "buy-market":
				if self.__shortPos.get(instrument, None) and self.__shortPos[instrument]:
					self.info("Processing a Buy-Market order.")
					self.__shortPos[instrument].cancelExit()
					self.__shortPos[instrument].exitMarket()
			elif action.lower() == "sell-market":
				if self.__longPos.get(instrument, None) and self.__longPos[instrument]:
					self.info("Processing a Sell-Market order.")
					self.__longPos[instrument].cancelExit()
					self.__longPos[instrument].exitMarket()
			else:
				pass # No need to take any action for Cover-Buy or Sell-Close entries.
		# There must be a stop loss order to process if a Buy or Sell order was processed in the
		# above step.
		#stopLossDateTime = int((bars.getDateTime() + datetime.timedelta(seconds=1) - datetime.datetime(1970,1,1,0,0,0)).total_seconds())
		stopLossDateTime = xiquantFuncs.secondsSinceEpoch(bars.getDateTime() + datetime.timedelta(seconds=1))
		for instrument, action, stopLossPrice in self.__ordersFile.getOrders(stopLossDateTime):
			self.info("%s %s at $%.2f" % (action, instrument, stopLossPrice))
			if self.__longPos.get(instrument, None) and self.__longPos[instrument]:
				self.__longPos[instrument].cancelExit()
				self.__longPos[instrument].exitStop(stopLossPrice, True)
			if self.__shortPos.get(instrument, None) and self.__shortPos[instrument]:
				self.__shortPos[instrument].cancelExit()
				self.__shortPos[instrument].exitStop(stopLossPrice, True)
		# Process any tightened stop loss orders or ones to lock profit
		#stopLossDateTime = int((bars.getDateTime() + datetime.timedelta(seconds=2) - datetime.datetime(1970,1,1,0,0,0)).total_seconds())
		stopLossDateTime = xiquantFuncs.secondsSinceEpoch(bars.getDateTime() + datetime.timedelta(seconds=2))
		for instrument, action, stopLossPrice in self.__ordersFile.getOrders(stopLossDateTime):
			self.info("%s %s at $%.2f" % (action, instrument, stopLossPrice))
			if self.__longPos.get(instrument, None) and self.__longPos[instrument]:
				self.__longPos[instrument].cancelExit()
				self.__longPos[instrument].exitStop(stopLossPrice, True)
			if self.__shortPos.get(instrument, None) and self.__shortPos[instrument]:
				self.__shortPos[instrument].cancelExit()
				self.__shortPos[instrument].exitStop(stopLossPrice, True)
		portfolioValue = self.getBroker().getEquity()
		self.info("Portfolio value: $%.2f" % (portfolioValue))

def main():
	# Load the orders file.
	ordersFile = OrdersFile("orders.csv")
	startPeriod = yearFromTimeSinceEpoch(ordersFile.getFirstDate())
	endPeriod = yearFromTimeSinceEpoch(ordersFile.getLastDate())
	print "First Year", startPeriod
	print "Last Year", endPeriod
	print "Instruments", ordersFile.getInstruments()

	# Download the CSV files from Yahoo Finance
	for instrument in ordersFile.getInstruments():
		tempFeed = yahoofinance.build_feed([instrument], startPeriod, endPeriod, ".")

	feed = yahoofeed.Feed()
	for instrument in ordersFile.getInstruments():
		for year in range(startPeriod, endPeriod + 1):
			csvFileName = instrument + "-" + str(year) + "-yahoofinance.csv"
			feed.addBarsFromCSV(instrument, csvFileName)

	# Run the strategy.
	cash = 100000
	useAdjustedClose = True
	myStrategy = MyStrategy(feed, cash, ordersFile, useAdjustedClose)

	# Attach returns and sharpe ratio analyzers.
	retAnalyzer = returns.Returns()
	myStrategy.attachAnalyzer(retAnalyzer)
	sharpeRatioAnalyzer = sharpe.SharpeRatio()
	myStrategy.attachAnalyzer(sharpeRatioAnalyzer)

	myStrategy.run()

	# Print the results.
	print "Final portfolio value: $%.2f" % myStrategy.getResult()
	print "Anual return: %.2f %%" % (retAnalyzer.getCumulativeReturns()[-1] * 100)
	print "Average daily return: %.2f %%" % (stats.mean(retAnalyzer.getReturns()) * 100)
	print "Std. dev. daily return: %.4f" % (stats.stddev(retAnalyzer.getReturns()))
	print "Sharpe ratio: %.2f" % (sharpeRatioAnalyzer.getSharpeRatio(0))

#main()
