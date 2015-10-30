#!/usr/bin/python

# Country specific market indicator
MARKET = 'SPY'
#MARKET = 'LON_ISF'
#MARKET = 'HK_2833'
TECH_SECTOR = 'QQQ'

# Strategy IDs
BB_SPREAD_ID = 11
BB_SPREAD_STR = 'BB Spread'
BB_SMA_20_CROSSOVER_MTM_ID = 21
BB_SMA_20_CROSSOVER_MTM_STR = 'BB 20 SMA Xover Mtm'
BB_SMA_100_CROSSOVER_MTM_ID = 22
BB_SMA_100_CROSSOVER_MTM_STR = 'BB 100 SMA Xover Mtm'
BB_SMA_200_CROSSOVER_MTM_ID = 23
BB_SMA_200_CROSSOVER_MTM_STR = 'BB 200 SMA Xover Mtm'
EMA_10_CROSSOVER_MTM_ID = 31
EMA_10_CROSSOVER_MTM_STR = 'EMA 10 Xover Mtm'
EMA_20_CROSSOVER_MTM_ID = 32
EMA_20_CROSSOVER_MTM_STR = 'EMA 20 Xover Mtm'
EMA_50_CROSSOVER_MTM_ID = 33
EMA_50_CROSSOVER_MTM_STR = 'EMA 50 Xover Mtm'

# Parameters for generic pre-processing of indicators
DUMMY_START_PORTFOLIO = 1000000

# This parameter is used to control whether we should go, 'Long' or 'Short' only
# or 'Both' for a particular strategy.
BB_SPREAD_LONG_OR_SHORT = 'Both'

# For these stocks we make an exception to trade against the market.
#SPY_EXCEPTIONS = ['AAPL', 'AMZN', 'PCLN', 'NFLX']
SPY_EXCEPTIONS = ['AAPL', 'PCLN']
SPY_CHECK = True
SPY_CASHFLOW_CHECK = False
SPY_VOLUME_CHECK = False
SPY_RSI_CHECK = False
SPY_BASED_LONG_TRADE_NULLIFICATION = 'LONG-SPY-NULL'
SPY_BASED_SHORT_TRADE_NULLIFICATION = 'SHORT-SPY-NULL'
QQQ_CHECK = False
QQQ_CASHFLOW_CHECK = False
QQQ_VOLUME_CHECK = False
QQQ_RSI_CHECK = False

# File for storing the orders generated by a run of a strategy
ORDERS_FILE = "orders.csv"
RESULTS_FILE = "results.csv"
UNEXECUTED_ORDERS_FILE = "unexecuted_orders.csv"
DUMMY_MARKET_PRICE = -1
DUMMY_RANK = -1
DUMMY_ADJ_RATIO = 0

# Lookback window for computing the slope of BB bands
BB_SLOPE_LOOKBACK_WINDOW = 2
BB_SLOPE_LIMIT_FOR_CURVING = 0
BB_CROC_SLOPE = 8
# A small wick is defined as not being a long wick
# A long wick is defined as being more than 40% of the candle.
BB_LONG_WICK = 40
DUMMY_CANDLE_LEN = 0.01

# For computing the percentage increase from the previous close
# when the price breaches the band.
BB_SPREAD_PERCENT_INCREASE_RANGE_1 = 5.0
BB_SPREAD_PERCENT_INCREASE_RANGE_2 = 3.0
BB_SPREAD_PERCENT_INCREASE_RANGE_3 = 2.0
BB_SPREAD_PERCENT_INCREASE_RANGE_4 = 1.5
BB_SPREAD_PERCENT_INCREASE_RANGE_5 = 1.0
BB_SPREAD_PERCENT_INCREASE_RANGE_6 = 2.0
BB_PRICE_RANGE_HIGH_1 = 50
BB_PRICE_RANGE_HIGH_2 = 100
BB_PRICE_RANGE_HIGH_3 = 200
BB_PRICE_RANGE_HIGH_4 = 250

BB_STOP_LOSS_PRICE_DELTA = 0.25

# Lookback window for checking if the price breached the same band recently
BB_BREACH_LOOKBACK_WINDOW = 5
BB_BREACH_TOLERANCE = 0.03
BB_PRICE_CHECK_FOR_TOLERANCE_BREACH = True

EMA_SHORT_1 = 10
EMA_SHORT_2 = 20
EMA_SHORT_3 = 50
SMA_TINY = 3
SMA_SHORT_1 = 20
SMA_LONG_1 = 100
SMA_LONG_2 = 200
SMA_TYPE = SMA_SHORT_1
EMA_TYPE = EMA_SHORT_1

SMA_STOP_PRICE_ADJ_BASED_ON_LOSS_LIMIT = False
SMA_LOSS_CHECK_PERCENT_OR_ABS = 'Percent'
SMA_LOSS_CHECK_PERCENT = 5.0
SMA_LOSS_CHECK_ABS = 0.01

