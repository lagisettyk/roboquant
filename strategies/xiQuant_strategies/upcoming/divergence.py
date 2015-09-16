#!/usr/bin/python

import logging

def check_dvx(values1, values2, highsOrLows):
	assert(len(values1) == len(values2))
	ret = []
	for i in range(len(values1)):
		if i == 0:
			continue
		v1 = values1[i]
		v1Prev = values1[i-1]
		v2 = values2[i]
		v2Prev = values2[i-1]
		if v1 is not None and v1Prev is not None and v2 is not None and v2Prev is not None:
			if highsOrLows and v1 >= v1Prev:
				if v2 >= v2Prev:
					continue
				else:
					return True
			elif not highsOrLows and v1 < v1Prev:
				if v2 < v2Prev:
					continue
				else:
					return True
		else:
			return True
	return False

def dvx_impl(values1, values2, start, end, highsOrLows):
	# Get both set of values.
	values1 = values1[start:end]
	values2 = values2[start:end]

	# Check if there's any divergence
	return check_dvx(values1, values2, highsOrLows)
