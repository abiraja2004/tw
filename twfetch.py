#encoding: utf-8
"""
from twitter import Twitter
twitter = Twitter.getTwitter()
q = twitter.search(q='scioli')
print q['search_metadata']
for t in q['statuses']:
  print t
"""

#import tweetstream
import time
import threading
from twython import TwythonStreamer
from pymongo import MongoClient
from datetime import datetime,  timedelta
from rulesmanager import getBrandClassifiers
import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--auth', action="store_true", default=False)
args = parser.parse_args()
dbuser = "monitor"
dbpasswd = "monitor678"
mclient = MongoClient()
db = mclient['unilever']
if args.auth:
    db.authenticate(dbuser, dbpasswd)
monitor = mclient['monitor']
if args.auth:
    monitor.authenticate(dbuser, dbpasswd)


#db.authenticate("pablo", "1234")

"""
words = ["opera", "firefox", "safari"]
#people = [123,124,125]
locations = ["-122.75,36.8", "-121.75,37.8"]
with tweetstream.FilterStream("pablobesada", "paddle26", track=words, locations=locations) as stream:
  for tweet in stream:
    print "Got interesting tweet:", tweet
""" 
    
def getWordsToTrack():
    accounts = monitor.accounts.find({})
    s = set()
    for acc in accounts:
        for cid, campaign in acc['campaigns'].items():
            for bid, brand in campaign['brands'].items():
                s.add(brand['name'])
                if brand.get('synonyms','').strip():
                    for kw in [kw.strip() for kw in brand['synonyms'].split(",") if kw.strip()]:
                            s.add(kw)    
    return s
    
stream = None

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
        try:
            print "received:", data['text']
        except:
            pass
        self.tweets.append(data)

    def on_error(self, status_code, data):
        print "error:", status_code

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
        global stream
        stream.disconnect()
        self.stop = True
        stream = None
    

class MyThread(threading.Thread):
    keywords = []
    running = False
    
    def run(self):
        MyThread.running = True
        global stream
        stream = TweetStreamer()
        #k = stream.statuses.filter(follow="138814032,31133330,117185027", track=["CFKArgentina", "cristina", "cris", "kirchner", "scioli", "massa"], language="es")
        #kwords = ['unilever', 'dove', 'knorr', 'maizena', 'ala', 'skip', 'lux', 'ades', 'ponds', "pond's", 'rexona', "hellman's", "axe", "cif", "savora", "impulse", "vivere", "suave", "hellen curtis", "lipton" ,"lifebuoy", "drive", "sedal", "comfort", "clear", "vasenol", "vim"] #argentina
        #kwords = ['unilever', "ades", "pond's", "ponds", "st. ives", "ives", "knorr", "dove", "axe", "tresemme", u"tresemmé", "sedal", "hellman's", "cif" , "iberia", "rexona", "maizena", "vo5", "clear", "nexxus", "vasenol", "lipton", "not butter", "ben & jerry's", "jerry's", "slim-fast", "slimfast", "del valle", "jumex", 'veet', 'nair', 'america','sivale','sivalesi','crujitos'] #"holanda (helado)", "primavera (margarina)" #mexico
        if MyThread.keywords:
            k = stream.statuses.filter(track=list(MyThread.keywords), language="es")
        MyThread.running = False
        
#        (follow="138814032", track=["CFKArgentina", "cristina", "cris"])
#(track=['scioli','massa','cfk','solanas','@cfkargentina','@danielscioli','@SergioMassa'])

class KeywordMonitor(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.stop = False

    def run(self):
        t = datetime.now() - timedelta(hours=99)
        keywords = None
        while not self.stop:
            if datetime.now()-t > timedelta(seconds=120):
                print "checking keywords..."
                t = datetime.now()
                k2 = getWordsToTrack()
                if k2 != keywords:
                    print "keyword changes found... restarting fetcher"
                    if stream: stream.finish()
                    while MyThread.running: time.sleep(1)
                    keywords = k2
                    MyThread.keywords = keywords
                    MyThread().start()
                    print "Tracking:", keywords
                time.sleep(1)
            else:
                time.sleep(30)

    def finish(self):
        print "finishing keyword monitor thread..."      
        self.stop = True
        
        
try:
    bcs = getBrandClassifiers()
    kwmonitor = KeywordMonitor()
    kwmonitor.start()
    while True:
        while not stream: time.sleep(0.2)                     
        for t in stream:
            t['x_process_version'] = 2
            t['x_created_at'] = datetime.strptime(t['created_at'], "%a %b %d %H:%M:%S +0000 %Y")
            pms = []
            for bc in bcs:
                pms.extend([pm.getDictionary() for pm in bc.extract(t['text'])])
            if pms:
                pms.sort(key=lambda x: x['confidence'], reverse=True)
                t['x_extracted_info'] = pms
                print "INSERTING!!!!"
                print db.tweets.insert(t)
            print            
            
            try:
                print t["text"], t['x_created_at']
            except:
                pass

      
except KeyboardInterrupt, e:
    pass
except Exception, e:
    print e
    if kwmonitor: kwmonitor.finish()    
    if stream: stream.finish()
    raise
    pass

if kwmonitor: kwmonitor.finish()    
if stream: stream.finish()

