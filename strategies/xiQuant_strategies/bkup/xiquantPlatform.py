#!/usr/bin/python

from pyalgotrade import bar
from pyalgotrade.barfeed import membf
import calendar
from pyalgotrade.bar import BasicBar, Frequency
from pyalgotrade.dataseries import SequenceDataSeries 
from pyalgotrade.dataseries.bards import BarDataSeries



class Feed(membf.BarFeed):
	def __init__(self, frequency, maxLen=1024):
		membf.BarFeed.__init__(self, frequency, maxLen)
		self.__barSeries = {}

	def barsHaveAdjClose(self):
		return True

	def loadBars(self, instrument, bars):
		self.addBarsFromSequence(instrument, bars) #### this is for raw values...
		self.__barSeries[instrument] = bars

	def getBarSeries(self, instrument):
		return self.__barSeries[instrument]

	

class xiQuantBasicBar(bar.BasicBar):
	def __init__(self, dateTime, open_, high, low, close, volume, adjClose, frequency, dividend, split):
		bar.BasicBar.__init__(self, dateTime, open_, high, low, close, volume, adjClose, frequency)
		self.__dividend = dividend
		self.__split = split

	def getDividend(self):
		return self.__dividend

	def getSplit(self):
		return self.__split





class xiQuantAdjustBars():
	def __init__(self, barsDict, startdate, enddate):

		self.__barsDict = barsDict
		self.__startdate = startdate
		self.__enddate = enddate
		self.__DateTimes = {}
		self.__OpenDataSeries = {}
		self.__HighDataSeries = {}
		self.__LowDataSeries = {}
		self.__CloseDataSeries = {}
		self.__VolumeDataSeries = {}
		self.__TypicalDataSeries = {}
		self.__barSeries = {}


	def adjustBars(self):

		for key, value in self.__barsDict.iteritems():

			basicbars = []
			bars = value
			bars_in_dtrange = [bar for bar in bars if self.__startdate.replace(tzinfo=None) <= bar.getDateTime() <= self.__enddate.replace(tzinfo=None)]
			bars_in_dtrange.sort(key=lambda bar: bar.getDateTime(), reverse=True)

			k = 0
			splitdataList = []
			dividendList = []

			for bar in bars_in_dtrange:
				splitdata = float(bar.getSplit())
				dividend = float(bar.getDividend())
				if splitdata != 1.0:
					splitdataList.append(bar.getSplit())
				if dividend != 0.0:
					adjFactor = (bar.getClose() + bar.getDividend()) / bar.getClose()
					dividendList.append(adjFactor)
				#### Special case.... end date / analysis date nothing to do..
				if (k==0):
					bar = BasicBar(bar.getDateTime(), 
						bar.getOpen() , bar.getHigh(), bar.getLow(), bar.getClose(), bar.getVolume(), bar.getClose(), Frequency.DAY)
					basicbars.append(bar)
				else:
					#### Adjust OHLC & Volume data for split adjustments and dividend adjustments
					Open = bar.getOpen()
					High = bar.getHigh()
					Low  = bar.getLow()
					Close = bar.getClose()
					Volume = bar.getVolume()
					### adjust data for splits
					for split in splitdataList:
						Open = Open / split
						High = High / split
						Low  = Low / split
						Close = Close /split
						Volume = Volume * split

					### adjust data for dividends
					for adjFactor in dividendList:
						Open = Open / adjFactor
						High = High / adjFactor
						Low  = Low / adjFactor
						Close = Close / adjFactor
						Volume = Volume * adjFactor
					bar = BasicBar(bar.getDateTime(), 
						Open , High, Low, Close, Volume, Close, Frequency.DAY)
					basicbars.append(bar)
				k +=1


			DateTimes = []
			OpenSeries = SequenceDataSeries(4000)
			HighSeries = SequenceDataSeries(4000)
			LowSeries =  SequenceDataSeries(4000)
			CloseSeries = SequenceDataSeries(4000)
			VolumeSeries = SequenceDataSeries(4000)
			TypicalSeries = SequenceDataSeries(4000)
			barSeries = BarDataSeries(4000)
			basicbars.sort(key=lambda bar: bar.getDateTime(), reverse=False)
			

			for bar in basicbars:
				DateTimes.append(bar.getDateTime())
				OpenSeries.appendWithDateTime(bar.getDateTime(), bar.getOpen())
				HighSeries.appendWithDateTime(bar.getDateTime(), bar.getHigh())
				LowSeries.appendWithDateTime(bar.getDateTime(), bar.getLow())
				CloseSeries.appendWithDateTime(bar.getDateTime(), bar.getClose())
				VolumeSeries.appendWithDateTime(bar.getDateTime(), bar.getVolume())
				TypicalSeries.appendWithDateTime(bar.getDateTime(), (bar.getOpen()+bar.getHigh()+bar.getLow())/3.0)
				barSeries.appendWithDateTime(bar.getDateTime(), bar)


			self.__DateTimes[key+"_adjusted"] = DateTimes
			self.__OpenDataSeries[key+"_adjusted"] = OpenSeries
			self.__HighDataSeries[key+"_adjusted"] = HighSeries
			self.__LowDataSeries[key+"_adjusted"] =  LowSeries
			self.__CloseDataSeries[key+"_adjusted"] = CloseSeries
			self.__VolumeDataSeries[key+"_adjusted"] = VolumeSeries
			self.__TypicalDataSeries[key+"_adjusted"] = TypicalSeries
			self.__barSeries[key+"_adjusted"] = barSeries



	def getDateTimes(self, instrument):
		return self.__DateTimes[instrument]

	def getOpenDataSeries(self, instrument):
		return self.__OpenDataSeries[instrument]

	def getHighDataSeries(self, instrument):
		return self.__HighDataSeries[instrument]

	def getLowDataSeries(self, instrument):
		return self.__LowDataSeries[instrument]

	def getCloseDataSeries(self, instrument):
		return self.__CloseDataSeries[instrument]

	def getVolumeDataSeries(self, instrument):
		return self.__VolumeDataSeries[instrument]

	def getTypicalDataSeries(self, instrument):
		return self.__TypicalDataSeries[instrument]

	def getBarSeries(self, instrument):
		return self.__barSeries[instrument]



