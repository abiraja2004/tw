from pymongo import MongoClient
from brandclassifier import BrandClassifier
import re
mclient = MongoClient()
monitor = mclient['monitor']

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
    if kwset:
        res = kwset['keywords']
        if res: return res
    return []
    
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
    brand_regexp = genEntityRegexp("BLD", br.name, 0, br.synonyms)
    return "(?:\\A|\\Z|\\W)" + rule.replace(" ", "\\W+").replace("[M]", brand_regexp) + "(?:\\A|\\Z|\\W)"
    
def getProductRegexpFromRule(br, pr, pr_number, rule):
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

def getBrandRules(brand, campaign, account):
    br = Rule("Brand")
    br.account_id = str(account.get('_id',''))
    br.account_name = account.get('name','')
    br.campaign_id = str(campaign.get('_id',''))
    br.campaign_name = campaign.get('name','')
    br.name = brand.get("name", "")
    br.synonyms = brand.get('synonyms', '')
    br.keywords = brand.get('keywords', [])
    br.keyword_sets = brand.get('keyword_sets', [])
    br.rules = brand.get('identification_rules', [])
    for prod_id, prod in brand['products'].items():
        br.children.append(getProductRules(prod))
    return br

def getCampaignRules(campaign, account):
    rules = []
    for brand_id, brand in campaign['brands'].items():
        rules.append(getBrandRules(brand, campaign, account))
    return rules


def getAccountRules(account):
    rules = []
    for camp_id, camp in account['campaigns'].items():
        rules.extend(getCampaignRules(camp, account))
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


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--regenerate_rules", nargs='?')
    args = parser.parse_args()
    if "regenerate_rules" in args:
        regenerateRules()
