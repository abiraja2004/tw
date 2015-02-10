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
        fe.d['x_feed_type'] = 'forum'
        return fe

    @classmethod
    def createFromMongoDoc(cls, doc):
        fe = cls()
        fe.d = doc
        fe.d['user'] = {'screen_name': fe.getUsername()}
        if not 'x_feed_type' in fe.d:
            fe.d['x_feed_type'] = 'forum'
        return fe        

    def __unicode__(self):
        return u"%s: %s" % (self.getUsername(), self.getText())
        
    def __repr__(self):
        return ("%s\n%s: %s" % (self.getCreatedDate(), self.getUsername(), self.getText())).encode("utf-8")
        
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

    def getFeed(self, url):
        print "fetching feeds from %s" % url
        d = feedparser.parse(url)
        #print "finished connecting to %s: %s, %s" % (self.url, d.bozo, len(d.entries))
        if not d.feed: #hubo algun error reintentamos
            print d.bozo_exception
            print d.bozo_exception.__class__
            d = feedparser.parse(url)            
        if not d.feed: return None
        return d
        
    def run(self):        
        while not self.finish_flag:
            d = self.getFeed(self.url)
            if not d: break
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
            self.processFeed(d)
            while not self.finish_flag and datetime.now() < next_check: 
                time.sleep(1)
            next_check = datetime.now() + upd_period
            
    def processFeed(self, feeds):
        for entry in feeds.entries:
            fe = FeedEntry.fromFeedParserEntry(feeds.feed.link, entry)
            fe.account = self.account
            fe.campaign = self.campaign
            self.queue.put(fe)

class HistoryFeedFetcher(MyThread):
    
    def __init__(self, account, campaign, url, queue):
        MyThread.__init__(self)
        self.account = account
        self.campaign = campaign
        self.url = url
        if self.url.endswith("/"): self.url = self.url[:-1]
        self.finish_flag = False
        self.queue = queue

    def stopWorking(self):
        self.finish_flag = True
        
    def getFeed(self, url):
        print "fetching history feeds from %s" % url
        d = feedparser.parse(url)
        #print "finished connecting to %s: %s, %s" % (self.url, d.bozo, len(d.entries))
        if not d.feed: #hubo algun error reintentamos
            print d.bozo_exception
            print d.bozo_exception.__class__
            d = feedparser.parse(url)            
        if not d.feed: return None
        return d
        
    def findFirstMonth(self):
        y = 2000
        
        while not self.finish_flag and datetime.now().year >= y:
            feed = self.getFeed(self.url + "/%s/feed" % y)
            if not feed: return None
            if feed.entries:
                m = 1
                while not self.finish_flag:
                    feed = self.getFeed(self.url + "/%s/%s/feed" % (y,m))
                    if not feed: return None
                    if feed.entries:
                        return y,m
                    else:
                        m += 1
            else:
                y += 1
        return None, None
    
    def run(self):
        year, month = self.findFirstMonth()
        #year = 2015
        #month = 2
        if not year or not month: return
        d = datetime(year, month, 1)
        while not self.finish_flag and d <= datetime.now():
           
            feed = self.getFeed(self.url + "/%s/%s/%s/feed" % (d.year, d.month, d.day))
            for entry in feed.entries:
                if self.finish_flag: break
                if entry.slash_comments > 0:
                    comments_feed = self.getFeed(entry.wfw_commentrss)
                    if comments_feed:
                        for comment_entry in comments_feed.entries:
                            fe = FeedEntry.fromFeedParserEntry(comments_feed.feed.link, comment_entry)
                            fe.account = self.account
                            fe.campaign = self.campaign
                            self.queue.put(fe)
                            
               
            d = d + timedelta(days=1)
            if d.day == 1: #cambio el mes, me fijo que si posts en el nuevo mes
                while not self.finish_flag and datetime.now():
                    dummy_feed = self.getFeed(self.url + "/%s/%s/feed" % (d.year, d.month))
                    if dummy_feed.entries: 
                        break
                    d = (d + timedelta(days=32)).replace(day=1)  #agrego 1 mes
        
        if d > datetime.now():    
            acc = MongoManager.getAccount(id=self.account.getId())
            camp = acc.getCampaign(id =self.campaign.getId())
            camp.addHistoryFetchedForum(self.url)
            MongoManager.saveCampaign(acc, camp)
           
           
           
        
class FeedManager(object):
    
    def __init__(self):
        self.pipeline = Pipeline()
        self.history_pipeline = Pipeline()
        for plsc in pipelinestages.getPipelineFeedStageClasses():
            self.pipeline.appendStage(plsc())
        for plsc in pipelinestages.getPipelineHistoryFeedStageClasses():
            self.history_pipeline.appendStage(plsc())

    def startWorking(self):
        self.extractors = []
        self.history_extractors = []
        for acc, camp, url in self.getAllHistoryFeedURLs():
            extractor = HistoryFeedFetcher(acc, camp, url,self.history_pipeline.getSourceQueue())        
            extractor.start()
            self.extractors.append(extractor)
        if self.history_extractors: self.history_pipeline.startWorking()
        
        for acc, camp, url in self.getAllFeedURLs():
            url += "/comments/feed"
            extractor = FeedFetcher(acc, camp, url,self.pipeline.getSourceQueue())        
            extractor.start()
            self.extractors.append(extractor)
        if self.extractors: self.pipeline.startWorking()            

    def stopWorking(self):
        if self.extractors: 
            for extractor in self.extractors:
                extractor.stopWorking()
        if self.history_extractors: 
            for extractor in self.history_extractors:
                extractor.stopWorking()
        while self.extractors or self.history_extractors:
            for extractor in self.extractors:
                extractor.join(1)
                if not extractor.isAlive():
                    self.extractors.remove(extractor)
            for extractor in self.history_extractors:
                extractor.join(1)
                if not extractor.isAlive():
                    self.history_extractors.remove(extractor)
                        
        self.pipeline.stopWorking()
        self.history_pipeline.stopWorking()

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

    def getAllHistoryFeedURLs(self):
        res = []
        accs = MongoManager.getActiveAccounts()
        for acc in accs:
            for camp in acc.getActiveCampaigns():
                hff = camp.getHistoryFetchedForums()
                for url in camp.getForums():
                    if url not in hff:
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
    
    