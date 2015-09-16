#!/usr/bin/python
import csv
import datetime
import os

from pyalgotrade.tools import yahoofinance
from pyalgotrade.barfeed import yahoofeed
from pyalgotrade.barfeed import csvfeed
from pyalgotrade import strategy
from pyalgotrade.technical import ma
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
			reader = csv.DictReader(ordersFile, fieldnames=["timeSinceEpoch", "symbol", "action", "stopPrice", "orderID", "adjRatio", "rank"])
		else:
			reader = csv.DictReader(open(ordersFile, "r"), fieldnames=["timeSinceEpoch", "symbol", "action", "stopPrice", "orderID", "adjRatio", "rank"])
		for row in reader:
			order = None
			timeSinceEpoch = int(row["timeSinceEpoch"])
			ordersList = self.__orders.setdefault(timeSinceEpoch, [])
			if int(row["rank"]) <= rank or rank == -1:
				if filterAction.lower == 'both' or row["action"].lower() != filterAction.lower():
					order = (row["symbol"], row["action"], float(row["stopPrice"]), row["orderID"], float(row["adjRatio"]))
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
		self.__SPYFeed = feed["SPY"]
		self.__spyDS = self.__SPYFeed.getCloseDataSeries()
		self.__spyOpenDS = self.__SPYFeed.getOpenDataSeries()
		self.__smaSPYShort1 = ma.SMA(self.__spyDS, consts.SMA_SHORT_1)
		self.__ordersFile = ordersFile
		self.__longPos = {}
		self.__shortPos = {}
		self.__results = {}
		self.__strategiesOutput = None
		self.__intraDayExits = {}
		self.__spyNullified = {}
		self.__stopLossExitPOrL = {}
		self.__stopLossExitDate = {}
		self.__stopLossExitPrice = {}
		self.__profitExitPOrL = {}
		self.__profitExitDate = {}
		self.__profitExitPrice = {}
		self.__portfolioCashBefore = 0.0
		self.__portfolioBefore = 0.0
		self.__prevBarDate = datetime.datetime.now()
		self.__cashKeptAsideForShortLoss = 0.0
		self.__adjRatio = {}
		self.__orderIDs = {}
		self.getBroker().setCommission(backtesting.NoCommission())
		self.__SPYExceptions = consts.SPY_EXCEPTIONS

	def getStrategiesOutput(self):
		return self.__strategiesOutput

	def onStart(self):
		self.__resultsFile = open(consts.RESULTS_FILE, 'w')
		outStr = "Instrument,Trade-Type,Entry-Date,Entry-Price,Quantity,StopLoss-Exit-Date,StopLoss-Exit-Price,StopLoss-Exit-PorL,Profit-Exit-Date,Profit-Exit-Price,Profit-Exit-PorL,Exit-Date,Exit-Price,PorL,Actual-PorL,Strategy,Current-Pos\n"
		self.__resultsFile.write(outStr)
		self.__strategiesOutput = outStr
		self.__unexecutedOrdersFile = open(consts.UNEXECUTED_ORDERS_FILE, 'w')
		self.__unexecutedOrdersFile.write("Unexecuted Orders\n")

	def onFinish(self, bars):
		self.__resultsFile.close()
		self.__unexecutedOrdersFile.close()

	def onEnterOk(self, position):
		instrument = position.getEntryOrder().getInstrument()
		execInfo = position.getEntryOrder().getExecutionInfo()
		execTime = execInfo.getDateTime()
		#execTimeInSecs = xiquantFuncs.secondsSinceEpoch(execTime)
		#execInstrOrderIDTuple = (instrument, str(execTimeInSecs))
		#orderID = self.__orderIDs[execInstrOrderIDTuple]
		# Due to potentially multiple orders, for the same instrument, on the same
		# day, we have to use the approach below for getting the orderID. Using
		# just the timestamp won't give us the correct orderID -- as the context
		# of which strategy lead to that order would be lost.
		orderID = None
		for tuple, pos in self.__longPos.items():
			#self.info("tuple: %s" % str(tuple))
			#self.info("pos: %s" % str(pos))
			if pos == position:
				orderID = tuple[1]
				#self.info("orderID: %s" % orderID)
		if orderID == None:
			for tuple, pos in self.__shortPos.items():
				#self.info("tuple: %s" % str(tuple))
				#self.info("pos: %s" % str(pos))
				if pos == position:
					orderID = tuple[1]
					#self.info("orderID: %s" % orderID)
		entryInstrOrderIDTuple = (instrument, orderID)
		#self.info("entryInstrOrderIDTuple: %s" % str(entryInstrOrderIDTuple))
		cashBefore = "%0.2f" % self.__portfolioCashBefore
		portfolioBefore = "%0.2f" % self.__portfolioBefore
		cashAfter = "%0.2f" % self.getBroker().getCash(includeShort=False)
		portfolioAfter = "%0.2f" % self.getBroker().getEquity()
		buyPrice = "%0.2f" % execInfo.getPrice()
		quantity = "%d" % execInfo.getQuantity()
		if position.getEntryOrder().getAction() == Order.Action.BUY:
			action = "LONG"
			self.info("Entry action: %s" % action)
		elif position.getEntryOrder().getAction() == Order.Action.SELL:
			action = "SELL"
			self.info("Entry action: %s" % action)
		elif position.getEntryOrder().getAction() == Order.Action.BUY_TO_COVER:
			action = "BUY_TO_COVER"
			self.info("Entry action: %s" % action)
		elif position.getEntryOrder().getAction() == Order.Action.SELL_SHORT:
			action = "SHORT"
			self.info("Entry action: %s" % action)
			shortCashAdjustment = abs(execInfo.getQuantity()) * consts.MAX_EXPECTED_LOSS_PER_SHORT_SHARE
			self.__cashKeptAsideForShortLoss += shortCashAdjustment
			self.info("Cash for this short adjustment: %.2f" % shortCashAdjustment)
			self.info("Total cash for short adjustments: %.2f" % self.__cashKeptAsideForShortLoss)
		else:
			action = "ERROR"

		# Check if SPY opened higher/lower on T than T-1's 20 SMA value for
		# bullinsh/bearish trades, otherwise nullify the trade.
		if consts.SIMULATE_SPY_TRADE_NULLIFICATION:
			self.__spyNullified[entryInstrOrderIDTuple] = False
			if not instrument in self.__SPYExceptions:
				if action.lower() == "long":
					if self.__spyOpenDS[-1] < self.__smaSPYShort1[-2]:
						action = consts.SPY_BASED_LONG_TRADE_NULLIFICATION
						self.__spyNullified[entryInstrOrderIDTuple] = True
				elif action.lower() == "short":
					if self.__spyOpenDS[-1] > self.__smaSPYShort1[-2]:
						action = consts.SPY_BASED_SHORT_TRADE_NULLIFICATION
						self.__spyNullified[entryInstrOrderIDTuple] = True

		self.__results[entryInstrOrderIDTuple] = instrument + ',' + action + ',' + str(execTime.date()) + ',' + buyPrice + ',' + quantity + ','
		self.info("Entered %s for %s, %s shares at %s" % (action, instrument, quantity, buyPrice))
		self.__intraDayExits[entryInstrOrderIDTuple] = False
		self.__profitExitPOrL[entryInstrOrderIDTuple] = 0.0
		self.__profitExitDate[entryInstrOrderIDTuple] = None
		self.__profitExitPrice[entryInstrOrderIDTuple] = 0.0
		self.__stopLossExitPOrL[entryInstrOrderIDTuple] = 0.0
		self.__stopLossExitDate[entryInstrOrderIDTuple] = None
		self.__stopLossExitPrice[entryInstrOrderIDTuple] = 0.0

		# The following is not required but still adding it to deal with the stop-buy 
		# and stop-sell issue due to the short or long orders not getting executed for some reason.
		if action.lower() == "long":
			self.__longPos[entryInstrOrderIDTuple] = position
			self.__shortPos[entryInstrOrderIDTuple] = None
		elif action.lower() == "short":
			self.__shortPos[entryInstrOrderIDTuple] = position
			self.__longPos[entryInstrOrderIDTuple] = None

	def onExitOk(self, position):
		instrument = position.getExitOrder().getInstrument()
		execInfo = position.getExitOrder().getExecutionInfo()
		execTime = execInfo.getDateTime()
		#entryExecInfo = position.getEntryOrder().getExecutionInfo()
		#entryExecTime = entryExecInfo.getDateTime()
		#entryExecTimeInSecs = xiquantFuncs.secondsSinceEpoch(entryExecTime)
		#execInstrOrderIDTuple = (instrument, str(entryExecTimeInSecs))
		#orderID = self.__orderIDs[execInstrOrderIDTuple]
		# Due to potentially multiple orders, for the same instrument, on the same
		# day, we have to use the approach below for getting the orderID. Using
		# just the timestamp won't give us the correct orderID -- as the context
		# of which strategy lead to that order would be lost.
		orderID = None
		for tuple, pos in self.__longPos.items():
			#self.info("tuple: %s" % str(tuple))
			#self.info("pos: %s" % str(pos))
			if pos == position:
				orderID = tuple[1]
				#self.info("orderID: %s" % orderID)
		if orderID == None:
			for tuple, pos in self.__shortPos.items():
				#self.info("tuple: %s" % str(tuple))
				#self.info("pos: %s" % str(pos))
				if pos == position:
					orderID = tuple[1]
					#self.info("orderID: %s" % orderID)
		entryInstrOrderIDTuple = (instrument, orderID)
		#self.info("entryInstrOrderIDTuple: %s" % str(entryInstrOrderIDTuple))
		cashBefore = "%0.2f" % self.__portfolioCashBefore
		portfolioBefore = "%0.2f" % self.__portfolioBefore
		cashAfter = "%0.2f" % self.getBroker().getCash(includeShort=False)
		portfolioAfter = "%0.2f" % self.getBroker().getEquity()
		sellPrice = "%0.2f" % execInfo.getPrice()
		profitOrLoss = "%0.2f" % position.getPnL()
		quantity = "%d" % execInfo.getQuantity()
		if position.getEntryOrder().getAction() == Order.Action.BUY:
			action = "SELL"
			self.info("Exit action: %s" % action)
		elif position.getEntryOrder().getAction() == Order.Action.SELL:
			action = "SELL"
			self.info("Exit action: %s" % action)
		elif position.getEntryOrder().getAction() == Order.Action.BUY_TO_COVER:
			action = "BUY_TO_COVER"
			self.info("Exit action: %s" % action)
		elif position.getEntryOrder().getAction() == Order.Action.SELL_SHORT:
			action = "BUY_TO_COVER"
			self.info("Exit action: %s" % action)
		else:
			action = "ERROR"
		exitDate = str(execTime.date())
		profitPOrL = "0.0"
		profitExitDate = "No-Exit"
		profitExitPrice = "0.0"
		if consts.SIMULATE_INTRA_DAY_EXIT and self.__profitExitPrice[entryInstrOrderIDTuple] != 0:
			profitPOrL = "%0.2f" % self.__profitExitPOrL[entryInstrOrderIDTuple]
			profitExitDate = self.__profitExitDate[entryInstrOrderIDTuple]
			profitExitPrice = "%0.2f" % self.__profitExitPrice[entryInstrOrderIDTuple]
		stopLossPOrL = "0.0"
		stopLossExitDate = "No-Exit"
		stopLossExitPrice = "0.0"
		if consts.SIMULATE_INTRA_DAY_EXIT and self.__stopLossExitPrice[entryInstrOrderIDTuple] != 0:
			stopLossPOrL = "%0.2f" % self.__stopLossExitPOrL[entryInstrOrderIDTuple]
			stopLossExitDate = self.__stopLossExitDate[entryInstrOrderIDTuple]
			stopLossExitPrice = "%0.2f" % self.__stopLossExitPrice[entryInstrOrderIDTuple]
		currPos = self.getBroker().getPositions()
		listOfCurrInstrs = list(currPos.keys())
		realPorL = profitOrLoss
		if float(profitPOrL) != 0:
			realPorL = profitPOrL
		if float(stopLossPOrL) != 0:
			realPorL = stopLossPOrL

		# Check if the trade was nullifed due to SPY value check.
		if consts.SIMULATE_SPY_TRADE_NULLIFICATION:
			if self.__spyNullified[entryInstrOrderIDTuple]:
				realPorL = "0.0"

		strat = ''
		stratID = int(orderID[0:2])
		if stratID == consts.BB_SPREAD_ID:
			strat = consts.BB_SPREAD_STR
		elif stratID == consts.BB_SMA_20_CROSSOVER_MTM_ID:
			strat = consts.BB_SMA_20_CROSSOVER_MTM_STR
		elif stratID == consts.BB_SMA_100_CROSSOVER_MTM_ID:
			strat = consts.BB_SMA_100_CROSSOVER_MTM_STR
		elif stratID == consts.BB_SMA_200_CROSSOVER_MTM_ID:
			strat = consts.BB_SMA_200_CROSSOVER_MTM_STR
		elif stratID == consts.EMA_10_CROSSOVER_MTM_ID:
			strat = consts.EMA_10_CROSSOVER_MTM_STR
		elif stratID == consts.EMA_20_CROSSOVER_MTM_ID:
			strat = consts.EMA_20_CROSSOVER_MTM_STR
		elif stratID == consts.EMA_50_CROSSOVER_MTM_ID:
			strat = consts.EMA_50_CROSSOVER_MTM_STR

		exitStr = stopLossExitDate + ',' + stopLossExitPrice + ',' + stopLossPOrL + ',' + profitExitDate + ',' + profitExitPrice + ',' + profitPOrL + ',' + exitDate + ',' + sellPrice + ',' + profitOrLoss + ',' + realPorL + ',' + strat + ',' + str(listOfCurrInstrs) + '\n'
		self.info("Exited %s for %s, %s shares at %s" % (action, instrument, quantity, sellPrice))
		if self.__results[entryInstrOrderIDTuple] is not None:
			self.__results[entryInstrOrderIDTuple] += exitStr
			self.__resultsFile.write(self.__results[entryInstrOrderIDTuple])
			self.__strategiesOutput += self.__results[entryInstrOrderIDTuple]
		else:
			self.info("exitStr causing problem: %s" % exitStr)
		self.__results[entryInstrOrderIDTuple] = None

		# Adjust the portfolio cash if we closed a short position.
		##### When a short position is closed, the exit should be a BUY_TO_COVER but due to some
		##### issue in pyalgotrade library, the exit action is turning out to be a BUY.
		if action.lower() == "buy_to_cover":
			shortCashAdjustment = abs(execInfo.getQuantity()) * consts.MAX_EXPECTED_LOSS_PER_SHORT_SHARE
			self.__cashKeptAsideForShortLoss -= shortCashAdjustment
			self.info("Cash for this buy-close adjustment: %.2f" % shortCashAdjustment)
			self.info("Total cash for short adjustments: %.2f" % self.__cashKeptAsideForShortLoss)

		self.__intraDayExits[entryInstrOrderIDTuple] = False
		self.__spyNullified[entryInstrOrderIDTuple] = False
		self.__profitExitPOrL[entryInstrOrderIDTuple] = 0.0
		self.__profitExitDate[entryInstrOrderIDTuple] = None
		self.__profitExitPrice[entryInstrOrderIDTuple] = 0.0
		self.__stopLossExitPOrL[entryInstrOrderIDTuple] = 0.0
		self.__stopLossExitDate[entryInstrOrderIDTuple] = None
		self.__stopLossExitPrice[entryInstrOrderIDTuple] = 0.0
		self.__adjRatio[entryInstrOrderIDTuple] = 0.0
		self.__orderIDs[entryInstrOrderIDTuple] = None

		#The following is not required but still adding it to deal with the issue of stop-buy 
		# and stop-sell issue due to the short or long orders not getting executed for some reason.
		if action.lower() == "sell":
			self.__longPos[entryInstrOrderIDTuple] = None
		elif action.lower() == "buy_to_cover":
			self.__shortPos[entryInstrOrderIDTuple] = None

	def onOrderUpdated(self, order):
		if order.isCanceled():
			#raise Exception("Order canceled. Ran out of cash?")
			pass

	def onBars(self, bars):
		self.__portfolioCashBefore = self.getBroker().getCash(includeShort=False)
		self.__portfolioBefore = self.getBroker().getEquity()
		# Cancel all outstanding entry orders from yesterday
		for instrument in self.__ordersFile.getInstruments():
			#self.__lowDS = self.__feed[instrument].getLowDataSeries()
			#self.__highDS = self.__feed[instrument].getHighDataSeries()
			#self.__openDS = self.__feed[instrument].getOpenDataSeries()
			#self.info("%s open: %0.2f" % (instrument, self.__openDS[-1]))
			#self.info("%s low: %0.2f" % (instrument, self.__lowDS[-1]))
			#self.info("%s high: %0.2f" % (instrument, self.__highDS[-1]))
			for instrOrderIDTuple in self.__longPos:
				for instrument in instrOrderIDTuple:
					#self.info("instrOrderIDTuple: %s" % str(instrOrderIDTuple))
					if self.__longPos.get(instrOrderIDTuple, None) and self.__longPos[instrOrderIDTuple] and self.__longPos[instrOrderIDTuple].entryActive():
						self.__longPos[instrOrderIDTuple].cancelEntry()
						self.info("Cancelled a LONG order for %s as it didn't get executed." % instrument)
						self.__longPos[instrOrderIDTuple] = None
			for instrOrderIDTuple in self.__shortPos:
				for instrument in instrOrderIDTuple:
					#self.info("instrOrderIDTuple: %s" % str(instrOrderIDTuple))
					if self.__shortPos.get(instrOrderIDTuple, None) and self.__shortPos[instrOrderIDTuple] and self.__shortPos[instrOrderIDTuple].entryActive():
						self.__shortPos[instrOrderIDTuple].cancelEntry()
						self.info("Cancelled a SHORT order for %s as it didn't get executed." % instrument)
						self.__shortPos[instrOrderIDTuple] = None

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
		for (instrument, action, price, orderID, adjRatio) in self.__ordersFile.getOrdersForTime(barDateTimeinSecs):
			if action.lower() != "buy" and action.lower() != "sell":
				noOfOrders -= 1
		cashAvailable = float(self.getBroker().getCash(includeShort=False) * consts.PERCENT_OF_CASH_BALANCE_FOR_ENTRY)
		self.info("Available cash: %.2f" % cashAvailable)

		for instrument, action, stopPrice, orderID, adjRatio in self.__ordersFile.getOrdersForTime(barDateTimeinSecs):
			instrOrderIDTuple = (instrument, orderID)
			#self.info("instrOrderIDTuple: %s" % str(instrOrderIDTuple))
			orderTimeStamp = orderID[3:]
			self.info("orderTimeStamp: %s" % str(orderTimeStamp))
			self.__orderIDs[(instrument, orderTimeStamp)] = orderID
			self.info("orderID: %s" % orderID)
			self.info("orderIDs entry: %s" % str((instrument, orderTimeStamp)))
			# Ensure that there's enough cach remaining in the portfolio for closing a short
			# position, with potential losses.
			cashAvailable -= self.__cashKeptAsideForShortLoss
			self.info("Available cash after short adjustment: %.2f" % cashAvailable)
			if action.lower() == "buy":
				if adjRatio != 0:
					self.__adjRatio[instrOrderIDTuple] = adjRatio
				cashForInstrument = float(cashAvailable / noOfOrders)
				if cashForInstrument > float(cashAvailable * consts.MAX_ALLOCATED_MONEY_FOR_EACH_TRADE):
					cashForInstrument = float(cashAvailable * consts.MAX_ALLOCATED_MONEY_FOR_EACH_TRADE)
				sharesToBuy = int(cashForInstrument / stopPrice)
				self.info("Shares to buy: %d" % sharesToBuy)
				if sharesToBuy < 1:
					# Buy at least 1 share
					if stopPrice < cashAvailable:
						self.info("%s %s of %s at $%.2f" % (action, '1', instrument, stopPrice))
						self.__longPos[instrOrderIDTuple] = self.enterLongStop(instrument, stopPrice, 1, True)
						cashAvailable -= stopPrice
						noOfOrders -= 1
						continue
					else:
						# Though there isn't enough money to buy one share of this
						# instrument, the money could be sufficient to buy shares of
						# other instruments.
						noOfOrders -= 1
						# Write this order to the file for unexecuted orders
						self.__unexecutedOrdersFile.write("%s, %s, %s\n" % (instrument, 'Buy', str(stopPrice)))
						continue 
				self.info("%s %d of %s at $%.2f" % (action, sharesToBuy, instrument, stopPrice))
				self.__longPos[instrOrderIDTuple] = self.enterLongStop(instrument, stopPrice, sharesToBuy, True)
				cashAvailable -= cashForInstrument
				noOfOrders -= 1
			elif action.lower() == "sell":
				if adjRatio != 0:
					self.__adjRatio[instrOrderIDTuple] = adjRatio
				cashForInstrument = float(cashAvailable / noOfOrders)
				if cashForInstrument > float(cashAvailable * consts.MAX_ALLOCATED_MONEY_FOR_EACH_TRADE):
					cashForInstrument = float(cashAvailable * consts.MAX_ALLOCATED_MONEY_FOR_EACH_TRADE)
				sharesToBuy = int(cashForInstrument / stopPrice)
				self.info("Shares to sell: %d" % sharesToBuy)
				if sharesToBuy < 1:
					# Buy at least 1 share
					if stopPrice < cashAvailable:
						self.info("%s %s of %s at $%.2f" % (action, '1', instrument, stopPrice))
						self.__shortPos[instrOrderIDTuple] = self.enterShortStop(instrument, stopPrice, 1, True)
						#self.__cashKeptAsideForShortLoss += 1 * consts.MAX_EXPECTED_LOSS_PER_SHORT_SHARE
						cashAvailable -= stopPrice
						noOfOrders -= 1
						continue
					else:
						# Though there isn't enough money to buy one share of this
						# instrument, the money could be sufficient to buy shares of
						# other instruments.
						noOfOrders -= 1
						# Write this order to the file for unexecuted orders
						self.__unexecutedOrdersFile.write("%s, %s, %s\n" % (instrument, 'Sell', str(stopPrice)))
						continue 
				self.info("%s %d of %s at $%.2f" % (action, sharesToBuy, instrument, stopPrice))
				self.__shortPos[instrOrderIDTuple] = self.enterShortStop(instrument, stopPrice, sharesToBuy, True)
				#self.__cashKeptAsideForShortLoss += sharesToBuy * consts.MAX_EXPECTED_LOSS_PER_SHORT_SHARE
				cashAvailable -= cashForInstrument
				noOfOrders -= 1
			elif action.lower() == "tightened-stop-buy" or action.lower() == "stop-buy":
				if self.__shortPos.get(instrOrderIDTuple, None) and self.__shortPos[instrOrderIDTuple]:
					self.__shortPos[instrOrderIDTuple].cancelExit()
					self.__shortPos[instrOrderIDTuple].exitStop(stopPrice, True)
			elif action.lower() == "tightened-stop-sell" or action.lower() == "stop-sell":
				if self.__longPos.get(instrOrderIDTuple, None) and self.__longPos[instrOrderIDTuple]:
					self.__longPos[instrOrderIDTuple].cancelExit()
					self.__longPos[instrOrderIDTuple].exitStop(stopPrice, True)
			elif action.lower() == "buy-market":
				if self.__shortPos.get(instrOrderIDTuple, None) and self.__shortPos[instrOrderIDTuple]:
					self.info("Processing a Buy-Market order.")
					self.__shortPos[instrOrderIDTuple].cancelExit()
					self.__shortPos[instrOrderIDTuple].exitMarket()
			elif action.lower() == "sell-market":
				if self.__longPos.get(instrOrderIDTuple, None) and self.__longPos[instrOrderIDTuple]:
					self.info("Processing a Sell-Market order.")
					self.__longPos[instrOrderIDTuple].cancelExit()
					self.__longPos[instrOrderIDTuple].exitMarket()
			else:
				pass # No need to take any action for Cover-Buy or Sell-Close entries.
		# There must be a stop loss order to process if a Buy or Sell order was processed in the
		# above step.
		stopLossDateTime = xiquantFuncs.secondsSinceEpoch(bars.getDateTime() + datetime.timedelta(seconds=1))
		for instrument, action, stopLossPrice, orderID, adjRatio in self.__ordersFile.getOrdersForTime(stopLossDateTime):
			self.info("Entry Day:%s: %s %s at $%.2f" % (str(stopLossDateTime), action, instrument, stopLossPrice))
			instrOrderIDTuple = (instrument, orderID)
			#self.info("instrOrderIDTuple: %s" % str(instrOrderIDTuple))
			orderTimeStamp = orderID[3:]
			self.info("orderTimeStamp: %s" % str(orderTimeStamp))
			self.__orderIDs[(instrument, orderTimeStamp)] = orderID
			self.info("orderID: %s" % orderID)
			self.info("orderIDs entry: %s" % str((instrument, orderTimeStamp)))
			if self.__longPos.get(instrOrderIDTuple, None) and self.__longPos[instrOrderIDTuple]:
				self.__longPos[instrOrderIDTuple].cancelExit()
				self.__longPos[instrOrderIDTuple].exitStop(stopLossPrice, True)
				# Check if exit could have happened on the entry day itself and adjust the profit
				# or loss accordingly.
				actualPorL =  0.0
				exitPrice = 0.0
				# The check for __intraDayExits being none is important due to
				# the following reason:
				# Since we added the intraday profit exit, we are now 
				# processing the stop-loss orders as well -- which we were 
				# not processing earlier. So, if a Buy/Sell order is filtered 
				# out but the corresponding stop-loss orders aren't, while 
				# trying to process the stop-loss order looking back from a 
				# Buy/Sell order the __longPos[instrument]/
				# __shortPos[instrument] will not be none (as it was 
				# initialized by the next Buy/Sell order that didn't get 
				# filtered out) but the __intraDayExits[instrument] will be 
				# none as it was never instantiated in onEnterOk (since the 
				# next unfiltered Buy/Sell is not yet executed). 
				# A very unique case :^)
				if not self.__longPos[instrOrderIDTuple].entryActive() and self.__intraDayExits.get(instrOrderIDTuple, None) != None and not self.__intraDayExits[instrOrderIDTuple]:
					self.__lowDS = self.__feed[instrument].getLowDataSeries()
					self.__highDS = self.__feed[instrument].getHighDataSeries()
					self.__openDS = self.__feed[instrument].getOpenDataSeries()
					execInfo = self.__longPos[instrOrderIDTuple].getEntryOrder().getExecutionInfo()
					if execInfo == None:
						continue
					# Adjust the profit lock price -- the price is already adjusted by the ratio
					# so the profit should be as well.
					lockProfitPrice = execInfo.getPrice() + consts.PROFIT_LOCK * self.__adjRatio[instrOrderIDTuple]
					self.info("lockProfitPrice: %0.2f" % lockProfitPrice)
					if self.__openDS[-1] <= stopLossPrice:
						exitPrice = self.__openDS[-1]
						self.info("exitPrice is self.__openDS[-1]")
					elif self.__lowDS[-1] <= stopLossPrice:
						exitPrice = stopLossPrice
						self.info("exitPrice is stopLossPrice")
					if exitPrice != 0:
						self.info("exitPrice: %0.2f" % exitPrice)
						actualPorL =  (exitPrice - execInfo.getPrice()) * execInfo.getQuantity()
						self.info("Actual P or L for long %s %d shares is %0.2f" % (instrument, execInfo.getQuantity(), actualPorL))
						self.__intraDayExits[instrOrderIDTuple] = True
						self.__stopLossExitPOrL[instrOrderIDTuple] = actualPorL
						self.__stopLossExitPrice[instrOrderIDTuple] = exitPrice
						self.__stopLossExitDate[instrOrderIDTuple] = str(bars.getDateTime().date())
					exitPrice = 0.0
					if self.__highDS[-1] >= lockProfitPrice:
						exitPrice = lockProfitPrice
						self.info("exitPrice is lockProfitPrice")
					if exitPrice != 0:
						self.info("exitPrice: %0.2f" % exitPrice)
						actualPorL =  (exitPrice - execInfo.getPrice()) * execInfo.getQuantity()
						self.info("Actual P or L for long %s %d shares is %0.2f" % (instrument, execInfo.getQuantity(), actualPorL))
						self.__intraDayExits[instrOrderIDTuple] = True
						self.__profitExitPOrL[instrOrderIDTuple] = actualPorL
						self.__profitExitPrice[instrOrderIDTuple] = exitPrice
						self.__profitExitDate[instrOrderIDTuple] = str(bars.getDateTime().date())
					#self.__results[instrOrderIDTuple] += str(actualPorL) + ',' + str(bars.getDateTime().date()) + ','
			if self.__shortPos.get(instrOrderIDTuple, None) and self.__shortPos[instrOrderIDTuple]:
				self.__shortPos[instrOrderIDTuple].cancelExit()
				self.__shortPos[instrOrderIDTuple].exitStop(stopLossPrice, True)
				# Check if exit could have happened on the entry day itself and adjust the profit
				# or loss accordingly.
				actualPorL =  0.0
				exitPrice = 0.0
				# The check for __intraDayExits being none is important due to
				# the following reason:
				# Since we added the intraday profit exit, we are now 
				# processing the stop-loss orders as well -- which we were 
				# not processing earlier. So, if a Buy/Sell order is filtered 
				# out but the corresponding stop-loss orders aren't, while 
				# trying to process the stop-loss order looking back from a 
				# Buy/Sell order the __longPos[instrument]/
				# __shortPos[instrument] will not be none (as it was 
				# initialized by the next Buy/Sell order that didn't get 
				# filtered out) but the __intraDayExits[instrument] will be 
				# none as it was never instantiated in onEnterOk (since the 
				# next unfiltered Buy/Sell is not yet executed). 
				# A very unique case :^)
				if not self.__shortPos[instrOrderIDTuple].entryActive() and self.__intraDayExits.get(instrOrderIDTuple, None) != None and not self.__intraDayExits[instrOrderIDTuple]:
					self.__lowDS = self.__feed[instrument].getLowDataSeries()
					self.__highDS = self.__feed[instrument].getHighDataSeries()
					self.__openDS = self.__feed[instrument].getOpenDataSeries()
					execInfo = self.__shortPos[instrOrderIDTuple].getEntryOrder().getExecutionInfo()
					if execInfo == None:
						continue
					# Adjust the profit lock price -- the price is already adjusted by the ratio
					# so the profit should be as well.
					lockProfitPrice = execInfo.getPrice() - consts.PROFIT_LOCK * self.__adjRatio[instrOrderIDTuple]
					self.info("lockProfitPrice: %0.2f" % lockProfitPrice)
					if self.__openDS[-1] >= stopLossPrice:
						exitPrice = self.__openDS[-1]
						self.info("exitPrice is self.__openDS[-1]")
					elif self.__highDS[-1] >= stopLossPrice:
						exitPrice = stopLossPrice
						self.info("exitPrice is stopLossPrice")
					if exitPrice != 0:
						self.info("exitPrice: %0.2f" % exitPrice)
						actualPorL =  (exitPrice - execInfo.getPrice()) * -1 * execInfo.getQuantity()
						self.info("Actual P or L for long %s %d shares is %0.2f" % (instrument, execInfo.getQuantity(), actualPorL))
						self.__intraDayExits[instrOrderIDTuple] = True
						self.__stopLossExitPOrL[instrOrderIDTuple] = actualPorL
						self.__stopLossExitPrice[instrOrderIDTuple] = exitPrice
						self.__stopLossExitDate[instrOrderIDTuple] = str(bars.getDateTime().date())
					exitPrice = 0.0
					if self.__lowDS[-1] <= lockProfitPrice:
						exitPrice = lockProfitPrice
						self.info("exitPrice is lockProfitPrice")
					if exitPrice != 0:
						self.info("exitPrice: %0.2f" % exitPrice)
						actualPorL =  (exitPrice - execInfo.getPrice()) * -1 * execInfo.getQuantity()
						self.info("Actual P or L for short %s %d shares is %0.2f" % (instrument, execInfo.getQuantity(), actualPorL))
						self.__intraDayExits[instrOrderIDTuple] = True
						self.__profitExitPOrL[instrOrderIDTuple] = actualPorL
						self.__profitExitPrice[instrOrderIDTuple] = exitPrice
						self.__profitExitDate[instrOrderIDTuple] = str(bars.getDateTime().date())
				#self.__results[instrOrderIDTuple] += str(actualPorL) + ','  + str(bars.getDateTime().date()) + ','
		# Process any tightened stop loss orders
		stopLossDateTime = xiquantFuncs.secondsSinceEpoch(bars.getDateTime() + datetime.timedelta(seconds=2))
		self.info("Later Day stop loss order time: %s" % str(stopLossDateTime))
		for instrument, action, stopLossPrice, orderID, adjRatio in self.__ordersFile.getOrdersForTime(stopLossDateTime):
			self.info("Later Day:%s: %s %s at $%.2f" % (str(stopLossDateTime), action, instrument, stopLossPrice))
			instrOrderIDTuple = (instrument, orderID)
			#self.info("instrOrderIDTuple: %s" % str(instrOrderIDTuple))
			orderTimeStamp = orderID[3:]
			self.info("orderTimeStamp: %s" % str(orderTimeStamp))
			self.__orderIDs[(instrument, orderTimeStamp)] = orderID
			self.info("orderID: %s" % orderID)
			self.info("orderIDs entry: %s" % str((instrument, orderTimeStamp)))
			if self.__longPos.get(instrOrderIDTuple, None) and self.__longPos[instrOrderIDTuple]:
				self.__longPos[instrOrderIDTuple].cancelExit()
				self.__longPos[instrOrderIDTuple].exitStop(stopLossPrice, True)
			if self.__shortPos.get(instrOrderIDTuple, None) and self.__shortPos[instrOrderIDTuple]:
				self.__shortPos[instrOrderIDTuple].cancelExit()
				self.__shortPos[instrOrderIDTuple].exitStop(stopLossPrice, True)

		# Simulate intraday exit to lock profit
		stopLossDateTime = xiquantFuncs.secondsSinceEpoch(self.__prevBarDate + datetime.timedelta(seconds=2))
		self.info("stopLossDateTime: %s" % str(stopLossDateTime))
		for instrument, action, stopLossPrice, orderID, adjRatio in self.__ordersFile.getOrdersForTime(stopLossDateTime):
			self.info("Later Day:%s: %s %s at $%.2f" % (str(stopLossDateTime), action, instrument, stopLossPrice))
			instrOrderIDTuple = (instrument, orderID)
			#self.info("instrOrderIDTuple: %s" % str(instrOrderIDTuple))
			orderTimeStamp = orderID[3:]
			self.info("orderTimeStamp: %s" % str(orderTimeStamp))
			self.__orderIDs[(instrument, orderTimeStamp)] = orderID
			self.info("orderID: %s" % orderID)
			self.info("orderIDs entry: %s" % str((instrument, orderTimeStamp)))
			if self.__longPos.get(instrOrderIDTuple, None) and self.__longPos[instrOrderIDTuple]:
				actualPorL =  0.0
				exitPrice = 0.0
				if not self.__longPos[instrOrderIDTuple].entryActive() and self.__intraDayExits.get(instrOrderIDTuple, None) != None and not self.__intraDayExits[instrOrderIDTuple]:
					self.__lowDS = self.__feed[instrument].getLowDataSeries()
					self.__highDS = self.__feed[instrument].getHighDataSeries()
					self.__openDS = self.__feed[instrument].getOpenDataSeries()
					execInfo = self.__longPos[instrOrderIDTuple].getEntryOrder().getExecutionInfo()
					if execInfo == None:
						continue
					# Adjust the profit lock price -- the price is already adjusted by the ratio
					# so the profit should be as well.
					lockProfitPrice = execInfo.getPrice() + consts.PROFIT_LOCK * self.__adjRatio[instrOrderIDTuple]
					self.info("lockProfitPrice: %0.2f" % lockProfitPrice)
					if self.__openDS[-1] <= stopLossPrice:
						exitPrice = self.__openDS[-1]
						self.info("exitPrice is self.__openDS[-1]")
					elif self.__lowDS[-1] <= stopLossPrice:
						exitPrice = stopLossPrice
						self.info("exitPrice is stopLossPrice")
					if exitPrice != 0:
						self.info("exitPrice: %0.2f" % exitPrice)
						actualPorL =  (exitPrice - execInfo.getPrice()) * execInfo.getQuantity()
						self.info("Actual P or L for long %s %d shares is %0.2f" % (instrument, execInfo.getQuantity(), actualPorL))
						self.__intraDayExits[instrOrderIDTuple] = True
						self.__stopLossExitPOrL[instrOrderIDTuple] = actualPorL
						self.__stopLossExitPrice[instrOrderIDTuple] = exitPrice
						self.__stopLossExitDate[instrOrderIDTuple] = str(bars.getDateTime().date())
					exitPrice = 0.0
					if self.__highDS[-1] >= lockProfitPrice:
						exitPrice = lockProfitPrice
						self.info("exitPrice is lockProfitPrice")
					if exitPrice != 0:
						self.info("exitPrice: %0.2f" % exitPrice)
						actualPorL =  (exitPrice - execInfo.getPrice()) * execInfo.getQuantity()
						self.info("Actual P or L for long %s %d shares is %0.2f" % (instrument, execInfo.getQuantity(), actualPorL))
						self.__intraDayExits[instrOrderIDTuple] = True
						self.__profitExitPOrL[instrOrderIDTuple] = actualPorL
						self.__profitExitPrice[instrOrderIDTuple] = exitPrice
						self.__profitExitDate[instrOrderIDTuple] = str(bars.getDateTime().date())
					#self.__results[instrOrderIDTuple] += str(actualPorL) + ',' + str(bars.getDateTime().date()) + ','
			if self.__shortPos.get(instrOrderIDTuple, None) and self.__shortPos[instrOrderIDTuple]:
				actualPorL =  0.0
				exitPrice = 0.0
				if not self.__shortPos[instrOrderIDTuple].entryActive() and self.__intraDayExits.get(instrOrderIDTuple, None) != None and not self.__intraDayExits[instrOrderIDTuple]:
					self.__lowDS = self.__feed[instrument].getLowDataSeries()
					self.__highDS = self.__feed[instrument].getHighDataSeries()
					self.__openDS = self.__feed[instrument].getOpenDataSeries()
					execInfo = self.__shortPos[instrOrderIDTuple].getEntryOrder().getExecutionInfo()
					if execInfo == None:
						continue
					# Adjust the profit lock price -- the price is already adjusted by the ratio
					# so the profit should be as well.
					lockProfitPrice = execInfo.getPrice() - consts.PROFIT_LOCK * self.__adjRatio[instrOrderIDTuple]
					self.info("lockProfitPrice: %0.2f" % lockProfitPrice)
					if self.__openDS[-1] >= stopLossPrice:
						exitPrice = self.__openDS[-1]
						self.info("exitPrice is self.__openDS[-1]")
					elif self.__highDS[-1] >= stopLossPrice:
						exitPrice = stopLossPrice
						self.info("exitPrice is stopLossPrice")
					if exitPrice != 0:
						self.info("exitPrice: %0.2f" % exitPrice)
						actualPorL =  (exitPrice - execInfo.getPrice()) * -1 * execInfo.getQuantity()
						self.info("Actual P or L for long %s %d shares is %0.2f" % (instrument, execInfo.getQuantity(), actualPorL))
						self.__intraDayExits[instrOrderIDTuple] = True
						self.__stopLossExitPOrL[instrOrderIDTuple] = actualPorL
						self.__stopLossExitPrice[instrOrderIDTuple] = exitPrice
						self.__stopLossExitDate[instrOrderIDTuple] = str(bars.getDateTime().date())
					exitPrice = 0.0
					if self.__lowDS[-1] <= lockProfitPrice:
						exitPrice = lockProfitPrice
						self.info("exitPrice is lockProfitPrice")
					if exitPrice != 0:
						self.info("exitPrice: %0.2f" % exitPrice)
						actualPorL =  (exitPrice - execInfo.getPrice()) * -1 * execInfo.getQuantity()
						self.info("Actual P or L for short %s %d shares is %0.2f" % (instrument, execInfo.getQuantity(), actualPorL))
						self.__intraDayExits[instrOrderIDTuple] = True
						self.__profitExitPOrL[instrOrderIDTuple] = actualPorL
						self.__profitExitPrice[instrOrderIDTuple] = exitPrice
						self.__profitExitDate[instrOrderIDTuple] = str(bars.getDateTime().date())
					#self.__results[instrOrderIDTuple] += str(actualPorL) + ','  + str(bars.getDateTime().date()) + ','
		self.__prevBarDate = bars.getDateTime()
		portfolioValue = self.getBroker().getEquity()
		self.info("Portfolio value: $%.2f" % (portfolioValue))

