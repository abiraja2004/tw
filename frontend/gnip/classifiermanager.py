#encoding: utf-8

from mongo import MongoManager
from datetime import timedelta
from brandclassifier import BrandClassifier
from topicclassifier import TopicClassifier
import re

class Rule(object):
    
    def __init__(self, type):
        self.type=type
        self.name = None
        self.synonyms = set()
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

class ClassifierManager(object):    
    def genClassifierClues(self, keywords):
        d = {}
        for kw, v in keywords:
            l = d.get(v, [])
            l.append(kw)
            d[v] = l
        res = []
        for k, v in d.items():
            res.append((int(k),) + tuple(v))
        return res

    def generateTopicClassifier(self, topicdoc):
        tc = TopicClassifier()
        tc.topic_name = topicdoc.getName()
        tc.topic_id = str(topicdoc.getId())
        tc.topic_confidence_clues = self.genClassifierClues(topicdoc.getKeywords())
        for kws in topicdoc.getKeywordsets():
            tc.topic_confidence_clues.append((kws.getValue(),) + tuple(MongoManager.getKeywordset(id=kws.getId()).getKeywords()))
        return tc

    def generateBrandClassifier(self, br):
        bc = BrandClassifier()
        bc.account_id = br.account_id
        bc.account_name = br.account_name
        bc.campaign_id = br.campaign_id
        bc.campaign_name = br.campaign_name
        bc.score_threshold = br.score_threshold
        bc.name = {br.name: br.synonyms}
        bc.brand_confidence_clues = self.genClassifierClues(br.keywords)
        for kws in br.keyword_sets:
            if kws.getId():
                bc.brand_confidence_clues.append((kws.getValue(),) + tuple(MongoManager.getKeywordset(id=kws.getId()).getKeywords()))
        if br.rules:
            bc.brand_regexps = [(re.compile(self.getBrandRegexpFromRule(br, rule), re.I|re.U), rule) for rule in br.rules]
        pr_number = 0
        for pr in br.children:
            bc.product_list.append(pr.name)
            bc.products[pr.name] = pr.synonyms
            bc.product_regexps[pr.name] = []
            for rule in pr.rules:
                bc.product_regexps[pr.name].append((re.compile(self.getProductRegexpFromRule(br, pr, pr_number, rule), re.I|re.U), rule))
            if pr.use_brand_id_rules: 
                for rule in br.rules:
                    if rule.find("[P]") >= 0:
                        bc.product_regexps[pr.name].append((re.compile(self.getProductRegexpFromRule(br, pr, pr_number, rule), re.I|re.U), rule))
            pr_number += 1
            bc.product_confidence_clues[pr.name] = self.genClassifierClues(pr.keywords)
        return bc

    def genEntityRegexp(self, entity_type, name, entity_number, synonyms):        
        kws = set([name]) | synonyms
        kws = [s.lower().strip() for s in kws]
        regexp = "(?:" + '|'.join(["(?P<%s_%s_%s>%s)" % (entity_type,entity_number, cnt,rx) for rx,cnt in zip(kws,range(len(kws)))]) + ")"
        return regexp

    def getBrandRegexpFromRule(self, br, rule):
        rule = rule.replace("[m]", "[M]").strip()
        brand_regexp = self.genEntityRegexp("BLD", br.name, 0, br.synonyms)
        return "(?:\\A|\\Z|\\W)" + rule.replace(" ", "\\W+").replace("[M]", brand_regexp) + "(?:\\A|\\Z|\\W)"
    
    def getProductRegexpFromRule(self, br, pr, pr_number, rule):
        rule = rule.replace("[m]", "[M]").replace("[p]", "[P]").strip()
        brand_regexp = self.genEntityRegexp("BLD", br.name, 0, br.synonyms)
        product_regexp = self.genEntityRegexp("PLD", pr.name, pr_number, pr.synonyms)
        return "(?:\\A|\\Z|\\W)" + rule.replace(" ", "\\W+").replace("[M]", brand_regexp).replace("[P]", product_regexp) + "(?:\\A|\\Z|\\W)"


    def getProductRules(self, product):
        pr = Rule("Product")
        pr.name = product.getName()
        pr.synonyms = product.getSynonyms()
        pr.keywords = product.getKeywords()
        pr.keywords_sets = product.getKeywordsets()
        pr.rules = product.getIdentificationRules()
        pr.use_brand_id_rules = product.isUsingBrandIdRules()
        return pr

    def getBrandRules(self, brand, campaign_id, campaign, account):
        br = Rule("Brand")
        br.account_id = account.getId()
        br.account_name = account.getName()
        br.campaign_id = campaign.getId()
        br.campaign_name = campaign.getName()
        br.name = brand.getName()
        br.synonyms = brand.getSynonyms() ##ojo que antes era un string y ahora es un set
        br.follow_accounts = brand.getFollowAccounts() ##ojo que antes era un string y ahora es un set
        br.keywords = brand.getKeywords()
        br.keyword_sets = brand.getKeywordsets()
        br.rules = brand.getIdentificationRules()
        br.score_threshold = brand.getScoreThreshold()
        for prod in brand.getProducts():
            br.children.append(self.getProductRules(prod))
        return br

    def getCampaignRules(self, campaign_id, campaign, account):
        rules = []
        for brand in campaign.getBrands():
            rules.append(self.getBrandRules(brand, campaign.getId(), campaign, account))
        return rules


    def getAccountRules(self, account):
        rules = []
        for camp in account.getActiveCampaigns():
            rules.extend(self.getCampaignRules(camp.getId(), camp, account))
        return rules
    
    
    @classmethod
    def getBrandClassifiers(cls):
        #faltaria buffer por max_age
        o = cls()
        accounts = MongoManager.getActiveAccounts(max_age=timedelta(seconds=10))
        rules = []
        for acc in accounts:
            rules.extend(o.getAccountRules(acc))
        res = []
        for r in rules:
            res.append(o.generateBrandClassifier(r))
        return res
    
    @classmethod
    def getCampaignBrandClassifiers(cls, account, campaign):
        #faltaria buffer por max_age
        o = cls()
        rules = o.getCampaignRules(campaign.getId(), campaign, account)
        res = []
        for r in rules:
            res.append(o.generateBrandClassifier(r))
        return res    

    @classmethod
    def getTopicClassifiers(cls):
        #faltaria buffer por max_age
        #devuelve un diccionario con los topics x campania
        o = cls()
        res = {}
        accounts = MongoManager.getActiveAccounts(max_age=timedelta(seconds=10))
        for acc in accounts:
            for campaign in acc.getActiveCampaigns():
                topics = campaign.getTopics()
                if not topics: continue
                res[campaign.getId()] = {}
                for topic in topics:
                    #topic['_id'] = topic.getId() ###ESTO VA???
                    res[campaign.getId()][topic.getId()] = o.generateTopicClassifier(topic)
        return res

    @classmethod
    def getCampaignTopicClassifiers(cls, campaign):
        #devuelve un diccionario con los topics para la campaña solicitada
        o = cls()
        res = {}
        topics = campaign.getTopics()
        for topic in topics:
            #topic['_id'] = topic.getId() ###ESTO VA???
            res[topic.getId()] = o.generateTopicClassifier(topic)
        return res


    
    
