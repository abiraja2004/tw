#encoding: utf-8
from pymongo import MongoClient
from bson import ObjectId
import argparse
from pprint import pprint
import time
import threading
from datetime import datetime, timedelta
from tweet import Tweet

class Product(object):
    
    def __init__(self, id, mongoproduct):
        self.id = id
        self.o = mongoproduct
        self.keywordsets = None

    def __unicode__(self):
        return u"<Product %s>" % self.getName()
    
    def __repr__(self):
        return self.__unicode__()

    def getName(self):
        return self.o.get('name', "")
    
    def isUsingBrandIdRules(self):
        return self.o.get("use_brand_id_rules", False)
    
    def getSynonyms(self):
        return set([x.strip().lower() for x in self.o.get("synonyms","").split(",") if x.strip()])
                   
    def getSearchKeywords(self):
        s = self.getSynonyms()
        s.add(self.getName().lower())
        return s
    
    def getIdentificationRules(self):
        return self.o.get("identification_rules", [])
    
    def getKeywords(self):
        res = self.o.get('keywords', [])
        return res

    def getKeywordsets(self):
        if self.keywordsets is None:
            self.keywordsets = []
            for kwset in self.o.get('keyword_sets', []):
                self.keyworsets.append(MongoManager.getKeywordset(id=str(kwset['_id'])))        
        return self.keywordsets    

class Brand(object):
    
    def __init__(self, id, mongobrand):
        self.id = id
        self.o = mongobrand
        self.keywordsets = None

    def __unicode__(self):
        return u"<Brand %s>" % self.getName()
    
    def __repr__(self):
        return self.__unicode__()

    def getId(self):
        return self.id
    
    def getName(self):
        return self.o.get('name', "")
    
    def isOwnBrand(self):
        return self.o.get('own_brand', False)
    
    def getProducts(self):
        return [Product(id, prod) for id, prod in self.o.get('products', {}).items()]

    def getSynonyms(self):
        return set([x.strip().lower() for x in self.o.get("synonyms","").split(",") if x.strip()])

    def getSearchKeywords(self):
        s = self.getSynonyms()
        s.add(self.getName().lower())
        return s

    def getFollowAccounts(self):
        return set([x.strip() for x in self.o.get("follow_accounts", "").split(",") if x.strip()])
    
    def getIdentificationRules(self):
        return self.o.get("identification_rules", [])
    
    def getKeywords(self):
        res = self.o.get('keywords', [])
        return res

    def getKeywordsets(self):
        if self.keywordsets is None:
            self.keywordsets = []
            for kwset in self.o.get('keyword_sets', []):
                try:
                    kwset_id = str(kwset.get('_id', ''))
                    if kwset_id:
                        keywordset = MongoManager.getKeywordset(id=kwset_id)
                        keywordset.setValue(kwset['value'])
                        self.keywordsets.append(keywordset)
                except Exception, e:
                    print "MARCA: ",self.getName()
                    raise
        return self.keywordsets
    
class Topic(object):
    
    def __init__(self, id, mongotopic):
        self.id = id
        self.o = mongotopic
        self.keywordsets = None

    def getId(self):
        return self.id
    
    def __unicode__(self):
        return u"<Topic %s>" % self.getName()
    
    def __repr__(self):
        return self.__unicode__().encode("latin1")

    def getName(self):
        return self.o.get('name', "")

    def getOwnKeywordsetIds(self):
        return [str(k['_id']) for k in self.o.get('keywordsets', [])]
    
    def getKeywords(self):
        res = self.o.get('keywords', [])
        for kwset in self.getKeywordsets():
            res.extend(kwset.getKeywords())
        return res

    def getKeywordsets(self):
        if self.keywordsets is None:
            self.keywordsets = []
            for kwset in self.o.get('keywordsets', []):
                self.keyworsets.append(MongoManager.getKeywordset(id=str(kwset['_id'])))        
        return self.keywordsets

    def addKeywordset(self, keywordset):
        self.keywordsets.append(keywordset)

class Keywordset(object):
    
    def __init__(self, id, mongokws):
        self.id = id
        self.o = mongokws
        self.keywordsets = []

    def getId(self):
        return self.id
    
    def getName(self):
        return self.o['name']

    def setValue(self, v):
        self.o['value'] = v
        
    def getValue(self):
        return self.o['value']
    
    def __unicode__(self):
        return u"<Keyworset %s>" % self.getName()
    
    def __repr__(self):
        return self.__unicode__().encode("latin1")
    
    def getKeywords(self):
        res = self.o.get('keywords', [])
        for kwset in self.getKeywordsets():
            res.extend(kwset.getKeywords())
        return res

    def getOwnKeywordsetIds(self):
        return [str(k['_id']) for k in self.o.get('keywordsets', [])]
    
    def getKeywordsets(self):
        return self.keywordsets
            
    def addKeywordset(self, keywordset):
        self.keywordsets.append(keywordset)
        
    def __iter__(self):
        for kw in self.getKeywords():
            yield kw    
        
        
