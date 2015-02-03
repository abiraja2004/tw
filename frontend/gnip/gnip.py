import urllib2
import urllib
import base64
import zlib
from threading import Lock
import json
import sys
import ssl
import time
from pprint import pprint
import gnip_rules
import utils
from utils import MyThread
from pipeline import Pipeline
import pipelinestages
from select import select
import pycurl
from xml.sax import make_parser, parse, parseString
from xml.sax.handler import ContentHandler
from xml.sax.xmlreader import IncrementalParser
from datetime import datetime, timedelta
from mongo import MongoManager


# Tune CHUNKSIZE as needed.  The CHUNKSIZE is the size of compressed data read
# For high volume streams, use large chuck sizes, for low volume streams, decrease
# CHUNKSIZE.  Minimum practical is about 1K.
CHUNKSIZE = 1024
GNIPKEEPALIVE = 30  # seconds
NEWLINE = '\r\n'

err_lock = Lock()

        
class GnipTwitterStreamReceiver(MyThread):
    class procEntry(MyThread):
        def __init__(self, buf, queue):
            self.buf = buf
            self.queue = queue
            MyThread.__init__(self)

        def run(self):
            for rec in [x.strip() for x in self.buf.split(NEWLINE) if x.strip() <> '']:
                try:
                    jrec = json.loads(rec.strip())
                    #tmp = json.dumps(jrec)
                    self.queue.put(jrec)
                except ValueError, e:
                    with err_lock:
                        sys.stderr.write("Error processing JSON: %s (%s)\n"%(str(e), rec))
    
    def __init__(self, url, username, password, queue):
        MyThread.__init__(self)
        self.url = url
        self.username = username
        self.password = password
        self.queue = queue
        self.finish_flag = False
        self.remainder = ''

    def stopWorking(self):
        self.finish_flag = True
    
    def on_receive(self, data):
        #print "data received: ", len(data)
        dd = ''.join([self.remainder, data]).rsplit(NEWLINE,1)
        if len(dd) > 1:
            [records, self.remainder] = dd
            GnipTwitterStreamReceiver.procEntry(records, self.queue).start()
        else:
            self.remainder = dd[0]
        
        if self.finish_flag: return -1
    
    def run(self):
        conn = pycurl.Curl()
        conn.setopt(pycurl.USERPWD, "%s:%s" % (self.username, self.password))
        conn.setopt(pycurl.URL, self.url)
        conn.setopt(pycurl.WRITEFUNCTION, self.on_receive)
        conn.setopt(pycurl.ENCODING, "gzip")
        try:
            conn.perform()    
        except pycurl.error, e:
            pass

        
class GnipTwitterManager(object):
    def __init__(self,accountname, username, password):
        self.accountname = accountname
        self.username = username
        self.password = password
        self.pipeline = Pipeline()
        for plsc in pipelinestages.getPipelineTwitterStageClasses():
            self.pipeline.appendStage(plsc())
        #self.pipeline.appendStage(Pipeline.Stage())
        self.extractor = None
        self.gniprules = gnip_rules.GnipTwitterRules(accountname, username, password)
        
        
    def startWorking(self):
        self.pipeline.startWorking()        
        URL = "https://stream.gnip.com:443/accounts/%s/publishers/twitter/streams/track/prod.json" %(self.accountname)        
        self.extractor = GnipTwitterStreamReceiver(URL, self.username, self.password, self.pipeline.getSourceQueue())        
        self.extractor.start()

    def stopWorking(self):
        if self.extractor: 
            self.extractor.stopWorking()
            self.extractor.join()
            self.extractor = None
        self.pipeline.stopWorking()
    
    
    def getRules(self):
        return self.gniprules.getRules()['rules']

    def addRules(self, rules):
        self.gniprules.initLocalRules()
        for r in rules:
            self.gniprules.appendLocalRule(r['value'], r.get('tag', None))
        self.gniprules.createGnipRules()

    def deleteRules(self, rules):
        self.gniprules.initLocalRules()
        for r in rules:
            self.gniprules.appendLocalRule(r['value'], r.get('tag', None))
        self.gniprules.deleteGnipRules()

    def getStats(self):
        res = {}
        res['Pipeline'] = self.pipeline.getStats()
        return res


