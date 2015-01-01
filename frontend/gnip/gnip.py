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

# Tune CHUNKSIZE as needed.  The CHUNKSIZE is the size of compressed data read
# For high volume streams, use large chuck sizes, for low volume streams, decrease
# CHUNKSIZE.  Minimum practical is about 1K.
CHUNKSIZE = 1024
GNIPKEEPALIVE = 30  # seconds
NEWLINE = '\r\n'

err_lock = Lock()

        
class GnipStreamReceiver(MyThread):
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
            GnipStreamReceiver.procEntry(records, self.queue).start()
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
        
    def run2(self):
        print "en el run"
        HEADERS = { 'Accept': 'application/json',
                'Connection': 'Keep-Alive',
                'Accept-Encoding' : 'gzip',
                'Authorization' : 'Basic %s' % base64.encodestring('%s:%s' % (self.username, self.password))  }
        
        print "antes del request"
        req = urllib2.Request(self.url, headers=HEADERS)
        print "antes del urlopen"
        response = urllib2.urlopen(req, timeout=(1+GNIPKEEPALIVE))
        print "antes del decompressobj"
        # header -  print response.info()
        decompressor = zlib.decompressobj(16+zlib.MAX_WBITS)
        remainder = ''
        print "antes del while"
        while not self.finish_flag:
            print "antes del read"
            chunk = response.read(CHUNKSIZE)
            print "chunk: ", len(chunk)
            tmp = decompressor.decompress(chunk)
            if tmp == '':
                print "tmp == '', saliendo !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
                print
                print
                #return
            else:
                dd = ''.join([remainder, tmp]).rsplit(NEWLINE,1)
                if len(dd) > 1:
                    [records, remainder] = dd
                    #print "records: %s, remainder %s" % (len(records), len(remainder))
                    GnipStreamReceiver.procEntry(records, self.queue).start()
                else:
                    remainder = dd[0]
                    #print "remainder: %s" % len(remainder)
        
        """
        req = urllib2.Request(self.url, headers=HEADERS)
        response = urllib2.urlopen(req, timeout=(1+GNIPKEEPALIVE))
        # header -  print response.info()
        decompressor = zlib.decompressobj(16+zlib.MAX_WBITS)
        remainder = ''
        chunk = ''
        while not self.finish_flag:
            while not self.finish_flag:
                try:
                    c = response.read(1)
                    chunk += c
                    print len(chunk), 
                    pprint(chunk)
                    if not c or len(chunk) >= CHUNKSIZE: break                    
                except Exception ,e:
                    print e
            if chunk and len(chunk) >= CHUNKSIZE:
                print 
                tmp = decompressor.decompress(chunk)
                print "chunk length: %s,  tmp: %s, unconsumed: %s" % (len(chunk), len(tmp), len(decompressor.unconsumed_tail))
                chunk = ''
                if tmp != '':
                    dd = ''.join([remainder, tmp]).rsplit(NEWLINE,1)
                    if len(dd) > 1:
                        [records, remainder] = dd
                        print "records: %s, remainder %s" % (len(records), len(remainder))
                        GnipStreamReceiver.procEntry(records, self.queue).start()
                    else:
                        remainder = dd[0]
                        print "remainder: %s" % len(remainder)
                else:
                    print "tmp == ''"
        """
                    
        
        
class GnipManager(object):
    def __init__(self,accountname, username, password):
        self.accountname = accountname
        self.username = username
        self.password = password
        self.pipeline = Pipeline()
        for plsc in pipelinestages.getPipelineStageClasses():
            self.pipeline.appendStage(plsc())
        #self.pipeline.appendStage(Pipeline.Stage())
        self.extractor = None
        self.gniprules = gnip_rules.GnipRules(accountname, username, password)
        
        
    def startWorking(self):
        self.pipeline.startWorking()        
        URL = "https://stream.gnip.com:443/accounts/%s/publishers/twitter/streams/track/prod.json" %(self.accountname)        
        self.extractor = GnipStreamReceiver(URL, self.username, self.password, self.pipeline.getSourceQueue())        
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
    
    UN = 'federicog@promored.mx'
    PWD = 'ladedarin'
    ACC = 'promored'
    gm = GnipManager(ACC, UN, PWD)    
    gm.startWorking()
    try:    
        while True:
            #pprint.pprint(gm.getStats())
            time.sleep(1)
    except KeyboardInterrupt, e:
        print "Terminando.\n"
        gm.stopWorking()
        pprint(gm.getStats())
        print "Terminado.\n"
        MyThread.checkFinalization()

    sys.exit(0)