class Campaign(object):
    
    def __init__(self, id, mongocampaign):
        self.id = id
        self.o = mongocampaign

    def getId(self):
        return self.id
    
    def __unicode__(self):
        return u"<Campaign %s>" % self.getName()
    
    def __repr__(self):
        return self.__unicode__()

    def getName(self):
        return self.o.get('name', "")
    
    def getBrands(self):
        return [Brand(id, prod) for id, prod in self.o.get('brands', {}).items()]

    def getTopics(self):
        return [Topic(id, topic) for id, topic in self.o.get('topics', {}).items()]
    
    def getFollowAccounts(self):
        s = set()
        for b in self.getBrands():
            s |= b.getFollowAccounts()
        return s

class Poll(object):
    
    def __init__(self, id, mongopoll):
        self.id = id
        self.o = mongopoll

    def getId(self):
        return self.id
    
    def __unicode__(self):
        return u"<Poll %s>" % self.getName()
    
    def __repr__(self):
        return self.__unicode__()

    def getName(self):
        return self.o.get('name', "")
    
    def getPollHashtag(self):
        return self.o.get("poll_hashtag", "")

    def getOptionHashtags(self):
        return [x.strip() for x in self.o.get("hashtags","").split(",") if x.strip()]
    
    def getSearchHashtags(self):
        if self.getPollHashtag():
            return set([self.getPollHashtag()])
        else:    
            return set([x.strip() for x in self.getOptionHashtags()])
    
class Account(object):
    
    def __init__(self, mongoaccount):
        self.o = mongoaccount

    def getId(self):
        return str(self.o['_id'])

    def __unicode__(self):
        return "<Account %s>" % self.getName()
    
    def __repr__(self):
        return self.__unicode__()
    
    def getName(self):
        return self.o['name']
    
    def getActiveCampaigns(self):
        return [Campaign(id, camp) for id, camp in self.o.get('campaigns', {}).items() if camp.get("active", False)]

    def getActivePolls(self):
        return [Poll(id, poll) for id, poll in self.o.get('polls', {}).items() if poll.get("active", True)]
    
    def getCampaign(self, **kwargs):
        if 'id' in kwargs:
            return Campaign(self.o['campaigns'][kwargs['id']])
        return None
    
    def getFollowAccounts(self):
        s = set()
        for b in self.getActiveCampaigns():
            s |= b.getFollowAccounts()
        return s    
    
    def getPollSearchHashtags(self):
        s = dict()
        for poll in self.getActivePolls():
            for ht in poll.getSearchHashtags():
                if ht not in s: s[ht] = []
                s[ht].append(poll)
        return s     
    
class MongoIterator(object):
    
    def __init__(self, collection, item_constructor):
        self.collection = collection
        self.item_constructor = item_constructor
        self.created = datetime.now()
        
    def __iter__(self):
        for i in self.collection:
            yield self.item_constructor(i)
                
    def __len__(self):
        return len(self.collection)

    def __getitem__(self, idx):
        return self.collection[idx]


    def getAge(self):
        return datetime.now() - self.created



    
