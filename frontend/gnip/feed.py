#encoding: utf-8

import feedparser
from pprint import pprint
import time
from datetime import timedelta, datetime
import HTMLParser
from utils import MyThread
from pipeline import Pipeline
import pipelinestages
from mongo import MongoManager


htmlparser = HTMLParser.HTMLParser()


class FeedPost(dict):
    pass
    
    
class FeedEntry(object):

    @classmethod
    def fromFeedParserEntry(cls, link, entry):
        fe = cls()
        fe.d['link'] = link
        fe.d['title'] =  entry.title    
        fe.d['text'] = htmlparser.unescape(entry.summary) #siempre hay que unescapear?? atom? rss? plain/text?
        fe.d['x_created_at'] = datetime.fromtimestamp(time.mktime(entry.published_parsed))
        fe.d['author'] = entry.author
        fe.d['_id'] = entry.id
        fe.d['reply_to_id'] = entry.get('thr_in-reply-to', None)
        return fe

    @classmethod
    def createFromMongoDoc(cls, doc):
        fe = cls()
        fe.d = doc
        return fe        

    def __unicode__(self):
        return u"%s: %s" % (self.getUsername(), self.getText())
        
    def __repr__(self):
        return ("%s: %s" % (self.getUsername(), self.getText())).encode("utf-8")
        
    def __init__(self):
        self.d = {}

    def getId(self):
        return self.d['_id']
    
    def getText(self):
        return self.d['text']

    def getUsername(self):
        return self.d['author']
    
    
    def getExtractedInfo(self):
        return self.d.get('x_extracted_info', [])

    def setExtractedInfo(self, pms):
        self.d['x_extracted_info'] = pms
    
    def getExtractedTopics(self):
        return self.d.get('x_extracted_topics', [])    
    
    def setExtractedTopics(self, tms):
        self.d['x_extracted_topics'] = tms

    def getCreatedDate(self):
        return self.d['x_created_at']

    def getSentiment(self):
        return self.d.get("x_sentiment", '')
    
    def setSentiment(self, s):
        self.d['x_sentiment'] = s

    def getMatchedCampaignIds(self):
        return [self.d.get('x_extracted_info', []).keys()]
        
    def getDictionary(self):
        return self.d

class FeedFetcher(MyThread):
    
    def __init__(self, account, campaign, url, queue):
        MyThread.__init__(self)
        self.account = account
        self.campaign = campaign
        self.url = url
        self.finish_flag = False
        self.queue = queue

    def stopWorking(self):
        self.finish_flag = True
        
    def run(self):
        
        while not self.finish_flag:
            print "fetching feeds from %s" % self.url
            d = feedparser.parse(self.url)
            #print "finished connecting to %s: %s, %s" % (self.url, d.bozo, len(d.entries))
            if d.bozo != 0: #hubo algun error reintentamos
                d = feedparser.parse(self.url)            
                
            if d.version.upper() == "RSS20":
                upd_freq = int(d.feed.sy_updatefrequency)
                upd_period = {'hourly': timedelta(hours=upd_freq), 'daily': timedelta(days=upd_freq), 'weekly': timedelta(weeks=upd_freq), 'yearly': timedelta(weeks=54*upd_freq)}[d.feed.sy_updateperiod]
                last_upd = datetime.fromtimestamp(time.mktime(d.feed.updated_parsed))
                if (last_upd >= datetime.now() - upd_period):
                    next_check = last_upd + upd_period + timedelta(seconds=10)
                else:
                    next_check = datetime.now() + upd_period
            else:
                upd_period = timedelta(hours=1)
                next_check = datetime.now() + upd_period

            if d.bozo == 0: self.processFeed(d)
            while not self.finish_flag and datetime.now() < next_check: 
                time.sleep(1)
            next_check = datetime.now() + upd_period
            
    def processFeed(self, feeds):
        for entry in feeds.entries:
            fe = FeedEntry.fromFeedParserEntry(feeds.feed.link, entry)
            fe.account = self.account
            fe.campaign = self.campaign
            self.queue.put(fe)


class FeedManager(object):
    
    def __init__(self):
        self.pipeline = Pipeline()
        for plsc in pipelinestages.getPipelineFeedStageClasses():
            self.pipeline.appendStage(plsc())

    def startWorking(self):
        self.pipeline.startWorking()        
        self.extractors = []
        for acc, camp, url in self.getAllFeedURLs():
            url += "/comments/feed"
            extractor = FeedFetcher(acc, camp, url,self.pipeline.getSourceQueue())        
            extractor.start()
            self.extractors.append(extractor)

    def stopWorking(self):
        if self.extractors: 
            for extractor in self.extractors:
                extractor.stopWorking()
            while self.extractors:
                for extractor in self.extractors:
                    extractor.join(1)
                    if not extractor.isAlive():
                        self.extractors.remove(extractor)
        self.pipeline.stopWorking()

    def getStats(self):
        res = {}
        res['Pipeline'] = self.pipeline.getStats()
        return res
    
            
    def getAllFeedURLs(self):
        res = []
        accs = MongoManager.getActiveAccounts()
        for acc in accs:
            for camp in acc.getActiveCampaigns():
                for url in camp.getForums():
                    res.append((acc, camp, url))
        return res

if __name__ == "__main__":
    #f = FeedFetcher('http://blogdeunaembarazada.com/comments/feed') #'http://www.mamitips.com.pe/comments/feed/')
    #f.start()
    fm = FeedManager()
    fm.startWorking()
    
    try:    
        while True:
            #pprint(fm.getStats())
            time.sleep(1)
    except KeyboardInterrupt, e:
        print "Terminando.\n"
        fm.stopWorking()
        print "Terminado.\n"
        MyThread.checkFinalization()
    
    