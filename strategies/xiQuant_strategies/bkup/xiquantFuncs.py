#!/usr/bin/python

import numpy
import StringIO
import csv

from pyalgotrade import dataseries
from pyalgotrade.talibext import indicator
from pyalgotrade.technical import cross
import xiquantStrategyParams as consts
import datetime

# Returns the last values of a dataseries as a numpy.array, or None if not enough values
# could be retrieved from the dataseries.

def dsToNumpyArray(ds, count):
	ret = None
	try:
		values = ds[count * -1:]
		#ret = numpy.array([float(value) for value in values], dtype=np.float)
		ret = numpy.array([value for value in values], dtype=numpy.float)
	except IndexError:
		pass
	except TypeError: # In case we try to convert None to float.
		pass
	return ret

def normalize(value, mean, stdDev):
	return float((value - mean) / stdDev)

def slope(val1, val2):
	return numpy.arctan(float((val1 - val2) / 2)) * 180 / numpy.pi

def slopeForSeries(inpDS, lookbackWin):
	if lookbackWin > 2:
		return indicator.LINEARREG_SLOPE(inpDS, lookbackWin)
	else:
		prevVal = inpDS[-1 * lookbackWin] 
		currVal = inpDS[-1] 
		s = numpy.arctan((currVal - prevVal) / lookbackWin) * 180 / numpy.pi
		#s = float(((currVal - prevVal) / prevVal) * 90)
	return s

def crocMouthCheck(val, prevVal):
	valDiff = abs(val - prevVal)
	if prevVal < consts.BB_SPREAD_EXIT_PRICE_RANGE_HIGH_1:
		if valDiff >= consts.BB_SPREAD_EXIT_PRICE_DELTA_1:
			return True
	if prevVal < consts.BB_SPREAD_EXIT_PRICE_RANGE_HIGH_2:
		if valDiff >= consts.BB_SPREAD_EXIT_PRICE_DELTA_2:
			return True
	if prevVal < consts.BB_SPREAD_EXIT_PRICE_RANGE_HIGH_3:
		if valDiff >= consts.BB_SPREAD_EXIT_PRICE_DELTA_3:
			return True
	if prevVal < consts.BB_SPREAD_EXIT_PRICE_RANGE_HIGH_4:
		if valDiff >= consts.BB_SPREAD_EXIT_PRICE_DELTA_4:
			return True
	if prevVal >= consts.BB_SPREAD_EXIT_PRICE_RANGE_HIGH_4:
		if valDiff >= consts.BB_SPREAD_EXIT_PRICE_DELTA_5:
			return True
	return False

def timestamp_from_datetime(t):
	# Sample: 2008-12-31 23:06:00
	# This custom parsing works faster than:
	# datetime.datetime.strptime(dateTime, "%Y%m%d %H%M%S")
	timestamp = str(t.year) + str(t.month) + str(t.day) + str(t.hour) + str(t.minute) + str(t.second)
	return timestamp

def secondsSinceEpoch(dt):
	epoch = datetime.datetime.utcfromtimestamp(0)
	delta = dt - epoch
	return int(delta.total_seconds())

def getEarningsCalendar(instrument, startPeriod, endPeriod):
	return []

def isEarnings(earningsCalList, date):
	if date.weekday() == 4: # If the analysis day is a Friday
		date = date + datetime.timedelta(days=2)
	else:
		date = date + datetime.timedelta(days=1)
	return date in earningsCalList

def make_fake_csv(data):
	"""Returns a populdated fake csv file object """
	fake_csv = StringIO.StringIO()
	fake_writer = csv.writer(fake_csv, delimiter=',')
	fake_writer.writerows(data) ########## data is nothing but list of lists....
	fake_csv.seek(0)
	return fake_csv

def computeStopPriceDelta(closePrice):
	stopPriceDelta = 0.0
	if closePrice < consts.BB_SPREAD_EXIT_PRICE_RANGE_HIGH_1:
		stopPriceDelta = consts.BB_SPREAD_EXIT_PRICE_DELTA_1
	if closePrice >= consts.BB_SPREAD_EXIT_PRICE_RANGE_HIGH_1 and closePrice < consts.BB_SPREAD_EXIT_PRICE_RANGE_HIGH_2:
		stopPriceDelta = consts.BB_SPREAD_EXIT_PRICE_DELTA_2
	if closePrice >= consts.BB_SPREAD_EXIT_PRICE_RANGE_HIGH_2 and closePrice < consts.BB_SPREAD_EXIT_PRICE_RANGE_HIGH_3:
		stopPriceDelta = consts.BB_SPREAD_EXIT_PRICE_DELTA_3
	if closePrice >= consts.BB_SPREAD_EXIT_PRICE_RANGE_HIGH_3 and closePrice < consts.BB_SPREAD_EXIT_PRICE_RANGE_HIGH_4:
		stopPriceDelta = consts.BB_SPREAD_EXIT_PRICE_DELTA_4
	if closePrice >= consts.BB_SPREAD_EXIT_PRICE_RANGE_HIGH_4:
		stopPriceDelta = consts.BB_SPREAD_EXIT_PRICE_DELTA_5
	return stopPriceDelta