class DataCollectionActivityHandler(ContentHandler):
    cached_fanpage_to_campaigns = None
    fanpage_to_campaigns_max_age = timedelta(seconds=10)
    
    entry_basic_tags = ("id","created", "published", "updated", "title")
    entry_composed_tags = {"source/gnip:rule": "rule", "activity:object/link[rel=alternate]": {"activity:link:alternate": "href"}, "activity:object/link[rel=via]": {"activity:link:via": "href"}, "activity:object/activity:object-type": "activity:type", "author/name": "author:name", "author/uri": "author:uri", "activity:object/id": "activity:id", "activity:object/title": "activity:title", "activity:object/content": "activity:content"}
    
    def __init__(self, queue):
        self.entries = []
        self.entry = None
        self.activity = None
        self.tagpath = []
        self.refreshURL = ""
        self.queue = queue
    
    def startElement(self, name, attrs):    
        if name == "results": 
            self.refreshURL = attrs['refreshURL']
            return
        if name == "root": return
        self.tagpath.append(name)
        comp_path = '/'.join(self.tagpath[1:])
        if comp_path == "activity:object/link":
            name = "link[rel=%s]" % attrs['rel']
            self.tagpath[-1] = name
            comp_path = '/'.join(self.tagpath[1:])
        if name == "entry":
            self.entry = {}
        if name == "activity:object":
            self.activity = {}
        elif name in self.entry_basic_tags and len(self.tagpath) >= 2 and self.tagpath[-2] == "entry":
            self.entry[name] = ""
        elif comp_path in self.entry_composed_tags:
            if isinstance(self.entry_composed_tags[comp_path], basestring):
                self.entry[self.entry_composed_tags[comp_path]] = ""
            elif isinstance(self.entry_composed_tags[comp_path], dict):
                self.entry[self.entry_composed_tags[comp_path].keys()[0]] = attrs[self.entry_composed_tags[comp_path].values()[0]]
                
    def characters(self, content):
        if not self.tagpath: return
        comp_path = '/'.join(self.tagpath[1:])
        if self.tagpath[-1] in self.entry_basic_tags and len(self.tagpath) >= 2 and self.tagpath[-2] == "entry":
            self.entry[self.tagpath[-1]] += content
        elif comp_path in self.entry_composed_tags:
            if isinstance(self.entry_composed_tags[comp_path], basestring):
                self.entry[self.entry_composed_tags[comp_path]] += content
            
    def endElement(self, name):
        if name == "results": return
        self.tagpath.pop()
        if name == "entry":
            self.entry['x_created_at'] = datetime.strptime(self.entry['created'], "%Y-%m-%dT%H:%M:%S+00:00")            
            self.entry['campaigns'] = self.__class__.getFanpageToCampaignsDict().get(self.entry.get('rule', ''), [])
            self.queue.put(self.entry)
            self.entry = None


    @classmethod
    def getFanpageToCampaignsDict(cls):
        if not cls.fanpage_to_campaigns_max_age or not cls.cached_fanpage_to_campaigns or (datetime.now() - cls.cached_fanpage_to_campaigns['fetch_time'] > cls.fanpage_to_campaigns_max_age):        
            print "refetching fanpages to campagins dict"
            accounts = MongoManager.getActiveAccounts()
            data = {}
            for acc in accounts:
                for camp in acc.getActiveCampaigns():
                    for fp in camp.getFacebookFanpages():
                        if fp not in data: data[fp] = []
                        data[fp].append(camp)
            cls.cached_fanpage_to_campaigns = {'data': data, 'fetch_time': datetime.now()}
        return cls.cached_fanpage_to_campaigns['data']
            

class GnipDataCollectionStreamReceiver(MyThread):
    
    def __init__(self, url, username, password, queue):
        MyThread.__init__(self)
        self.url = url
        self.username = username
        self.password = password
        self.queue = queue
        self.finish_flag = False
        self.remainder = ''

    def stopWorking(self):
        self.finish_flag = True
    
    def run(self):
        passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
        passman.add_password(None, self.url, self.username, self.password)
        authhandler = urllib2.HTTPBasicAuthHandler(passman)
        opener = urllib2.build_opener(authhandler)
        urllib2.install_opener(opener)
        request = urllib2.urlopen(self.url, None, 1)
        handler = DataCollectionActivityHandler(self.queue)
        parser = make_parser()
        parser.setContentHandler(handler)
        s = ""
        parser.feed("<root>")
        while not self.finish_flag:
            try:
                s = s + request.read(1)
            except ssl.SSLError, e:
                print s,
                parser.feed(s)
                s = ""
                #print "timeout"
                pass #timeout
            except KeyboardInterrupt, e:
                break
        return


class GnipCollectionManager(object):
            
    def __init__(self,accountname, username, password):
        self.accountname = accountname
        self.username = username
        self.password = password
        self.pipeline = Pipeline()
        for plsc in pipelinestages.getPipelineCollectionStageClasses():
            self.pipeline.appendStage(plsc())
        #self.pipeline.appendStage(Pipeline.Stage())
        self.extractor = None
        self.gniprules = gnip_rules.GnipCollectionRules(accountname, username, password)
        
        
    def startWorking(self):
        self.pipeline.startWorking()        
        URL = "https://%s.gnip.com/data_collectors/1/stream.xml" %(self.accountname)
        self.extractor = GnipDataCollectionStreamReceiver(URL, self.username, self.password, self.pipeline.getSourceQueue())        
        self.extractor.start()

    def stopWorking(self):
        if self.extractor: 
            self.extractor.stopWorking()
            self.extractor.join()
            self.extractor = None
        self.pipeline.stopWorking()
    
    
    def getRules(self):
        return self.gniprules.getRules()['rules']

    def addRules(self, rules):
        self.gniprules.initLocalRules()
        for r in rules:
            self.gniprules.appendLocalRule(r['value'], r.get('tag', None))
        self.gniprules.createGnipRules()

    def deleteRules(self, rules):
        self.gniprules.initLocalRules()
        for r in rules:
            self.gniprules.appendLocalRule(r['value'], r.get('tag', None))
        self.gniprules.deleteGnipRules()
        
    def getStats(self):
        res = {}
        res['Pipeline'] = self.pipeline.getStats()
        return res
        

if __name__ == "__main__":
# Note: this automatically reconnects to the stream upon being disconnected
    UN = 'pablobesada'
    PWD = 'pdbpdb'
    ACC = 'promored'
    gcm = GnipCollectionManager(ACC, UN, PWD)    
    gcm.startWorking()
    
    UN = 'federicog@promored.mx'
    PWD = 'ladedarin'
    ACC = 'promored'
    gtm = GnipTwitterManager(ACC, UN, PWD)    
    gtm.startWorking()
    
    try:    
        while True:
            #pprint(gcm.getStats())
            time.sleep(1)
    except KeyboardInterrupt, e:
        print "Terminando.\n"
        gcm.stopWorking()
        gtm.stopWorking()
        pprint(gcm.getStats())
        pprint(gtm.getStats())
        print "Terminado.\n"
        MyThread.checkFinalization()

    sys.exit(0)    
    
