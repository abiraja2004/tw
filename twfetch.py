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
from frontend.rulesmanager import getBrandClassifiers, getTopicClassifiers
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

def getAccountsToTrack():
    accounts = monitor.accounts.find({})
    s = dict()
    for acc in accounts:
        for cid, campaign in acc['campaigns'].items():
            for bid, brand in campaign['brands'].items():
                if brand.get('follow_accounts','').strip():
                    for kw in [kw.strip() for kw in brand['follow_accounts'].split(",") if kw.strip()]:
                            s[kw] = cid
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
            print "%s, waiting..." % (datetime.now())
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
    accountsToTrack = []
    running = False
    
    def run(self):
        MyThread.running = True
        global stream
        stream = TweetStreamer()
        #k = stream.statuses.filter(follow="138814032,31133330,117185027", track=["CFKArgentina", "cristina", "cris", "kirchner", "scioli", "massa"], language="es")
        #kwords = ['unilever', 'dove', 'knorr', 'maizena', 'ala', 'skip', 'lux', 'ades', 'ponds', "pond's", 'rexona', "hellman's", "axe", "cif", "savora", "impulse", "vivere", "suave", "hellen curtis", "lipton" ,"lifebuoy", "drive", "sedal", "comfort", "clear", "vasenol", "vim"] #argentina
        #kwords = ['unilever', "ades", "pond's", "ponds", "st. ives", "ives", "knorr", "dove", "axe", "tresemme", u"tresemmé", "sedal", "hellman's", "cif" , "iberia", "rexona", "maizena", "vo5", "clear", "nexxus", "vasenol", "lipton", "not butter", "ben & jerry's", "jerry's", "slim-fast", "slimfast", "del valle", "jumex", 'veet', 'nair', 'america','sivale','sivalesi','crujitos'] #"holanda (helado)", "primavera (margarina)" #mexico
        if MyThread.keywords or MyThread.accountsToTrack:
            k = stream.statuses.filter(track=list(MyThread.keywords) + list(MyThread.accountsToTrack), language="es")
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
        t = datetime.now() - timedelta(hours=99)
        keywords = None
        accountsToTrack = None
        while not self.stop:
            if datetime.now()-t > timedelta(seconds=60):
                print "checking keywords and accounts to track..."
                t = datetime.now()
                k2 = getWordsToTrack()
                a2 = getAccountsToTrack()
                bcs = getBrandClassifiers()
                tcs = getTopicClassifiers()
                if k2 != keywords or a2 != accountsToTrack:
                    print "keyword or account changes found... restarting fetcher"
                    if stream: stream.finish()
                    while MyThread.running: time.sleep(1)
                    keywords = k2
                    accountsToTrack = a2
                    MyThread.keywords = keywords
                    MyThread.accountsToTrack = accountsToTrack
                    MyThread().start()
                    try:
                        print "Tracking:", keywords
                        print "Accounts: ", accountsToTrack                        
                        open("tracking_words.txt", "wb").write(str(keywords))
                        open("tracking_accounts.txt", "wb").write(str(accountsToTrack))
                    except:
                        pass
                time.sleep(1)
            else:
                time.sleep(30)

    def finish(self):
        print "finishing keyword monitor thread..."      
        self.stop = True
        
        
try:
    bcs = getBrandClassifiers()
    tcs = getTopicClassifiers()
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
            x_mentions_count = {}
            campaign_ids = set()                            
            for m in t['entities']['user_mentions']:
                if ("@" + m["screen_name"]) in MyThread.accountsToTrack: 
                    x_mentions_count["@" + m['screen_name']] = 1
                    campaign_ids.add(MyThread.accountsToTrack["@" + m['screen_name']])
            if pms or x_mentions_count:
                tms = []
                for tc in tcs:
                    tm = tc.extract(t['text'])
                    if tm: tms.append(tm.getDictionary())
                pms.sort(key=lambda x: x['confidence'], reverse=True)
                t['x_extracted_info'] = pms
                t['x_mentions_count'] = x_mentions_count
                if tms: tms.sort(key=lambda x: x['confidence'], reverse=True)
                t['x_extracted_topics'] = tms
                
                for pm in pms:
                    campaign_ids.add(pm['campaign_id'])
                for cid in campaign_ids:
                    collection_name = "tweets_%s" % cid                    
                    print "INSERTING into %s" % collection_name
                    print monitor[collection_name].insert(t)
            print            
            
            try:
                print t["text"], t['x_created_at']
            except:
                pass

      
except KeyboardInterrupt, e:
    pass
except Exception, e:
    print e
    try:
        if kwmonitor: kwmonitor.finish()    
    except:
        pass
    if stream: stream.finish()
    raise
    pass

if kwmonitor: kwmonitor.finish()    
if stream: stream.finish()

