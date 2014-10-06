#encoding: utf-8
import urllib2

from xml.sax import make_parser, parse, parseString
from xml.sax.handler import ContentHandler
from xml.sax.xmlreader import IncrementalParser
import codecs
from pymongo import MongoClient, DESCENDING
from datetime import datetime
import ssl

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--auth', action="store_true", default=False)
args = parser.parse_args()
dbuser = "monitor"
dbpasswd = "monitor678"
mclient = MongoClient()

SERVER_LOCAL=0
SERVER_REMOTE=1

server_mode = SERVER_LOCAL
    
accountdb = mclient['monitor']
if args.auth:
    accountdb.authenticate(dbuser, dbpasswd)
    server_mode = SERVER_REMOTE
    server_domain = "www.nuev9.com"


collection = "fb_posts_5410f5a52e61d7162c700232" #campaña sivale
user = "pablobesada"
password = "pdbpdb"
    
class ActivityHandler(ContentHandler):
    entry_basic_tags = ("id","created", "published", "updated", "title")
    entry_composed_tags = {"source/gnip:rule": "rule", "activity:object/link[rel=alternate]": {"activity:link:alternate": "href"}, "activity:object/link[rel=via]": {"activity:link:via": "href"}, "activity:object/activity:object-type": "activity:type", "author/name": "author:name", "author/uri": "author:uri", "activity:object/id": "activity:id", "activity:object/title": "activity:title", "activity:object/content": "activity:content"}
    
    def __init__(self):
        self.entries = []
        self.entry = None
        self.activity = None
        self.tagpath = []
        self.refreshURL = ""
    
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
            if server_mode == SERVER_LOCAL or self.entry['rule'] == "sivalemx": #REVISAR!
                accountdb[collection].save(self.entry)
            self.entries.append(self.entry)
            self.entry = None
            

def poll(url=None):
    if not url: url = "https://promored.gnip.com/data_collectors/1/activities.xml"
    #url = "https://promored.gnip.com/data_collectors/1/activities.xml?since_date=20141005155726"
    #url = "https://promored.gnip.com/data_collectors/1/activities.xml?since_date=20141005223644"
    #url = "https://promored.gnip.com/data_collectors/1/activities.xml?since_date=20141005223737"
    passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
    passman.add_password(None, url, user, password)
    authhandler = urllib2.HTTPBasicAuthHandler(passman)
    opener = urllib2.build_opener(authhandler)
    urllib2.install_opener(opener)
    page = urllib2.urlopen(url)
    #page = open("sivale.xml", "rb") #.write(page.read())
    handler = ActivityHandler()
    #print page.read()
    s = page.read()
    #print s
    parseString(s, handler)
    return len(handler.entries), handler.refreshURL 

def pollAll():
    print accountdb[collection].drop()
    n = 1
    refreshURL = None
    while n > 0:
        print refreshURL,
        n, refreshURL = poll(refreshURL)
        print n


def stream():
    url = "https://promored.gnip.com/data_collectors/1/stream.xml"
    passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
    passman.add_password(None, url, user, password)
    authhandler = urllib2.HTTPBasicAuthHandler(passman)
    opener = urllib2.build_opener(authhandler)
    urllib2.install_opener(opener)
    request = urllib2.urlopen(url, None, 1)
    #page = open("sivale.xml", "rb") #.write(page.read())
    handler = ActivityHandler()
    parser = make_parser()
    parser.setContentHandler(handler)
    #print request
    s = ""
    parser.feed("<root>")
    while True:
        try:
            s = s + request.read(1)
        except ssl.SSLError, e:
            #print s,
            parser.feed(s)
            s = ""
            #print "timeout"
            pass #timeout
        except KeyboardInterrupt, e:
            break
    return
    

if __name__ == "__main__":
    pollAll()
    stream()
    pass