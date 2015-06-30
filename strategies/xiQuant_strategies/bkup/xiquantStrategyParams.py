#!/usr/bin/python

# File for storing the orders generated by a run of a strategy
ORDERS_FILE = "orders.csv"
RESULTS_FILE = "results.csv"
DUMMY_MARKET_PRICE = -1

# Lookback window for computing the slope of BB bands
BB_SLOPE_LOOKBACK_WINDOW = 2
BB_SLOPE_LIMIT_FOR_CURVING = 0
BB_CROC_SLOPE = 8
# A small wick is defined as not being a long wick
# A long wick is defined as being more than 40% of the candle.
BB_LONG_WICK = 40
PERCENT_OF_CASH_BALANCE_FOR_ENTRY = 0.95

# For computing the percentage increase from the previous close
# when the price breaches the band.
BB_SPREAD_PERCENT_INCREASE_RANGE_1 = 5.0
BB_SPREAD_PERCENT_INCREASE_RANGE_2 = 3.0
BB_SPREAD_PERCENT_INCREASE_RANGE_3 = 2.0
BB_SPREAD_PERCENT_INCREASE_RANGE_4 = 1.5
BB_SPREAD_PERCENT_INCREASE_RANGE_5 = 1.0
BB_PRICE_RANGE_HIGH_1 = 50
BB_PRICE_RANGE_HIGH_2 = 100
BB_PRICE_RANGE_HIGH_3 = 200
BB_PRICE_RANGE_HIGH_4 = 250

BB_STOP_LOSS_PRICE_DELTA = 0.25

# Lookback window for checking if the price breached the same band recently
BB_BREACH_LOOKBACK_WINDOW = 5

# SMA periods
SMA_100 = 100
SMA_200 = 200
SMA_PRICE_DELTA = 2
SMA_ENTRY_DAY_STOP_PRICE_DELTA = 0.35
SMA_OTHER_DAY_STOP_PRICE_DELTA = 0.25
SMA_COMPARE_LOOKBACK = 2

PRICE_DELTA = 0.20
RESISTANCE_LOOKBACK_WINDOW = 792
RESISTANCE_RECENT_LOOKBACK_WINDOW = 198
RESISTANCE_DELTA = 2
SUPPORT_LOOKBACK_WINDOW = 792
SUPPORT_RECENT_LOOKBACK_WINDOW = 198
SUPPORT_DELTA = 2

# These lookback window numbers have to be 1 more than the actual lookback.
# For example, if you want to lookback one entry, set the window size to 2.
PRICE_JUMP_LOOKBACK_WINDOW = 2
VOLUME_LOOKBACK_WINDOW = 2
VOLUME_AVG_WINDOW = 6
VOLUME_DELTA = 7
CASH_FLOW_LOOKBACK_WINDOW = 4

RSI_SETTING = 7
RSI_UPPER_LIMIT = 70
RSI_LOWER_LIMIT = 30
RSI_LOOKBACK_WINDOW = 2

ADX_PERIOD = 12
ADX_COUNT = 24
DMI_PERIOD = 28
DMI_COUNT = 29

MACD_FAST_FASTPERIOD = 8
MACD_FAST_SLOWPERIOD = 18
MACD_FAST_SIGNALPERIOD = 6
# MACD price divergence check lookback window
MACD_PRICE_DVX_LOOKBACK = 30
MACD_CHECK_HIGHS = True
MACD_CHECK_LOWS = False

EMA_SHORT_1 = 10
EMA_SHORT_2 = 20
EMA_SHORT_3 = 50
SMA_TINY = 10
SMA_SHORT_1 = 20
SMA_LONG_1 = 100
SMA_LONG_2 = 200

PRICE_AVG_CHECK_DELTA = 2

## Exit Price Related
PROFIT_LOCK = 2.50
BB_BAND_CURVES_IN_PRICE_TIGHTEN_PERCENT = 2.0
BB_SPREAD_EXIT_PRICE_RANGE_HIGH_1 = 30
BB_SPREAD_EXIT_PRICE_RANGE_HIGH_2 = 49
BB_SPREAD_EXIT_PRICE_RANGE_HIGH_3 = 100
BB_SPREAD_EXIT_PRICE_RANGE_HIGH_4 = 200
BB_SPREAD_EXIT_PRICE_DELTA_1 = 0.25
BB_SPREAD_EXIT_PRICE_DELTA_2 = 0.35
BB_SPREAD_EXIT_PRICE_DELTA_3 = 0.60
BB_SPREAD_EXIT_PRICE_DELTA_4 = 1.00
BB_SPREAD_EXIT_PRICE_DELTA_5 = 1.25
BB_SPREAD_EXIT_TIGHTEN_PRICE_FACTOR = 0.5
BB_SPREAD_TRADE_DAY_STOP_LOSS_DELTA_1 = 3.0
BB_SPREAD_TRADE_DAY_STOP_LOSS_DELTA_2 = 5.0
BB_SPREAD_TRADE_DAY_STOP_LOSS_DELTA_3 = 7.5