class MongoManager(object):

    db = None
    cached_active_accounts = {}
    cached_polls_by_hashtag = {}
    follow_accounts_by_campaign = {}
    
    @classmethod
    def connect(cls):
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
        cls.db = mclient['monitor']
        if args.auth:
            cls.db.authenticate(dbuser, dbpasswd)
        
    def isConnected(self):
        return self.db != None

    @classmethod
    def getActiveAccounts(cls, **kwargs):
        #return [Account(acc) for acc in self.db.accounts.find({"$or": [{"active": True}, {"active": {"$exists": False}}]})]
        max_age = kwargs.get('max_age', timedelta(seconds=0))
        if not max_age or not cls.cached_active_accounts or (datetime.now() - cls.cached_active_accounts['fetch_time'] > max_age):
            cls.cached_active_accounts = {'data': MongoIterator(list(cls.db.accounts.find({"$or": [{"active": True}, {"active": {"$exists": False}}]})), Account), 'fetch_time': datetime.now()}
        return cls.cached_active_accounts['data']
    
    @classmethod
    def findTweets(cls, collection_name, **kwargs):
        from tweet import Tweet
        filters = kwargs.get("filters", {})
        sort = kwargs.get("sort", ())
        skip = kwargs.get("skip", None)
        limit = kwargs.get("limit", None)
        res = cls.db[collection_name].find(filters)
        if sort: res.sort(*sort)
        if skip is not None: res.skip(skip)
        if limit is not None: res.limit(limit)
        return MongoIterator(res, Tweet.createFromMongoDoc)

    @classmethod
    def countDocuments(cls, collection_name, **kwargs):
        filters = kwargs.get("filters", {})
        skip = kwargs.get("skip", None)
        limit = kwargs.get("limit", None)
        res = cls.db[collection_name].find(filters)
        if skip is not None: res.skip(skip)
        if limit is not None: res.limit(limit)
        return res.count()
    
    
    @classmethod
    def getAccount(cls, **kwargs):
        if not kwargs: return None
        d = {}
        if 'id' in kwargs:
            d['_id'] = ObjectId(kwargs['id'])
        return Account(cls.db.accounts.find_one(d))  
    
    @classmethod
    def getKeywordset(cls, **kwargs):
        if not kwargs: return None
        d = {}
        if 'id' in kwargs:
            d['_id'] = ObjectId(kwargs['id'])
        if 'name' in kwargs:
            d['name'] = kwargs['name']
        mongokwset = cls.db.keywordset.find_one(d)
        kwset = Keywordset(mongokwset['_id'], mongokwset) 
        for child_kwset_id in kwset.getOwnKeywordsetIds():
            child_kwset = cls.getKeywordset(id=child_kwset_id)
            kwset.addKeywordset(child_kwset)
        return kwset

    @classmethod
    def getPollsByHashtag(cls, **kwargs):
        #return [Account(acc) for acc in self.db.accounts.find({"$or": [{"active": True}, {"active": {"$exists": False}}]})]
        max_age = kwargs.get('max_age', timedelta(seconds=0))
        if not max_age or not cls.cached_polls_by_hashtag or (datetime.now() - cls.cached_polls_by_hashtag['fetch_time'] > max_age):
            data={}
            accounts = cls.getActiveAccounts(max_age = max_age)
            for acc in accounts:
                d = acc.getPollSearchHashtags()
                for ht, polls in d.items():
                    if ht not in data: data[ht] = []
                    data[ht].extend(polls)
            cls.cached_polls_by_hashtag = {'data': data, 'fetch_time': datetime.now()}
        return cls.cached_polls_by_hashtag['data']

    @classmethod
    def getFollowAccountsbyCampaign(cls, **kwargs):
        max_age = kwargs.get('max_age', timedelta(seconds=0))
        if not max_age or not cls.follow_accounts_by_campaign or (datetime.now() - cls.follow_accounts_by_campaign['fetch_time'] > max_age):
            data = {}
            accounts = cls.getActiveAccounts(max_age = max_age)
            s = {}
            for acc in accounts:
                for campaign in acc.getActiveCampaigns():
                    for brand in campaign.getBrands():
                        follow_accounts = brand.getFollowAccounts() 
                        for fa in follow_accounts:
                            if fa not in s: s[fa] = []
                            s[fa].append({"cid": campaign.getId(), "bid": brand.getId(), "brand": brand.getName(), 'own_brand': brand.isOwnBrand()})
            
            cls.follow_accounts_by_campaign = {'data': s, 'fetch_time': datetime.now()}
        return cls.follow_accounts_by_campaign['data']


    @classmethod
    def saveDocument(cls, collection_name, doc):
        return cls.db[collection_name].save(doc)
    
MongoManager.connect()


if __name__ == "__main__":
    mm = MongoManager
    print mm.getPollsByHashtag()
    """
    beber = "5403eb34fbe4d07b0d73407f"
    futbol = "5403ebf0fbe4d07b0d734080"
    k = mm.getKeywordset(name=u"Fútbol")
    pprint(k)
    pprint(k.getKeywords())
    pprint(k.getKeywordsets())
    
    exit(0)
    print mm.isConnected()
    for acc in mm.getActiveAccounts():
        #time.sleep(1)
        print acc
        
    print mm.getActiveAccounts()[1]
    exit(0)
    acc = mm.getAccount(id='53ff7ae51e076582a6fb7f12')
    print mm.getSearchKeywords()
    print mm.getFollowAccounts()
    print mm.getPollSearchHashtags()
    """