def main():
	import dateutil.parser
	startPeriod = dateutil.parser.parse('2005-06-30T08:00:00.000Z')
	endPeriod = dateutil.parser.parse('2014-12-31T08:00:00.000Z')
	# Load the orders file.
	#ordersFile = OrdersFile("MasterOrders_Both_Abhi-26.csv", filterAction='sell', rank=500)
	#ordersFile = OrdersFile("MasterOrders_Both_SP-500.csv", filterAction='both', rank=500)
	ordersFile = OrdersFile("orders.csv", filterAction='both', rank=20)
	#ordersFile = OrdersFile("Problem-Orders.csv", filterAction='both', rank=20)
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

	# Add the SPY bars to support the simulation of whether we should have
	# entered certain trades or not -- based on the SPY opening higher/lower
	# than 20 SMA value for bullish/bearish trades.
	feed = xiquantPlatform.add_feeds_EODRAW_CSV(feed, 'SPY', startPeriod, endPeriod)

	barsDictForCurrAdj = {}
	for instrument in ordersFile.getInstruments():
		barsDictForCurrAdj[instrument] = feed.getBarSeries(instrument)
	barsDictForCurrAdj['SPY'] = feed.getBarSeries('SPY')
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
	print "Strategy Results:\n" 
	print myStrategy.getStrategiesOutput()

#main()
