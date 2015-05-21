import sys
 
sys.path.append('/home/parallels/Code/heroku-envbased/roboquant/strategies')
print sys.path

from algotrade import simple_strategy

import datetime
from time import mktime

import redis
import urlparse
import os
from pyalgotrade.feed import memfeed
from pyalgotrade.dataseries.bards import BarDataSeries
from pyalgotrade.bar import BasicBar, Frequency
from pyalgotrade.barfeed import membf



'''
class Feed(membf.BarFeed):
    def __init__(self, frequency, maxLen=1024):
        membf.BarFeed.__init__(self, frequency, maxLen)

    def barsHaveAdjClose(self):
        return True

    def loadBars(self, instrument, bars):
        self.addBarsFromSequence(instrument, bars)




dt = datetime.datetime(2012, 01, 01, 17, 0, 0, 0)
dt2 = datetime.datetime(2012, 12, 31, 17, 0, 0, 0)
seconds = mktime(dt.timetuple())
seconds2 = mktime(dt2.timetuple())

redis_url = os.environ.get('REDISCLOUD_URL', 'redis://localhost:6379')
url = urlparse.urlparse(redis_url)
#print "$$$URL: ", url
redisConn = redis.StrictRedis(host=url.hostname, port=url.port, password=url.password)
redis_data = redisConn.zrangebyscore('AAPL:Adj. Close', int(seconds*1000), int(seconds2*1000), 0, -1, True)
#bdseries = BarDataSeries()
bd = []
for x in range(len(redis_data)):
	v = redis_data[x][0]
	bar = BasicBar(datetime.datetime.fromtimestamp(redis_data[x][1]/1000), 
		  v, v, v, v, 200000, v, Frequency.DAY)
	bd.append(bar)
	#bdseries.append(bar)
feed = Feed(Frequency.DAY, 1024)
feed.loadBars("AAPL", bd)
#feed.addBarsFromSequence("aapl", bdseries)

print feed
print seconds, seconds2
'''

#dt2 = datetime.datetime.fromtimestamp(seconds)

#print seconds, seconds2

#print datetime.date(2006, 01, 01).toordinal()

'''ateDataSeries
values = [(datetime.datetime.now() + datetime.timedelta(seconds=i), {"i": i}) for i in xrange(100)]
print  [(datetime.datetime.now()+datetime.timedelta(seconds=5), 20),]
'''

print simple_strategy.run_strategy_redis("AAPL", 500000)
#	simple_strategy.run_strategy_redis(i)

