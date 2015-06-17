#!/usr/bin/python

import numpy

from pyalgotrade import dataseries
from pyalgotrade.talibext import indicator
import xiquantStrategyParams as consts

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

def slope(inpDS, lookbackWin):
	if lookbackWin > 2:
		return LINEARREG_SLOPE(inpDS, lookbackWin)
	else:
		prevVal = inpDS[-1 * lookbackWin] 
		currVal = inpDS[-1] 
		s = numpy.arctan((currVal - prevVal) / 2) * 180 / numpy.pi
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

def isEarnings(instrument, dateTime, tomorrow=False):
	return False
