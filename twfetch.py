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
    while True:
        while not stream: 
            time.sleep(0.2)                     
        for t in stream:
            t['x_process_version'] = 2
            t['x_created_at'] = datetime.strptime(t['created_at'], "%a %b %d %H:%M:%S +0000 %Y")
            pms = {}
            for bc in bcs:
                if not bc.campaign_id in pms: pms[bc.campaign_id] = []
                pms[bc.campaign_id].extend([pm.getDictionary() for pm in bc.extract(t['text'])])
            x_mentions_count = {}
            #campaign_ids = set()                            
            poll_ids = set()
            for m in t['entities']['user_mentions']:
                if ("@" + m["screen_name"]) in MyThread.accountsToTrack: 
                    x_mentions_count["@" + m['screen_name']] = 1
                    #campaign_ids.add(MyThread.accountsToTrack["@" + m['screen_name']]['cid'])
                    pm = ProductMatch()
                    pm.brand = MyThread.accountsToTrack["@" + m['screen_name']]['brand']
                    pm.campaign_id = MyThread.accountsToTrack["@" + m['screen_name']]['cid']
                    pm.confidence = 5
                    pms[pm.campaign_id].append(pm.getDictionary())
                    
            for m in t['entities']['hashtags']:
                if ("#" + m["text"]) in MyThread.hashtagsToTrack: 
                    for d in MyThread.hashtagsToTrack["#" + m['text']]:
                        poll_ids.add(d['pid'])
                    
            if 'user' in t and 'id_str' in t['user']:
                if t['user']['id_str'] in MyThread.accountsToTrackIds:
                    #campaign_ids.add(MyThread.accountsToTrackIds[t['user']['id_str']]['cid'])
                    pm = ProductMatch()
                    pm.brand = MyThread.accountsToTrackIds[t['user']['id_str']]['brand']
                    pm.campaign_id = MyThread.accountsToTrackIds[t['user']['id_str']]['cid']
                    pm.confidence = 5
                    pms[pm.campaign_id].append(pm.getDictionary())
                    if MyThread.accountsToTrackIds[t['user']['id_str']]['own_brand']:
                        t['x_sentiment'] = '='
                    
            #if pms or x_mentions_count or campaign_ids or poll_ids:
            if pms or x_mentions_count or poll_ids:
                t['x_mentions_count'] = x_mentions_count
                
                """ por el momento topics globales desactivados
                tms = []
                for tc in tcs:
                    tm = tc.extract(t['text'])
                    if tm: tms.append(tm.getDictionary())

                print "mentions count: " + str(x_mentions_count)
                if tms: tms.sort(key=lambda x: x['confidence'], reverse=True)
                t['x_extracted_topics'] = tms
                """ #topics globales desactivados
                
                #for cids in pms:
                #    campaign_ids.add(cids)
                #for cid in campaign_ids:
                for cid in pms.keys():
                    extracted_infos = pms.get(cid, [])
                    if extracted_infos:
                        extracted_infos.sort(key=lambda x: x['confidence'], reverse=True)
                        if extracted_infos[0]['confidence'] > 0:
                            t['x_extracted_info'] = extracted_infos
                            
                            #una vez que ya se que voy a guardar el tweet en una campanna le aplico los x_extracted_topics
                            tms = []
                            for topic_id, topic_classiffier in tcs.get(cid, {}).items():
                                tm = topic_classiffier.extract(t['text'])
                                if tm: tms.append(tm.getDictionary())
                            if tms: tms.sort(key=lambda x: x['confidence'], reverse=True)
                            t['x_extracted_topics'] = tms                            
                            
                            collection_name = "tweets_%s" % cid                    
                            print "INSERTING into %s" % collection_name
                            print monitor[collection_name].insert(t)
                for pid in poll_ids:
                    collection_name = "polls_%s" % pid                    
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
    if kwmonitor: kwmonitor.finish()    
    if stream: stream.finish()
    raise
    pass

if kwmonitor: kwmonitor.finish()    
if stream: stream.finish()

