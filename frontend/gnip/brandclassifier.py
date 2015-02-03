#encoding: utf-8

import re
import pymongo

class ProductMatch(object):
    
    def __init__(self):
        self.brand = ""
        self.product = ""
        self.sentiment = None
        self.brand_matched_word = ""
        self.brand_matched_pos = (-1, -1)
        self.product_matched_word = ""
        self.product_matched_pos = (-1, -1)
        self.source = ""
        self.patten = ""
        self.rule = ""
        self.campaign_id = ""
        self.campaign_name = ""
        self.account_id = ""
        self.account_name = ""
        self.confidence = 0
    
    
    def __unicode__(self):
        return u"<Brand: %s, Product: %s>" % (self.brand, self.product)
    
    def getDetail(self):
        ctx = 10
        res  = u"Brand: %s, match: %s, context: %s" % (self.brand, self.brand_matched_word, self.source[(self.brand_matched_pos[0]-ctx):(self.brand_matched_pos[1]+ctx)])
        res = res + "\nProduct: %s, match: %s, context: %s" % (self.product, self.product_matched_word, self.source[(self.product_matched_pos[0]-ctx):(self.product_matched_pos[1]+ctx)])
        return res

    def getDictionary(self):
        res = {}
        for k in ("brand","product","sentiment","brand_matched_word","brand_matched_pos","product_matched_word","product_matched_pos","source","patten","rule","campaign_id","campaign_name","account_id","account_name", "confidence"):
            res[k] = self.__getattribute__(k)
        return res
                          