#SMA_PROFIT_CHECK_PERCENT_OR_ABS = 'Abs'
SMA_PROFIT_CHECK_PERCENT_OR_ABS = 'Percent'
SMA_PROFIT_CHECK_PERCENT = 2.0
SMA_PROFIT_CHECK_ABS = 2
EMA_PROFIT_CHECK_PERCENT_OR_ABS = 'Percent'
EMA_PROFIT_CHECK_PERCENT = 1.0
EMA_PROFIT_CHECK_ABS = 2
#SMA_NUM_OF_DAYS_FOR_BOOKING_PROFIT_BEFORE_PROGRESSING_STOP_LOSS = 4
SMA_NUM_OF_DAYS_FOR_BOOKING_PROFIT_BEFORE_PROGRESSING_STOP_LOSS = 8
SMA_STOP_PRICE_ADJ_BASED_ON_NO_PROFIT_FOR_N_DAYS = False
#SMA_STOP_PRICE_ADJ_NOT_BASED_ON_PROFIT_LOCK = True
SMA_STOP_PRICE_ADJ_NOT_BASED_ON_PROFIT_LOCK = False
SMA_STOP_PRICE_PERCENT_OR_ABS = 'Percent'
SMA_ENTRY_DAY_STOP_PRICE_PERCENT = 1
SMA_ENTRY_DAY_STOP_PRICE_ABS = 0.35
SMA_OTHER_DAY_STOP_PRICE_PERCENT = 0.7
SMA_OTHER_DAY_STOP_PRICE_ABS = 0.25
EMA_STOP_PRICE_ADJ_NOT_BASED_ON_PROFIT_LOCK = True
EMA_STOP_PRICE_PERCENT_OR_ABS = 'Percent'
EMA_ENTRY_DAY_STOP_PRICE_PERCENT = 1
EMA_ENTRY_DAY_STOP_PRICE_ABS = 0.35
EMA_OTHER_DAY_STOP_PRICE_PERCENT = 0.7
EMA_OTHER_DAY_STOP_PRICE_ABS = 0.25
EMA_CROSSOVERS_LOOKBACK = 132
SMA_PROGRESS_STOP_LOSS = True
SMA_BREACH_LOOKBACK = 2
SMA_CROSSOVERS_LOOKBACK = 132
SMA_CROSSOVERS_LIMIT_1_LOW_RANGE = 5
SMA_CROSSOVERS_LIMIT_1_HIGH_RANGE = 5
SMA_CROSSOVERS_LIMIT_2_LOW_RANGE = 8
SMA_CROSSOVERS_LIMIT_2_HIGH_RANGE = 11
SMA_CROSSOVERS_LIMIT_3_LOW_RANGE = 12
SMA_CROSSOVERS_LIMIT_3_HIGH_RANGE = 15
EMA_PROGRESS_STOP_LOSS = True
EMA_CROSSOVERS_LIMIT_1_LOW_RANGE = 5
EMA_CROSSOVERS_LIMIT_1_HIGH_RANGE = 5
EMA_CROSSOVERS_LIMIT_2_LOW_RANGE = 8
EMA_CROSSOVERS_LIMIT_2_HIGH_RANGE = 11
EMA_CROSSOVERS_LIMIT_3_LOW_RANGE = 12
EMA_CROSSOVERS_LIMIT_3_HIGH_RANGE = 15
EMA_TREND_BOUNCE_DELTA_PERCENT = 5
EMA_TREND_BB_BREACH_LOOKBACK = 50
EMA_TREND_FURTHER_BREACH_LOOKBACK = 50

PRICE_DELTA = 0.20
RESISTANCE_LOOKBACK_WINDOW = 792
TRADE_DAYS_IN_RESISTANCE_LOOKBACK_WINDOW = 541
RESISTANCE_RECENT_LOOKBACK_WINDOW = 198
RESISTANCE_DELTA = 2
SUPPORT_LOOKBACK_WINDOW = 792
SUPPORT_RECENT_LOOKBACK_WINDOW = 198
SUPPORT_DELTA = 2
PRICE_CUTOFF_FOR_TRADING = 35.0
DAILY_PRICE_RANGE_LOOKBACK_WINDOW = 5
CANDLE_LEN_CHECK_LOOKBACK_WINDOW = 6
DAILY_PRICE_RANGE_FOR_TRADING = 1.0
WICK_REL_LEN_CUTOFF_FOR_TRADING = 60.0
CANDLE_LEN_CUTOFF_COMPARED_TO_AVERAGE_LEN = 1.80
WICK_REL_LEN_CUTOFF_FOR_TIGHTENING = 60.0
SAME_CANDLE_TYPE_AND_TRADE = True

# These lookback window numbers have to be 1 more than the actual lookback.
# For example, if you want to lookback one entry, set the window size to 2.
PRICE_JUMP_LOOKBACK_WINDOW = 2
VOLUME_LOOKBACK_WINDOW = 3
VOLUME_AVG_WINDOW = 6
VOLUME_DELTA = 7
CASH_FLOW_LOOKBACK_WINDOW = 5

RSI_SETTING = 7
RSI_UPPER_LIMIT = 80
RSI_LOWER_LIMIT = 20
RSI_LOOKBACK_WINDOW = 2

ADX_PERIOD = 12
ADX_COUNT = 24
DMI_PERIOD = 28
DMI_COUNT = 29
TALIB_MA_T3 = 3

