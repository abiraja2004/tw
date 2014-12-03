#encoding: utf-8
from pymongo import MongoClient
from bson import ObjectId
from brandclassifier import BrandClassifier
from topicclassifier import TopicClassifier
import re

import argparse
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


class Rule(object):
    
    def __init__(self, type):
        self.type=type
        self.name = None
        self.synonyms = ''
        self.keywords = []
        self.keyword_sets = []
        self.rules = []
        self.children = []

    def __str__(self):
        return "<%s %s: %s -- %s -- %s -- %s>" % (self.type, self.name, self.synonyms, self.keywords, self.keyword_sets, self.rules)

    def __unicode__(self):
        return u"<%s %s: %s %s>" % (self.type, self.name, self.rules, '\n  '.join([unicode(c) for c in self.children]))

    def __repr__(self):
        return self.__str__()

def fetchKeywordset(kws_id):    
    kwset = monitor.keywordset.find_one({"_id": kws_id})
    res = []
    if kwset:
        #print "KEYWORDSET %s FETCHED. " % kwset['name']        
        res.extend(kwset['keywords'])
        for kws in kwset['keywordsets']:
            res.extend(fetchKeywordset(ObjectId(kws['_id'])))
    return res
    
def genClassifierClues(keywords):
    d = {}
    for kw, v in keywords:
        l = d.get(v, [])
        l.append(kw)
        d[v] = l
    res = []
    for k, v in d.items():
        res.append((int(k),) + tuple(v))
    return res

def generateTopicClassifier(topicdoc):
    tc = TopicClassifier()
    tc.topic_name = topicdoc['name']
    tc.topic_id = str(topicdoc['_id'])
    tc.topic_confidence_clues = genClassifierClues(topicdoc['keywords'])
    for kws in topicdoc['keywordsets']:
        tc.topic_confidence_clues.append((kws['value'],) + tuple(fetchKeywordset(ObjectId(kws['_id']))))
    return tc

def generateBrandClassifier(br):
    bc = BrandClassifier()
    bc.account_id = br.account_id
    bc.account_name = br.account_name
    bc.campaign_id = br.campaign_id
    bc.campaign_name = br.campaign_name
    bc.name = {br.name: br.synonyms}
    bc.brand_confidence_clues = genClassifierClues(br.keywords)
    for kws in br.keyword_sets:
        bc.brand_confidence_clues.append((kws['value'],) + tuple(fetchKeywordset(kws['_id'])))
    if br.rules:
        bc.brand_regexps = [(re.compile(getBrandRegexpFromRule(br, rule), re.I|re.U), rule) for rule in br.rules]
    pr_number = 0
    for pr in br.children:
        bc.product_list.append(pr.name)
        bc.products[pr.name] = pr.synonyms
        bc.product_regexps[pr.name] = []
        for rule in pr.rules:
            bc.product_regexps[pr.name].append((re.compile(getProductRegexpFromRule(br, pr, pr_number, rule), re.I|re.U), rule))
        if pr.use_brand_id_rules: 
            for rule in br.rules:
                if rule.find("[P]") >= 0:
                    bc.product_regexps[pr.name].append((re.compile(getProductRegexpFromRule(br, pr, pr_number, rule), re.I|re.U), rule))
        pr_number += 1
        bc.product_confidence_clues[pr.name] = genClassifierClues(pr.keywords)
    return bc

def genEntityRegexp(entity_type, name, entity_number, synonyms):        
    kws = [name] + [s.strip() for s in synonyms.split(",") if s.strip()]
    kws = [s.lower().strip() for s in kws]
    regexp = "(?:" + '|'.join(["(?P<%s_%s_%s>%s)" % (entity_type,entity_number, cnt,rx) for rx,cnt in zip(kws,range(len(kws)))]) + ")"
    return regexp

def getBrandRegexpFromRule(br, rule):
    rule = rule.replace("[m]", "[M]")
    brand_regexp = genEntityRegexp("BLD", br.name, 0, br.synonyms)
    return "(?:\\A|\\Z|\\W)" + rule.replace(" ", "\\W+").replace("[M]", brand_regexp) + "(?:\\A|\\Z|\\W)"
    
