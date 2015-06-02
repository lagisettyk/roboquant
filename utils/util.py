### Redis related Utility functions...
import redis
import os
import urlparse

def get_redis_conn(redis_url=os.getenv('REDISCLOUD_URL', 'redis://localhost:6379')):
	url = urlparse.urlparse(redis_url)
	print "$$$URL: ", url
	return redis.StrictRedis(host=url.hostname, port=url.port, password=url.password)
	