def adjustBars(barsDict, startdate, enddate, keyFlag=True):

	feed = Feed(Frequency.DAY, 1024)
	for key, value in barsDict.iteritems():

		bars = value
		basicbars = []
		bars_in_dtrange = [bar for bar in bars if startdate.replace(tzinfo=None) <= bar.getDateTime() <= enddate.replace(tzinfo=None)]
		#bars_in_dtrange = [bar for bar in bars if startdate <= bar.getDateTime() <= enddate]
		bars_in_dtrange.sort(key=lambda bar: bar.getDateTime(), reverse=True)

		k = 0
		splitdataList = []
		dividendList = []
		for bar in bars_in_dtrange:
			splitdata = float(bar.getSplit())
			dividend = float(bar.getDividend())
			if splitdata != 1.0:
				splitdataList.append(bar.getSplit())
			if dividend != 0.0:
				adjFactor = (bar.getClose() + bar.getDividend()) / bar.getClose()
				dividendList.append(adjFactor)
			#### Special case.... end date / analysis date nothing to do..
			if (k==0):
				bar = BasicBar(bar.getDateTime(), 
					bar.getOpen() , bar.getHigh(), bar.getLow(), bar.getClose(), bar.getVolume(), bar.getClose(), Frequency.DAY)
				basicbars.append(bar)
			else:
				#### Adjust OHLC & Volume data for split adjustments and dividend adjustments

				Open = bar.getOpen()
				High = bar.getHigh()
				Low  = bar.getLow()
				Close = bar.getClose()
				Volume = bar.getVolume()
				### adjust data for splits
				for split in splitdataList:
					Open = Open / split
					High = High / split
					Low  = Low / split
					Close = Close /split
					Volume = Volume * split

				### adjust data for dividends
				for adjFactor in dividendList:
					Open = Open / adjFactor
					High = High / adjFactor
					Low  = Low / adjFactor
					Close = Close / adjFactor
					Volume = Volume * adjFactor


				bar = BasicBar(bar.getDateTime(), 
					Open , High, Low, Close, Volume, Close, Frequency.DAY)
				basicbars.append(bar)
			k +=1
		
		if keyFlag:
			feed.loadBars(key+"_adjusted", basicbars)
		else:
			feed.loadBars(key, basicbars)

	return feed

######################################### Feed for accessing the redis/quandl OHLC data via CSV files #############################

def redis_build_feed_EOD_RAW(ticker, stdate, enddate):
	from pyalgotrade.bar import BasicBar, Frequency

	feed = Feed(Frequency.DAY, 1024)
	return add_feeds_EODRAW_CSV(feed, ticker, stdate, enddate)

def add_feeds_EODRAW_CSV(feed, ticker, stdate, enddate):
	import datetime
	from pyalgotrade.utils import dt
	from pyalgotrade.bar import BasicBar, Frequency
	import csv
	import dateutil.parser
	import os

	bd = [] ##### initialize bar data.....
	file_EODRAW = os.path.join(os.path.dirname(__file__), ticker+'_EODRAW.csv')
	with open(file_EODRAW, 'rU') as csvfile:
		reader = csv.DictReader(csvfile)
		for row in reader:
			dateTime = dateutil.parser.parse(row['Date'])
			### Let's only populate the dates passed in the feed...
			if dateTime.date() <= enddate.date() and dateTime.date() >= stdate.date() :
				bar = xiQuantBasicBar(dateTime, 
				float(row['Open']) , float(row['High']), float(row['Low']), float(row['Close']), float(row['Volume']), float(row['AdjClose']), Frequency.DAY, float(row['Dividend']), float(row['Split']) )
				bd.append(bar)
	feed.loadBars(ticker, bd)
	return feed

######################################### Feed for accessing the redis/quandl OHLC data via CSV files #############################
