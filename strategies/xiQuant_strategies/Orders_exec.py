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
import xiquantPlatform

class OrdersFile:
	def __init__(self, ordersFile, filterAction='both', rank=10000, fakecsv=False):
		self.__orders = {}
		self.__firstDate = 0
		self.__lastDate = 0
		self.__instruments = []

		if fakecsv:
			reader = csv.DictReader(ordersFile, fieldnames=["timeSinceEpoch", "symbol", "action", "stopPrice", "rank"])
		else:
			reader = csv.DictReader(open(ordersFile, "r"), fieldnames=["timeSinceEpoch", "symbol", "action", "stopPrice", "rank"])
		order = None
		for row in reader:
			timeSinceEpoch = int(row["timeSinceEpoch"])
			ordersList = self.__orders.setdefault(timeSinceEpoch, [])
			if int(row["rank"]) <= rank or rank == -1:
				if filterAction.lower == 'both' or row["action"].lower() != filterAction.lower():
					order = (row["symbol"], row["action"], float(row["stopPrice"]))
				#print "Order being processed from the file: "
				#print order
				#print "Time of the order: "
				#print timeSinceEpoch
				if order is not None:
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

	def getOrdersForTime(self, dateTime):
		return self.__orders.get(dateTime, [])

	def getOrders(self):
		return self.__orders

def yearFromTimeSinceEpoch(secs):
	t = datetime.timedelta(seconds=secs)
	return t.days / 365 + 1970