class BrandClassifier(object):

    #name = "Brand"
    #brands= ["Brand"]
    #products = ["Product 1", "Product 2", {u"Product 3": ["prod3", u"producto 3"]}]
    
    def __str__(self):
        return ""
    
    def __init__(self):
        self.campaign_id = ""
        self.campaign_name = ""
        self.brand_regexps = []  #lista de tuplas (regexp, rule)
        self.product_regexps = {} #diccionario: producto->lista de tuplas (regexp,rule)
        self.name = ""
        self.products = {}
        self.product_list = []
    
        self.brand_confidence_clues = []
        self.product_confidence_clues = {}
        
        self.pld_counter = 1
        self.bld_counter = 1
        self.brandLookupDict = {}
        self.rule = ""
    

    def getProductLookupWords(self):
        self.productLookupDict = {}
        res = []
        for p in self.products:
            if isinstance(p, basestring): 
                res.append("(?P<PLD_%s>%s+)" % (self.pld_counter,p))
                self.productLookupDict["PLD_%s"%self.pld_counter] = p
                self.pld_counter += 1
            elif isinstance(p, dict):
                for k,v in p.items():
                    res.append("(?P<PLD_%s>%s+)" % (self.pld_counter, k))
                    self.productLookupDict["PLD_%s"%self.pld_counter] = k
                    self.pld_counter += 1                    
                    if isinstance(v, basestring): 
                        res.append("(?P<PLD_%s>%s+)" % (self.pld_counter,v))
                        self.productLookupDict["PLD_%s"%self.pld_counter] = k
                        self.pld_counter += 1                    
                    elif isinstance(v, list): 
                        for w in v:
                            res.append("(?P<PLD_%s>%s+)" % (self.pld_counter,w))            
                            self.productLookupDict["PLD_%s"%self.pld_counter] = k
                            self.pld_counter += 1                                                            
        return res

    def getBrandLookupWords(self):
        res = []
        p = self.name
        if isinstance(p, basestring): 
            res.append("(?P<BLD_%s>%s+)" % (self.bld_counter,p))
            self.brandLookupDict["BLD_%s"%self.bld_counter] = p
            self.bld_counter += 1
        elif isinstance(p, dict):
            for k,v in p.items():
                res.append("(?P<BLD_%s>%s+)" % (self.bld_counter, k))
                self.brandLookupDict["BLD_%s"%self.bld_counter] = k
                self.bld_counter += 1                    
                if isinstance(v, basestring): 
                    res.append("(?P<BLD_%s>%s+)" % (self.bld_counter,v))
                    self.brandLookupDict["BLD_%s"%self.bld_counter] = k
                    self.bld_counter += 1                    
                elif isinstance(v, list): 
                    for w in v:
                        res.append("(?P<BLD_%s>%s+)" % (self.bld_counter,w))            
                        self.brandLookupDict["BLD_%s"%self.bld_counter] = k
                        self.bld_counter += 1       
        return res
    
    
    @classmethod
    def getProductNormalizationDict(cls):
        res = {}
        for p in cls.products:
            if isinstance(p, basestring):
                res[p.lower()] = p
            elif isinstance(p, dict):
                for k,v in p.items():
                    res[k.lower()] = k
                    if isinstance(v, basestring):
                        res[v] = k
                    elif isinstance(v, list):
                        for vv in v:
                            res[vv] = k
        return res

    @classmethod
    def getBrandNormalizationDict(cls):
        res = {}
        for p in cls.brands:
            if isinstance(p, basestring):
                res[p.lower()] = p
            elif isinstance(p, dict):
                for k,v in p.items():
                    res[k.lower()] = k
                    if isinstance(v, basestring):
                        res[v] = k
                    elif isinstance(v, list):
                        for vv in v:
                            res[vv] = k
        return res

    @classmethod
    def normalizeBrand(cls, b):
        if not b: return ""
        return cls.getBrandNormalizationDict().get(b.lower(), "")

    @classmethod    
    def normalizeProduct(cls, p):
        if not p: return ""
        return cls.getProductNormalizationDict().get(p.lower(), "")

    
    def getPatterns(self):
        regexps = ["(" + r % {"BRANDS": '|'.join(self.getBrandLookupWords()), "PRODUCTS": '|'.join(self.getProductLookupWords())} + ")" for r in self.brand_regexps]
        pattern = "(" + '|'.join(regexps) + ")"
        #print pattern
        patterns = [re.compile(pattern, re.I|re.U)]
        return patterns

    
    def calculateConfidence(self, pm, text):
        def processClues(cluelist):
            res = 0
            wdict = {}
            for clue in cluelist:
                if isinstance(clue, tuple):
                    for w in clue[1:]:
                        wdict[w.lower()] = clue[0]
                else:
                    raise Exception("invalid clue: %s" % clue)
            if wdict:
                regexps = []
                kc = len(wdict.keys())
                kp = 0
                while kp < kc:                    
                    keys = wdict.keys()[kp:kp+25]
                    kp += 25
                    regexp = "(" + "|".join(["(?:(?<=\W)|^)(?P<CONFIDENCE_%s>%s)(?=\W|$)" % (c,k) for k,c in zip(keys, range(len(keys)))]) + ")"
                        #"\\b(?P<CONFIDENCE_%s>%s)\\b" % (c,k) for k,c in zip(keys, range(len(keys)))]) + ")"
                    #print regexp
                    pattern = re.compile(regexp, re.I|re.U)
                    for mo in pattern.finditer(text):
                        for k in mo.groupdict():
                            if mo.group(k) and k.startswith("CONFIDENCE"):
                                #print mo.group(k), wdict[mo.group(k).lower()]
                                res += wdict[mo.group(k).lower()]
            return res
        
        confidence = 0
        if pm.brand_matched_word: confidence += 5
        if pm.product_matched_word: 
            confidence += 5
            if pm.product in self.product_confidence_clues: confidence += processClues(self.product_confidence_clues[pm.product])
        confidence += processClues(self.brand_confidence_clues)
        return confidence
    

    def extract(self, text):
        res = []   
        for pattern, rule in self.brand_regexps:
            matches = pattern.finditer(text)
            for m in matches:
                #print pattern.pattern, m.groups()
                pm = ProductMatch()
                #print self.getBrandNormalizationDict()
                #print 1,m.group("brand1"), m.group("product1")
                #print 2,m.group("brand2"), m.group("product2")
                pm.pattern = pattern.pattern
                for k in m.groupdict():
                    if k.startswith("BLD_") and m.group(k): 
                        pm.brand = self.name.keys()[0]
                        pm.brand_matched_word = m.group(k)
                        pm.brand_matched_pos = (m.start(k), m.end(k))
                        pm.source = text
                    elif k.startswith("PLD_") and m.group(k): 
                        pm.product = self.product_list[int(k.split("_")[1])]
                        pm.product_matched_word = m.group(k)
                        pm.product_matched_pos = (m.start(k), m.end(k))
                        pm.brand = self.name.keys()[0]
                        pm.source = text                        
                pm.confidence = self.calculateConfidence(pm, text)
                pm.rule = rule
                pm.campaign_id = self.campaign_id
                pm.campaign_name = self.campaign_name
                pm.account_id = self.account_id
                pm.account_name = self.account_name
                res.append(pm)
        for prod_name in self.products.keys():
            for pattern,rule in self.product_regexps[prod_name]:
                matches = pattern.finditer(text)
                #print pattern.pattern, text
                for m in matches:
                    pm = ProductMatch()
                    pm.pattern = pattern.pattern
                    for k in m.groupdict():
                        if k.startswith("BLD_") and m.group(k): 
                            pm.brand = self.name.keys()[0]
                            pm.brand_matched_word = m.group(k)
                            pm.brand_matched_pos = (m.start(k), m.end(k))
                            pm.source = text
                        elif k.startswith("PLD_") and m.group(k): 
                            pm.product = self.product_list[int(k.split("_")[1])]
                            pm.product_matched_word = m.group(k)
                            pm.product_matched_pos = (m.start(k), m.end(k))
                            pm.brand = self.name.keys()[0]
                            pm.source = text
                    pm.confidence = self.calculateConfidence(pm, text)
                    pm.rule = rule
                    pm.campaign_id = self.campaign_id
                    pm.campaign_name = self.campaign_name
                    pm.account_id = self.account_id
                    pm.account_name = self.account_name                    
                    res.append(pm)
        return res

    