def getProductRegexpFromRule(br, pr, pr_number, rule):
    rule = rule.replace("[m]", "[M]").replace("[p]", "[P]")
    brand_regexp = genEntityRegexp("BLD", br.name, 0, br.synonyms)
    product_regexp = genEntityRegexp("PLD", pr.name, pr_number, pr.synonyms)
    return "(?:\\A|\\Z|\\W)" + rule.replace(" ", "\\W+").replace("[M]", brand_regexp).replace("[P]", product_regexp) + "(?:\\A|\\Z|\\W)"


def getProductRules(product):
    pr = Rule("Product")
    pr.name = product.get("name", "")
    pr.synonyms = product.get('synonyms', '')
    pr.keywords = product.get('keywords', [])
    pr.keywords_sets = product.get('keyword_sets', [])
    pr.rules = product.get('identification_rules', [])
    pr.use_brand_id_rules = product.get("use_brand_id_rules", False)
    return pr

def getBrandRules(brand, campaign_id, campaign, account):
    br = Rule("Brand")
    br.account_id = str(account.get('_id',''))
    br.account_name = account.get('name','')
    br.campaign_id = campaign_id
    br.campaign_name = campaign.get('name','')
    br.name = brand.get("name", "")
    br.synonyms = brand.get('synonyms', '')
    br.follow_accounts = brand.get('folllow_accounts', '')
    br.keywords = brand.get('keywords', [])
    br.keyword_sets = brand.get('keyword_sets', [])
    br.rules = brand.get('identification_rules', [])
    for prod_id, prod in brand['products'].items():
        br.children.append(getProductRules(prod))
    return br

def getCampaignRules(campaign_id, campaign, account):
    rules = []
    for brand_id, brand in campaign['brands'].items():
        rules.append(getBrandRules(brand, campaign_id, campaign, account))
    return rules


def getAccountRules(account):
    rules = []
    for camp_id, camp in account['campaigns'].items():
        if 'active' in camp and camp['active']:
            rules.extend(getCampaignRules(camp_id, camp, account))
    return rules

def regenerateRules():
    accounts = monitor.accounts.find({})
    rules = []
    for acc in accounts:
        rules.extend(getAccountRules(acc))
    for r in rules:
        print r.__unicode__()
        print
    bc = generateBrandClassifier(rules[1])
    print "CONF:", bc.brand_confidence_clues
    
    

def getBrandClassifiers():
    accounts = monitor.accounts.find({})
    rules = []
    for acc in accounts:
        rules.extend(getAccountRules(acc))
    res = []
    for r in rules:
        res.append(generateBrandClassifier(r))
    return res

def getTopicClassifiers():
    #devuelve un diccionario con los topics x campania
    res = {}
    accounts = monitor.accounts.find({})
    for acc in accounts:
        for campaign_id, campaign in acc['campaigns'].items():
            if not 'active' in campaign or not campaign['active'] or not 'topics' in campaign: continue
            res[campaign_id] = {}
            for topic_id, topic in campaign['topics'].items():
                topic['_id'] = topic_id
                res[campaign_id][topic_id] = generateTopicClassifier(topic)
                    
    #los topics globales por ahora quedan desactivados
    """
    topics = monitor.topic.find({})
    res = []
    for topicdoc in topics:
        res.append(generateTopicClassifier(topicdoc))
    """
    return res

def getAccountsToTrack():
    accounts = monitor.accounts.find({})
    s = dict()
    i = dict()
    for acc in accounts:
        for cid, campaign in acc['campaigns'].items():
            if not 'active' in campaign or not campaign['active']: continue
            for bid, brand in campaign['brands'].items():
                if brand.get('follow_accounts','').strip():
                    for kw in [kw.strip() for kw in brand['follow_accounts'].split(",") if kw.strip()]:
                            s[kw] = {"cid": cid, "bid": bid, "brand": brand['name'], 'own_brand': brand['own_brand']}
                if brand.get('follow_account_ids','').strip():
                    for kw in [kw.strip() for kw in brand['follow_account_ids'].split(",") if kw.strip()]:
                            i[kw] = {"cid": cid, "bid": bid, "brand": brand['name'], 'own_brand': brand['own_brand']}
    return s,i

if __name__ == "__main__":
            
    bcs = getTopicClassifiers()
    bcs2 = getTopicClassifiers()
    print bcs == bcs2
