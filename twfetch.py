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
from twython import TwythonStreamer, Twython
from pymongo import MongoClient
from datetime import datetime,  timedelta
from frontend.rulesmanager import getBrandClassifiers, getTopicClassifiers, getAccountsToTrack
import argparse
from frontend.brandclassifier import ProductMatch
import traceback
from frontend.gnip.pipeline import Pipeline
from frontend.gnip import pipelinestages

parser = argparse.ArgumentParser()
parser.add_argument('--auth', action="store_true", default=False)
parser.add_argument('--host', default='')
args = parser.parse_args()
dbuser = "monitor"
dbpasswd = "monitor678"
if args.host:
    mclient = MongoClient(args.host)
else:
    mclient = MongoClient()

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
            if not 'active' in campaign or not campaign['active']: continue
            for bid, brand in campaign['brands'].items():
                s.add(brand['name'])
                if brand.get('synonyms','').strip():
                    for kw in [kw.strip() for kw in brand['synonyms'].split(",") if kw.strip()]:
                            s.add(kw)     
    return s

stream = None

def getHashtagsToTrack():
    accounts = monitor.accounts.find({})
    s = dict()
    for acc in accounts:
        if not 'polls' in acc: continue
        for pid, poll in acc['polls'].items():
            hts = set()
            if poll.get('poll_hashtag', ''): 
                hts.add(poll['poll_hashtag'].strip())
            else:
                for ht in [ht.strip() for ht in poll['hashtags'].split(",") if ht.strip()]:
                    hts.add(ht)
            for ht in hts:
                if ht not in s: s[ht] = []
                s[ht].append({"aid": str(acc['_id']), "pid": pid})
    return s

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
        print "stream created %s" % id(self)

    
    def on_success(self, data):
        try:
            print "received:", data['text'], id(self)
        except:
            pass
        self.tweets.append(data)

    def on_error(self, status_code, data):
        try:
            print "error:", status_code, data
        except:
            pass

        # Want to stop trying to get data because of the error?
        # Uncomment the next line!
        # self.disconnect()

    def __iter__(self):
        return self
      
    def next(self):
        print "en next"
        while not self.tweets: 
            if self.stop: raise StopIteration
            print "%s, waiting... %s" % (datetime.now(), id(self))
            time.sleep(0.5)
        t = self.tweets.pop(0)
        return t

    def finish(self):
        print "finishing streamer thread... %s" % id(self)
        global stream
        print "current stream: %s" % id(stream)
        self.disconnect()
        self.stop = True        
        stream = None
        print "Streamer thread finished"  
    

class MyThread(threading.Thread):
    keywords = []
    accountsToTrack = []
    accountsToTrackIds = []
    hashtagsToTrack = []
    running = False
    
    def run(self):
        MyThread.running = True
        global stream
        stream = TweetStreamer()
        #k = stream.statuses.filter(follow="138814032,31133330,117185027", track=["CFKArgentina", "cristina", "cris", "kirchner", "scioli", "massa"], language="es")
        #kwords = ['unilever', 'dove', 'knorr', 'maizena', 'ala', 'skip', 'lux', 'ades', 'ponds', "pond's", 'rexona', "hellman's", "axe", "cif", "savora", "impulse", "vivere", "suave", "hellen curtis", "lipton" ,"lifebuoy", "drive", "sedal", "comfort", "clear", "vasenol", "vim"] #argentina
        #kwords = ['unilever', "ades", "pond's", "ponds", "st. ives", "ives", "knorr", "dove", "axe", "tresemme", u"tresemmé", "sedal", "hellman's", "cif" , "iberia", "rexona", "maizena", "vo5", "clear", "nexxus", "vasenol", "lipton", "not butter", "ben & jerry's", "jerry's", "slim-fast", "slimfast", "del valle", "jumex", 'veet', 'nair', 'america','sivale','sivalesi','crujitos'] #"holanda (helado)", "primavera (margarina)" #mexico
        if MyThread.keywords or MyThread.accountsToTrack or MyThread.accountsToTrackIds or MyThread.hashtagsToTrack:
            k = stream.statuses.filter(follow=list(MyThread.accountsToTrackIds), track=list(MyThread.keywords) + list(MyThread.accountsToTrack) + list(MyThread.hashtagsToTrack), language="es")
        MyThread.running = False
        
