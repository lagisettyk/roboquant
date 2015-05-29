#!/usr/bin/python

# Lookback window for computing the slope of BB bands
BB_SLOPE_LOOKBACK_WINDOW = 2
BB_SLOPE_LIMIT_FOR_CURVING = 0
BB_CROC_SLOPE = 20
# A small wick is defined as not being more than 20% of the candle.
BB_SMALL_WICK = 20
# A long wick is defined as being more than 80% of the candle.
BB_LONG_WICK = 65
PERCENT_OF_CASH_BALANCE_FOR_ENTRY = 0.95

# For computing the percentage increase from the previous close
# when the price breaches the band.
BB_SPREAD_PERCENT_INCREASE_RANGE_1 = 5
BB_SPREAD_PERCENT_INCREASE_RANGE_2 = 4
BB_SPREAD_PERCENT_INCREASE_RANGE_3 = 3
BB_SPREAD_PERCENT_INCREASE_RANGE_4 = 2
BB_PRICE_RANGE_HIGH_1 = 50
BB_PRICE_RANGE_HIGH_2 = 100
BB_PRICE_RANGE_HIGH_3 = 200

# Lookback window for checking if the price breached the same band recently
BB_BREACH_LOOKBACK_WINDOW = 5

PRICE_DELTA = 0.35
RESISTANCE_LOOKBACK_WINDOW = 525
RESISTANCE_RECENT_LOOKBACK_WINDOW = 66
RESISTANCE_DELTA = 2
SUPPORT_LOOKBACK_WINDOW = 525
SUPPORT_RECENT_LOOKBACK_WINDOW = 66
SUPPORT_DELTA = 2

# These lookback window numbers have to be 1 more than the actual lookback.
# For example, if you want to lookback one entry, set the window size to 2.
PRICE_JUMP_LOOKBACK_WINDOW = 2
VOLUME_LOOKBACK_WINDOW = 2
CASH_FLOW_LOOKBACK_WINDOW = 4

RSI_SETTING = 7
RSI_UPPER_LIMIT = 70
RSI_LOWER_LIMIT = 30
RSI_LOOKBACK_WINDOW = 2

ADX_SETTING = 12
DMI_SETTING = 28

MACD_FAST_FASTPERIOD = 8
MACD_FAST_SLOWPERIOD = 18
MACD_FAST_SIGNALPERIOD = 6
# MACD price divergence check lookback window
MACD_PRICE_DVX_LOOKBACK = 22
MACD_CHECK_HIGHS = True
MACD_CHECK_LOWS = False

## Exit Price Related
BB_BAND_CURVES_IN_PRICE_TIGHTEN_PERCENT = 2.0
BB_BAND_SECOND_DAY_BELOW = 0.25