def computeStopPrice(candleLen, bullishOrBearish, openPrice, closePrice, stopPriceDelta):
	stopPrice = 0.0
	compareLen = 0.0
	candleLenAsPricePercent = float(candleLen / closePrice * 100)
	if consts.BB_SPREAD_TRADE_DAY_STOP_LOSS_PERCENTAGE:
		compareLen = candleLenAsPricePercent
	else:
		compareLen = candleLen
	if bullishOrBearish.lower() == "bullish":
		if compareLen <= consts.BB_SPREAD_TRADE_DAY_STOP_LOSS_DELTA_1:
			stopPrice = openPrice - stopPriceDelta
		if compareLen > consts.BB_SPREAD_TRADE_DAY_STOP_LOSS_DELTA_1 and candleLen <= consts.BB_SPREAD_TRADE_DAY_STOP_LOSS_DELTA_2:
			stopPrice = openPrice + candleLen / 3
			if not consts.BB_SPREAD_TRADE_DAY_STOP_LOSS_PERCENTAGE and stopPrice < consts.BB_SPREAD_TRADE_DAY_STOP_LOSS_DELTA_1:
				stopPrice = consts.BB_SPREAD_TRADE_DAY_STOP_LOSS_DELTA_1
		if compareLen > consts.BB_SPREAD_TRADE_DAY_STOP_LOSS_DELTA_2:
			stopPrice = openPrice + candleLen / 2
			if not consts.BB_SPREAD_TRADE_DAY_STOP_LOSS_PERCENTAGE and stopPrice < consts.BB_SPREAD_TRADE_DAY_STOP_LOSS_DELTA_1:
				stopPrice = consts.BB_SPREAD_TRADE_DAY_STOP_LOSS_DELTA_1
	elif bullishOrBearish.lower() == "bearish":
		if compareLen <= consts.BB_SPREAD_TRADE_DAY_STOP_LOSS_DELTA_1:
			stopPrice = openPrice + stopPriceDelta
		if compareLen > consts.BB_SPREAD_TRADE_DAY_STOP_LOSS_DELTA_1 and candleLen <= consts.BB_SPREAD_TRADE_DAY_STOP_LOSS_DELTA_2:
			stopPrice = openPrice - candleLen / 3
			if not consts.BB_SPREAD_TRADE_DAY_STOP_LOSS_PERCENTAGE and stopPrice < consts.BB_SPREAD_TRADE_DAY_STOP_LOSS_DELTA_1:
				stopPrice = consts.BB_SPREAD_TRADE_DAY_STOP_LOSS_DELTA_1
		if compareLen > consts.BB_SPREAD_TRADE_DAY_STOP_LOSS_DELTA_2:
			stopPrice = openPrice - candleLen / 2
			if not consts.BB_SPREAD_TRADE_DAY_STOP_LOSS_PERCENTAGE and stopPrice < consts.BB_SPREAD_TRADE_DAY_STOP_LOSS_DELTA_1:
				stopPrice = consts.BB_SPREAD_TRADE_DAY_STOP_LOSS_DELTA_1
	return stopPrice

def totalCrossovers(thatCrossesDS, beingCrossedDS, startRange=-2, endRange=None):
	noOfCrossAbove = cross.cross_above(thatCrossesDS, beingCrossedDS, startRange, endRange)
	noOfCrossBelow = cross.cross_below(thatCrossesDS, beingCrossedDS, startRange, endRange)
	return noOfCrossAbove + noOfCrossBelow

def totalCrossAbove(thatCrossesDS, beingCrossedDS, startRange=-2, endRange=None):
	noOfCrossAbove = cross.cross_above(thatCrossesDS, beingCrossedDS, startRange, endRange)
	return noOfCrossAbove 

def totalCrossBelow(thatCrossesDS, beingCrossedDS, startRange=-2, endRange=None):
	noOfCrossBelow = cross.cross_below(thatCrossesDS, beingCrossedDS, startRange, endRange)
	return noOfCrossBelow
