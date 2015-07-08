#!/usr/bin/env python
from mechanize import Browser
from bs4 import BeautifulSoup
from bs4 import Comment
import json
import datetime
from datetime import timedelta
import dateutil.parser
import csv
import util
import os

def populate_historical_earnings_cal(tickerList):

	for ticker in tickerList:
		mech = Browser()
		url = "http://zacks.thestreet.com/CompanyView.php?ticker=" + ticker
		page = mech.open(url)
		html = page.read()

		soup = BeautifulSoup(html)
		dataTable =  soup.find("div", {"id": "dataTableDiv"})
		extractedSoup =  dataTable(text=lambda text: isinstance(text, Comment))[0].extract()

		earnings_cal = []
		for data in extractedSoup.string.split("=> Array"):
			for d in data.split("=>"):
				if '[1]' in d:
					try:
						YY = '20'
						s = d.rstrip('  [1]').strip()
						s = YY + s
						dt = datetime.datetime(year=int(s[0:4]), month=int(s[4:6]), day=int(s[6:8]))
						if dt not in earnings_cal:
							earnings_cal.append(dt)
					except :
						pass

		##### Write in to CSV file.... #######
		with open('earnings_cal.csv', 'a') as csvfile:
			#### Check if file is already open.... ######
			if os.stat('earnings_cal.csv').st_size == 0:
				fieldnames = ['Ticker', 'Cal_Date']
				writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
				writer.writeheader()
			else:
				writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

			for date in earnings_cal:
				writer.writerow({'Ticker': ticker, 'Cal_Date': date.strftime("%B %d, %Y")})

#def populate_earnings_flag(tickerList):
	

tickerList = util.getTickerListWithSPY()
populate_historical_earnings_cal(tickerList)


#### Test reading the file....
with open('earnings_cal.csv', 'rU') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            dateTime = dateutil.parser.parse(row['Cal_Date'])
            print "####: ", dateTime