MACD_FAST_FASTPERIOD = 8
MACD_FAST_SLOWPERIOD = 18
MACD_FAST_SIGNALPERIOD = 6
# MACD price divergence check lookback window
MACD_PRICE_DVX_LOOKBACK = 30
MACD_CHECK_HIGHS = True
MACD_CHECK_LOWS = False

EMA_BREACH_LOOKBACK = 2

#Exit related
BB_SPREAD_PROFIT_CHECK_PERCENT_OR_ABS = 'Percent'
#BB_SPREAD_PROFIT_CHECK_PERCENT = 1
BB_SPREAD_PROFIT_CHECK_PERCENT = 2
BB_SPREAD_PROFIT_CHECK_ABS = 2
BB_SPREAD_STOP_PRICE_ADJ_NOT_BASED_ON_PROFIT_LOCK = False
#BB_SPREAD_STOP_PRICE_ADJ_NOT_BASED_ON_PROFIT_LOCK = True
BB_SPREAD_STOP_PRICE_PERCENT_OR_ABS = 'Percent'
BB_SPREAD_ENTRY_DAY_STOP_PRICE_PERCENT = 1
BB_SPREAD_ENTRY_DAY_STOP_PRICE_ABS = 0.35
BB_SPREAD_PROGRESS_STOP_LOSS = True

SMA_TREND_CHECK = 10
SMA_STOP_LOSS_BASED_ON_ENTRY_STOP_LOSS_DIFFERENCE_AND_UNDER_SMA = False
SMA_DIFFERENCE_BETWEEN_ENTRY_AND_STOP_LOSS_PERCENT_OR_ABS = 'Percent'
SMA_DIFFERENCE_BETWEEN_ENTRY_AND_STOP_LOSS_PERCENT = 3
SMA_DIFFERENCE_BETWEEN_ENTRY_AND_STOP_LOSS_ABS = 2
SMA_MAX_DIFFERENCE_BETWEEN_ENTRY_AND_STOP_LOSS_PERCENT = 100
SMA_MAX_DIFFERENCE_BETWEEN_ENTRY_AND_STOP_LOSS_ABS = 10
SMA_EXIT_IF_CONVERSE_ENTRY = True
SMA_PROGRESS_STOP_LOSS_DELTA_CHANGE_PERCENT = 2
SMA_STOP_LOSS_UNDER_CANDLE_OR_SMA = 'Candle'
#SMA_STOP_LOSS_UNDER_CANDLE_OR_SMA = 'sma'
SMA_STOP_LOSS_OVER_UNDER_PREV_CANDLE = True
#SMA_STOP_LOSS_OVER_UNDER_PREV_CANDLE = False
SMA_ENTRY_STOP_LOSS_OVER_UNDER_PREV_CANDLE = True
#SMA_ENTRY_STOP_LOSS_OVER_UNDER_PREV_CANDLE = True
EMA_EXIT_IF_CONVERSE_ENTRY = False
EMA_PROGRESS_STOP_LOSS_DELTA_CHANGE_PERCENT = 2
EMA_STOP_LOSS_UNDER_CANDLE_OR_EMA = 'EMA'
EMA_STOP_LOSS_OVER_UNDER_PREV_CANDLE = True

# Entry price related
SMA_ENTRY_PRICE_DELTA_PERCENT_OR_ABS = 'Percent'
SMA_ENTRY_PRICE_DELTA_PERCENT = 1
SMA_ENTRY_PRICE_DELTA_ABS = 0.20
EMA_ENTRY_PRICE_DELTA_PERCENT_OR_ABS = 'Percent'
EMA_ENTRY_PRICE_DELTA_PERCENT = 1
EMA_ENTRY_PRICE_DELTA_ABS = 0.25

PRICE_AVG_CHECK_DELTA = 2.0
WICK_PRICE_AVG_CHECK_DELTA = 1.0


## Exit Price Related
FORCE_EXIT_HOLDING_DAYS = 90
MIN_CURRENT_PROFIT = 1.0
SIMULATE_PROFIT_EXIT = False
PROFIT_LOCK_PERCENT_OR_ABS = 'Percent'
PROFIT_LOCK_PERCENT = 2.0
PROFIT_LOCK_ABS = 0.01
PROFIT_LOCK_OPTION = True
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
BB_SPREAD_TRADE_DAY_STOP_LOSS_PERCENTAGE = True


# Money allocation related
ADD_MONEY_TO_CAPUTRE_ORDER = False

PERCENT_OF_CASH_BALANCE_FOR_ENTRY = 0.95
MAX_ALLOCATED_MONEY_FOR_EACH_TRADE = 1.0
MAX_EXPECTED_LOSS_PER_SHORT_SHARE = 5
# This is equivalent to a margin so there could be interest implications which
# we have to deal with later. Additionally, we will have to consider the 
# implications of trades taking around 3 days to settle.
PERCENTAGE_OF_PORTFOLIO_FOR_SHORT = 10 
SIMULATE_INTRA_DAY_EXIT = True
SIMULATE_SPY_TRADE_NULLIFICATION = True