#        (follow="138814032", track=["CFKArgentina", "cristina", "cris"])
#(track=['scioli','massa','cfk','solanas','@cfkargentina','@danielscioli','@SergioMassa'])

bcs = None
tcs = None

class KeywordMonitor(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.stop = False

    def run(self):
        global bcs
        global tcs
        global stream
        t = datetime.now() - timedelta(hours=99)
        keywords = None
        accountsToTrack = None
        hashtagsToTrack = None
        checking_interval=6 #seconds
        while not self.stop:
            if datetime.now()-t > timedelta(seconds=checking_interval):
                print "checking keywords and accounts to track..."
                t = datetime.now()
                k2 = getWordsToTrack()
                a2, i2 = getAccountsToTrack()
                h2 = getHashtagsToTrack()
                bcs = getBrandClassifiers()
                tcs2 = getTopicClassifiers()
                if k2 != keywords or a2 != accountsToTrack or i2 != accountsToTrackIds or h2 != hashtagsToTrack or not (tcs2 == tcs):
                    print "keyword or account changes found... restarting fetcher"
                    print (tcs2 == tcs)
                    if stream: stream.finish()
                    while MyThread.running: time.sleep(1)
                    keywords = k2
                    accountsToTrack = a2
                    accountsToTrackIds = i2
                    hashtagsToTrack = h2
                    tcs = tcs2
                    MyThread.keywords = keywords
                    MyThread.accountsToTrack = accountsToTrack
                    MyThread.accountsToTrackIds = accountsToTrackIds
                    MyThread.hashtagsToTrack = hashtagsToTrack
                    MyThread().start()
                    try:
                        print "Tracking:", keywords
                        print "Accounts: ", accountsToTrack                        
                        print "Hashtags: ", hashtagsToTrack
                        open("tracking_words.txt", "wb").write(str(keywords))
                        open("tracking_accounts.txt", "wb").write(str(accountsToTrack))
                        open("tracking_hashtags.txt", "wb").write(str(hashtagsToTrack))
                    except:
                        pass
                time.sleep(1)
            else:
                time.sleep(checking_interval/2)

    def finish(self):
        print "finishing keyword monitor thread..."      
        self.stop = True
        
        
try:

    #t = Twython("1qxRMuTzu2I7BP7ozekfRw", "whQFHN8rqR78L6su6U32G6TPT7e7W2vCouR4inMfM", "2305874377-TTmvLjLuP8aq8q2bT7GPJsOjG9n6uYLAA0tvsYU", "iy4SYpkHK26Zyfr9RhYSGOLVtd9eMNF6Ebl2p552gF4vL")    
    #user_id = t.lookup_user(screen_name='pablobesada')[0]['id_str']
    #print user_id
    #exit(0)
    bcs = getBrandClassifiers()
    tcs = getTopicClassifiers()
    kwmonitor = KeywordMonitor()
    kwmonitor.start()
    pipeline = Pipeline()
    for plsc in pipelinestages.getPipelineTwitterStageClasses():
        pipeline.appendStage(plsc())
    pipeline.startWorking()
    while True:
        while not stream: 
            time.sleep(0.2)                     
        for t in stream:
            pipeline.getSourceQueue().put(t)



      
except KeyboardInterrupt, e:
    pass
except Exception, e:
    print traceback.format_exc()
    if kwmonitor: kwmonitor.finish()    
    if stream: stream.finish()
    raise
    pass

if kwmonitor: kwmonitor.finish()    
if stream: stream.finish()
pipeline.stopWorking()