class MyStrategy(strategy.BacktestingStrategy):
	def __init__(self, feed, cash, ordersFile, useAdjustedClose):
		strategy.BacktestingStrategy.__init__(self, feed, cash)
		self.__feed = feed
		self.__ordersFile = ordersFile
		self.__longPos = {}
		self.__shortPos = {}
		self.__results = {}
		self.__intraDayExits = {}
		self.__intraDayExitPOrL = {}
		self.__intraDayExitDate = {}
		self.__portfolioCashBefore = 0.0
		self.__portfolioBefore = 0.0
		self.__cashKeptAsideForShortLoss = 0.0
		self.getBroker().setCommission(backtesting.NoCommission())

	def onStart(self):
		self.__resultsFile = open(consts.RESULTS_FILE, 'w')
		self.__resultsFile.write("Instrument,Trade-Type,Entry-Date,Entry-Price,Quantity,Portfolio-Value-Pre,Portfolio-Cash-Pre,Portfolio-Value-Post,Portfolio-Cash-Post,Exit-Date,Exit-Price,Portfolio-Value-Pre,Portfolio-Cash-Pre,Portfolio-Value-Post,Portfolio-Cash-Post,PorL,Current-Pos\n")

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
		quantity = "%d" % execInfo.getQuantity()
		if position.getEntryOrder().getAction() == Order.Action.BUY:
			action = "LONG"
		elif position.getEntryOrder().getAction() == Order.Action.SELL:
			action = "SELL"
		elif position.getEntryOrder().getAction() == Order.Action.BUY_TO_COVER:
			action = "BUY_TO_COVER"
		elif position.getEntryOrder().getAction() == Order.Action.SELL_SHORT:
			action = "SHORT"
		else:
			action = "ERROR"
		self.__results[instrument] = instrument + ',' + action + ',' + str(execTime.date()) + ',' + buyPrice + ',' + quantity + ',' + portfolioBefore + ',' + cashBefore + ',' + portfolioAfter + ',' + cashAfter + ','
		self.info("Entered %s for %s, %s shares at %s" % (action, instrument, quantity, buyPrice))
		self.__intraDayExits[instrument] = False
		self.__intraDayExitPOrL[instrument] = 0.0
		self.__intraDayExitDate[instrument] = None

		#The following is not required but still adding it to deal with the issue of stop-buy 
		# and stop-sell issue due to the short or long orders not getting executed for some reason.
		if action.lower() == "long":
			self.__longPos[instrument] = position
		elif action.lower() == "short":
			self.__shortPos[instrument] = position

	def onExitOk(self, position):
		instrument = position.getExitOrder().getInstrument()
		execInfo = position.getExitOrder().getExecutionInfo()
		execTime = execInfo.getDateTime()
		cashBefore = "%0.2f" % self.__portfolioCashBefore
		portfolioBefore = "%0.2f" % self.__portfolioBefore
		cashAfter = "%0.2f" % self.getBroker().getCash(includeShort=False)
		portfolioAfter = "%0.2f" % self.getBroker().getEquity()
		sellPrice = "%0.2f" % execInfo.getPrice()
		profitOrLoss = "%0.2f" % position.getPnL()
		quantity = "%d" % execInfo.getQuantity()
		if position.getEntryOrder().getAction() == Order.Action.BUY:
			action = "LONG"
		elif position.getEntryOrder().getAction() == Order.Action.SELL:
			action = "SELL"
		elif position.getEntryOrder().getAction() == Order.Action.BUY_TO_COVER:
			action = "BUY_TO_COVER"
		elif position.getEntryOrder().getAction() == Order.Action.SELL_SHORT:
			action = "SHORT"
		else:
			action = "ERROR"
		exitDate = str(execTime.date())
		if consts.SIMULATE_INTRA_DAY_EXIT and self.__intraDayExitPOrL[instrument] != 0:
			profitOrLoss = "%0.2f" % self.__intraDayExitPOrL[instrument]
			exitDate = self.__intraDayExitDate[instrument]
		currPos = self.getBroker().getPositions()
		listOfCurrInstrs = list(currPos.keys())
		exitStr = exitDate + ',' + sellPrice + ',' + portfolioBefore + ',' + cashBefore + ',' + portfolioAfter + ',' + cashAfter + ',' + profitOrLoss + ',' + str(listOfCurrInstrs) + '\n'
		self.info("Exited %s for %s, %s shares at %s" % (action, instrument, quantity, sellPrice))
		if self.__results[instrument] is not None:
			self.__results[instrument] += exitStr
			self.__resultsFile.write(self.__results[instrument])
		else:
			self.info("exitStr causing problem: %s" % exitStr)
		self.__results[instrument] = None

		# Adjust the portfolio cash if we closed a short position.
		if position.getEntryOrder().getAction() == Order.Action.BUY_TO_COVER:
			self.__cashKeptAsideForShortLoss -= abs(execInfo.getQuantity()) * consts.MAX_EXPECTED_LOSS_PER_SHORT_SHARE

		self.__intraDayExits[instrument] = False
		self.__intraDayExitPOrL[instrument] = 0.0
		self.__intraDayExitDate[instrument] = None

		#The following is not required but still adding it to deal with the issue of stop-buy 
		# and stop-sell issue due to the short or long orders not getting executed for some reason.
		if action.lower() == "sell":
			self.__longPos[instrument] = None
		elif action.lower() == "buy_to_cover":
			self.__shortPos[instrument] = None

	def onOrderUpdated(self, order):
		if order.isCanceled():
			#raise Exception("Order canceled. Ran out of cash?")
			pass

	def onBars(self, bars):
		self.__portfolioCashBefore = self.getBroker().getCash(includeShort=False)
		self.__portfolioBefore = self.getBroker().getEquity()
		# Cancel all outstanding entry orders from yesterday
		for instrument in self.__ordersFile.getInstruments():
			if self.__longPos.get(instrument, None) and self.__longPos[instrument] and self.__longPos[instrument].entryActive():
				self.__longPos[instrument].cancelEntry()
			if self.__shortPos.get(instrument, None) and self.__shortPos[instrument] and self.__shortPos[instrument].entryActive():
				self.__shortPos[instrument].cancelEntry()

		#bar = bars[self.__instrument]
		#barDateTimeinSecs = int((bars.getDateTime() - datetime.datetime(1970,1,1,0,0,0)).total_seconds())
		barDateTimeinSecs = xiquantFuncs.secondsSinceEpoch(bars.getDateTime())
		self.info("Bar Time: %.2f" % (barDateTimeinSecs))
		self.info(self.__ordersFile.getOrdersForTime(barDateTimeinSecs))
		# The available cash is split equally among all the orders for the day
		noOfOrders = len(self.__ordersFile.getOrdersForTime(barDateTimeinSecs))
		self.info("Total no. of orders: %d" % noOfOrders)
		# Some of the orders could be stop loss orders so we shouldn't be allocating any money
		# to those orders.
		for (instrument, action, price) in self.__ordersFile.getOrdersForTime(barDateTimeinSecs):
			if action.lower() != "buy" and action.lower() != "sell":
				noOfOrders -= 1
		cashAvailable = float(self.getBroker().getCash(includeShort=False) * consts.PERCENT_OF_CASH_BALANCE_FOR_ENTRY)
		self.info("Available cash: %.2f" % cashAvailable)

		for instrument, action, stopPrice in self.__ordersFile.getOrdersForTime(barDateTimeinSecs):
			# Ensure that there's enough cach remaining in the portfolio for closing a short
			# position, with potential losses.
			cashAvailable -= self.__cashKeptAsideForShortLoss
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
						noOfOrders -= 1
						continue 
				self.info("%s %d of %s at $%.2f" % (action, sharesToBuy, instrument, stopPrice))
				self.__longPos[instrument] = self.enterLongStop(instrument, stopPrice, sharesToBuy, True)
				cashAvailable -= cashForInstrument
				noOfOrders -= 1
			elif action.lower() == "sell":
				cashForInstrument = float(cashAvailable / noOfOrders)
				if cashForInstrument > float(cashAvailable * consts.MAX_ALLOCATED_MONEY_FOR_EACH_TRADE):
					cashForInstrument = float(cashAvailable * consts.MAX_ALLOCATED_MONEY_FOR_EACH_TRADE)
				sharesToBuy = int(cashForInstrument / stopPrice)
				self.info("Shares to sell: %d" % sharesToBuy)
				if sharesToBuy < 1:
					# Buy at least 1 share
					if stopPrice < cashAvailable:
						self.info("%s %s of %s at $%.2f" % (action, '1', instrument, stopPrice))
						self.__shortPos[instrument] = self.enterShortStop(instrument, stopPrice, 1, True)
						self.__cashKeptAsideForShortLoss += 1 * consts.MAX_EXPECTED_LOSS_PER_SHORT_SHARE
						cashAvailable -= stopPrice
						noOfOrders -= 1
						continue
					else:
						# Though there isn't enough money to buy one share of this
						# instrument, the money could be sufficient to buy shares of
						# other instruments.
						noOfOrders -= 1
						continue 
				self.info("%s %d of %s at $%.2f" % (action, sharesToBuy, instrument, stopPrice))
				self.__shortPos[instrument] = self.enterShortStop(instrument, stopPrice, sharesToBuy, True)
				self.__cashKeptAsideForShortLoss += sharesToBuy * consts.MAX_EXPECTED_LOSS_PER_SHORT_SHARE
				cashAvailable -= cashForInstrument
				noOfOrders -= 1
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
		for instrument, action, stopLossPrice in self.__ordersFile.getOrdersForTime(stopLossDateTime):
			self.info("%s %s at $%.2f" % (action, instrument, stopLossPrice))
			if self.__longPos.get(instrument, None) and self.__longPos[instrument]:
				self.__longPos[instrument].cancelExit()
				self.__longPos[instrument].exitStop(stopLossPrice, True)
				# Check if exit could have happened on the entry day itself and adjust the profit
				# or loss accordingly.
				actualPorL =  0.0
				exitPrice = 0.0
				if not self.__longPos[instrument].entryActive() and not self.__intraDayExits[instrument]:
					self.__lowDS = self.__feed[instrument].getLowDataSeries()
					self.__highDS = self.__feed[instrument].getHighDataSeries()
					self.__openDS = self.__feed[instrument].getOpenDataSeries()
					execInfo = self.__longPos[instrument].getEntryOrder().getExecutionInfo()
					if execInfo == None:
						continue
					lockProfitPrice = execInfo.getPrice() + consts.PROFIT_LOCK
					if self.__openDS[-1] <= stopLossPrice:
						exitPrice = self.__openDS[-1]
					elif self.__lowDS[-1] <= stopLossPrice:
						exitPrice = stopLossPrice
					elif self.__highDS[-1] >= lockProfitPrice:
						exitPrice = lockProfitPrice
					if exitPrice != 0:
						actualPorL =  (exitPrice - execInfo.getPrice()) * execInfo.getQuantity()
						self.info("Actual P or L for long %s %d shares is %0.2f" % (instrument, execInfo.getQuantity(), actualPorL))
						self.__intraDayExits[instrument] = True
						self.__intraDayExitPOrL[instrument] = actualPorL
						self.__intraDayExitDate[instrument] = str(bars.getDateTime().date())
					#self.__results[instrument] += str(actualPorL) + ',' + str(bars.getDateTime().date()) + ','
			if self.__shortPos.get(instrument, None) and self.__shortPos[instrument]:
				self.__shortPos[instrument].cancelExit()
				self.__shortPos[instrument].exitStop(stopLossPrice, True)
				# Check if exit could have happened on the entry day itself and adjust the profit
				# or loss accordingly.
				actualPorL =  0.0
				exitPrice = 0.0
				if not self.__shortPos[instrument].entryActive() and not self.__intraDayExits[instrument]:
					self.__lowDS = self.__feed[instrument].getLowDataSeries()
					self.__highDS = self.__feed[instrument].getHighDataSeries()
					self.__openDS = self.__feed[instrument].getOpenDataSeries()
					execInfo = self.__shortPos[instrument].getEntryOrder().getExecutionInfo()
					if execInfo == None:
						continue
					lockProfitPrice = execInfo.getPrice() - consts.PROFIT_LOCK
					if self.__openDS[-1] >= stopLossPrice:
						exitPrice = self.__openDS[-1]
					elif self.__highDS[-1] >= stopLossPrice:
						exitPrice = stopLossPrice
					elif self.__lowDS[-1] <= lockProfitPrice:
						exitPrice = lockProfitPrice
					if exitPrice != 0:
						actualPorL =  (execInfo.getPrice() - exitPrice) * execInfo.getQuantity()
						self.info("Actual P or L for short %s %d shares is %0.2f" % (instrument, execInfo.getQuantity(), actualPorL))
						self.__intraDayExits[instrument] = True
						self.__intraDayExitPOrL[instrument] = actualPorL
						self.__intraDayExitDate[instrument] = str(bars.getDateTime().date())
					#self.__results[instrument] += str(actualPorL) + ','  + str(bars.getDateTime().date()) + ','
		# Process any tightened stop loss orders or ones to lock profit
		#stopLossDateTime = int((bars.getDateTime() + datetime.timedelta(seconds=2) - datetime.datetime(1970,1,1,0,0,0)).total_seconds())
		stopLossDateTime = xiquantFuncs.secondsSinceEpoch(bars.getDateTime() + datetime.timedelta(seconds=2))
		for instrument, action, stopLossPrice in self.__ordersFile.getOrdersForTime(stopLossDateTime):
			self.info("%s %s at $%.2f" % (action, instrument, stopLossPrice))
			if self.__longPos.get(instrument, None) and self.__longPos[instrument]:
				self.__longPos[instrument].cancelExit()
				self.__longPos[instrument].exitStop(stopLossPrice, True)
				actualPorL =  0.0
				exitPrice = 0.0
				if not self.__longPos[instrument].entryActive() and not self.__intraDayExits[instrument]:
					self.__lowDS = self.__feed[instrument].getLowDataSeries()
					self.__highDS = self.__feed[instrument].getHighDataSeries()
					execInfo = self.__longPos[instrument].getEntryOrder().getExecutionInfo()
					if execInfo == None:
						continue
					lockProfitPrice = execInfo.getPrice() + consts.PROFIT_LOCK
					if self.__openDS[-1] <= stopLossPrice:
						exitPrice = self.__openDS[-1]
					elif self.__lowDS[-1] <= stopLossPrice:
						exitPrice = stopLossPrice
					elif self.__highDS[-1] >= lockProfitPrice:
						exitPrice = lockProfitPrice
					if exitPrice != 0:
						actualPorL =  (exitPrice - execInfo.getPrice()) * execInfo.getQuantity()
						self.info("Actual P or L for long %s %d shares is %0.2f" % (instrument, execInfo.getQuantity(), actualPorL))
						self.__intraDayExits[instrument] = True
						self.__intraDayExitPOrL[instrument] = actualPorL
						self.__intraDayExitDate[instrument] = str(bars.getDateTime().date())
					#self.__results[instrument] += str(actualPorL) + ',' + str(bars.getDateTime().date()) + ','
			if self.__shortPos.get(instrument, None) and self.__shortPos[instrument]:
				self.__shortPos[instrument].cancelExit()
				self.__shortPos[instrument].exitStop(stopLossPrice, True)
				actualPorL =  0.0
				exitPrice = 0.0
				if not self.__shortPos[instrument].entryActive() and not self.__intraDayExits[instrument]:
					self.__lowDS = self.__feed[instrument].getLowDataSeries()
					self.__highDS = self.__feed[instrument].getHighDataSeries()
					execInfo = self.__shortPos[instrument].getEntryOrder().getExecutionInfo()
					if execInfo == None:
						continue
					lockProfitPrice = execInfo.getPrice() - consts.PROFIT_LOCK
					if self.__openDS[-1] >= stopLossPrice:
						exitPrice = self.__openDS[-1]
					elif self.__highDS[-1] >= stopLossPrice:
						exitPrice = stopLossPrice
					elif self.__lowDS[-1] <= lockProfitPrice:
						exitPrice = lockProfitPrice
					if exitPrice != 0:
						actualPorL =  (execInfo.getPrice() - exitPrice) * execInfo.getQuantity()
						self.info("Actual P or L for short %s %d shares is %0.2f" % (instrument, execInfo.getQuantity(), actualPorL))
						self.__intraDayExits[instrument] = True
						self.__intraDayExitPOrL[instrument] = actualPorL
						self.__intraDayExitDate[instrument] = str(bars.getDateTime().date())
					#self.__results[instrument] += str(actualPorL) + ','  + str(bars.getDateTime().date()) + ','
		portfolioValue = self.getBroker().getEquity()
		self.info("Portfolio value: $%.2f" % (portfolioValue))

