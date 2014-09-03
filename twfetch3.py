"""
from twitter import Twitter
twitter = Twitter.getTwitter()
q = twitter.search(q='scioli')
print q['search_metadata']
for t in q['statuses']:
  print t
"""

import tweetstream
import time
import threading
from twython import TwythonStreamer
from pymongo import MongoClient
#mongoclient = MongoClient()
#db = mongoclient['test']

"""
words = ["opera", "firefox", "safari"]
#people = [123,124,125]
locations = ["-122.75,36.8", "-121.75,37.8"]
with tweetstream.FilterStream("pablobesada", "paddle26", track=words, locations=locations) as stream:
  for tweet in stream:
    print "Got interesting tweet:", tweet
""" 
    
class TweetStreamer(TwythonStreamer):
    TWITTER_ADDRESS = "@TestProdeBr2014"
    CONSUMER_KEY = "1qxRMuTzu2I7BP7ozekfRw"
    CONSUMER_SECRET = "whQFHN8rqR78L6su6U32G6TPT7e7W2vCouR4inMfM"
    ACCESS_TOKEN = "2305874377-TTmvLjLuP8aq8q2bT7GPJsOjG9n6uYLAA0tvsYU"
    ACCESS_KEY = "iy4SYpkHK26Zyfr9RhYSGOLVtd9eMNF6Ebl2p552gF4vL"
  
    
    def __init__(self):
        import threading
	TwythonStreamer.__init__(self, TweetStreamer.CONSUMER_KEY, TweetStreamer.CONSUMER_SECRET, TweetStreamer.ACCESS_TOKEN, TweetStreamer.ACCESS_KEY)
	self.tweets = []
	self.stop = False

	
    def on_success(self, data):
	#print data
	print data
	self.tweets.append(data)

    def on_error(self, status_code, data):
        print "error:", status_code, data

        # Want to stop trying to get data because of the error?
        # Uncomment the next line!
        # self.disconnect()

    def __iter__(self):
	return self
      
    def next(self):
	if self.stop: raise StopIteration
	while not self.tweets: 
	    print "waiting..."
	    time.sleep(0.5)
	t = self.tweets.pop(0)
	return t

    def finish(self):
	print "finishing streamer thread..."      
	stream.disconnect()
	self.stop = True
	
stream = None
class MyThread(threading.Thread):
    def run(self):
	global stream
        stream = TweetStreamer()
        k = stream.statuses.filter(follow="138814032", track=["CFKArgentina", "cristina", "cris"])

try:
  MyThread().start()
  while not stream: time.sleep(0.2)         
  
  for t in stream:
      print t
      #db.tweets.insert(t)
except KeyboardInterrupt, e:
  pass
except Exception, e:
  print e
  pass

if stream: stream.finish()
    
