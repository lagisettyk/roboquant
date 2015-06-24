import csv
import datetime
import dateutil.parser
import os
import util
from rq import Queue
import redis
import time

'''
def processOptionsFile(inputfile, outputfile):
	header = True
	keyList = [] ### we need only option row per ticker per type...
	#with open('L3_options_20131101.csv', 'rU') as fin:
	with open(inputfile, 'rU') as fin:
		with open(outputfile, 'w') as fout :
			reader = csv.DictReader(fin)
			for row in reader:
				#### Apply above stated rules to filter the rows...
				data_date = dateutil.parser.parse(row[' DataDate'])
				exp_date =  dateutil.parser.parse(row['Expiration'])
				intrinsicVal = float(row['UnderlyingPrice']) - float(row['Strike'])
				key = row['UnderlyingSymbol'] + row['Type']
				fieldnames = ['UnderlyingSymbol',	'UnderlyingPrice',	'Flags',	'OptionSymbol',	'Type',\
								'Expiration', 'DataDate', 'Strike',	'Last',	'Bid', 'Ask', 'Volume',	'OpenInterest',	'T1OpenInterest', \
									'IVMean',	'IVBid',	'IVAsk', 'Delta', 'Gamma',	'Theta', 'Vega', 'AKA']
				### Populate delta flag....
				Delta = False
				if row['Type'] == 'call' and float(row ['Delta']) >= 0.70:
					Delta = True
				elif row['Type'] == 'put' and float(row ['Delta']) >= -0.70:
					Delta = True

				#and abs(float(row ['Delta'])) >= 0.70

				if  (exp_date - data_date).days >= 30 and intrinsicVal > 0 and Delta and (0.10 <= float(row['Ask']) - float(row['Bid']) <= 0.35) and float(row['OpenInterest']) >= 100 and key not in keyList :
					
					
					if os.stat(outputfile).st_size == 0 and header:
						writer = csv.DictWriter(fout, fieldnames=fieldnames)
						writer.writeheader()
						header = False
					else:
						writer = csv.DictWriter(fout, fieldnames=fieldnames)

					writer.writerow(
							{'UnderlyingSymbol': row['UnderlyingSymbol'], 'UnderlyingPrice': row['UnderlyingPrice'], 
							'Flags': row['Flags'],  'OptionSymbol': row['OptionSymbol'], 'Type':row['Type'], 'Expiration': row['Expiration'], 
							'DataDate': row[' DataDate'], 'Strike': row['Strike'], 'Last': row['Last'], 'Bid': row['Bid'], 'Ask': row['Ask'], 
							'Volume': row['Volume'], 'OpenInterest': row['OpenInterest'], 'T1OpenInterest': row['T1OpenInterest'], 'IVMean': row['IVMean'], 
							'IVBid': row['IVBid'], 'IVAsk': row['IVAsk'], 'Delta': row['Delta'], 'Gamma': row['Gamma'], 'Theta': row['Theta'], 
							'Vega': row['Vega'], 'AKA': row['AKA'] }
					)
					keyList.append(key) ### to track specific ticker option has been populated...

'''







		