def main():
	import dateutil.parser
	startPeriod = dateutil.parser.parse('2005-06-30T08:00:00.000Z')
	endPeriod = dateutil.parser.parse('2014-12-31T08:00:00.000Z')
	# Load the orders file.
	ordersFile = OrdersFile("MasterOrders_Both_Abhi-26.csv", filterAction='both', rank=500)
	#ordersFile = OrdersFile("MasterOrders_Both_SP-500.csv", filterAction='both', rank=500)
	#ordersFile = OrdersFile("orders.csv", filterAction='both', rank=20)
	#startPeriod = yearFromTimeSinceEpoch(ordersFile.getFirstDate())
	#endPeriod = yearFromTimeSinceEpoch(ordersFile.getLastDate())
	print "First Year", startPeriod
	print "Last Year", endPeriod
	print "Instruments", ordersFile.getInstruments()
	#instrument = ordersFile.getInstruments()[0]

	k = 0
	feed = None
	for instrument in ordersFile.getInstruments():
		if k == 0:
			feed = xiquantPlatform.redis_build_feed_EOD_RAW(instrument, startPeriod, endPeriod)
		else:
			feed = xiquantPlatform.add_feeds_EODRAW_CSV(feed, instrument, startPeriod, endPeriod)
		k += 1

	barsDictForCurrAdj = {}
	for instrument in ordersFile.getInstruments():
		barsDictForCurrAdj[instrument] = feed.getBarSeries(instrument)
	feedAdjustedToEndDate = xiquantPlatform.adjustBars(barsDictForCurrAdj, startPeriod, endPeriod, keyFlag=False)

	cash = 100000
	useAdjustedClose = True
	#myStrategy = MyStrategy(feedAdjustedToEndDate, cash, ordersFile, useAdjustedClose)
	myStrategy = MyStrategy(feedAdjustedToEndDate, cash, ordersFile, useAdjustedClose)
	# Attach returns and sharpe ratio analyzers.
	retAnalyzer = returns.Returns()
	myStrategy.attachAnalyzer(retAnalyzer)
	sharpeRatioAnalyzer = sharpe.SharpeRatio()
	myStrategy.attachAnalyzer(sharpeRatioAnalyzer)

	myStrategy.run()
	filteredOrders = ordersFile.getOrders()
	for key in sorted(filteredOrders.iterkeys()):
		print key, filteredOrders[key]

	# Print the results.
	print "Final Portfolio Value: $%.2f" % myStrategy.getResult()
	print "Total Return: %.2f %%" % (retAnalyzer.getCumulativeReturns()[-1] * 100)
	print "Average Daily Return: %.2f %%" % (stats.mean(retAnalyzer.getReturns()) * 100)
	print "Std. Dev. Daily Return: %.4f" % (stats.stddev(retAnalyzer.getReturns()))
	print "Sharpe Ratio: %.2f" % (sharpeRatioAnalyzer.getSharpeRatio(0))


	'''
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
	'''

#main()
