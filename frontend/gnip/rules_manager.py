from gnip import GnipTwitterManager, GnipCollectionManager
from mongo import MongoManager
from pprint import pprint
from utils import MyThread
from topicclassifier import TopicClassifier
from brandclassifier import BrandClassifier
import time
from datetime import timedelta, datetime
import re
from classifiermanager import ClassifierManager
import traceback



class GnipTwitterRulesManager(object):
    
    def __init__(self):
        pass
    
    def generateGnipRulesFromMongo(self):
        accounts = MongoManager.getActiveAccounts()
        rules = []
        for acc in accounts:
            for camp in acc.getActiveCampaigns():
                for brand in camp.getBrands():
                    fa = sorted(brand.getFollowAccounts())
                    if fa: 
                        rules.append({"value": " OR ".join(fa), "tag": "%s/%s/%s/follow accounts - mention" % (acc.getName(), camp.getName(), brand.getName())})
                        clean_user_names = [x.replace("@", "") for x in fa]
                        rules.append({"value": " OR ".join(["from:%s" % x for x in clean_user_names]), "tag": "%s/%s/%s/follow accounts - from" % (acc.getName(), camp.getName(), brand.getName())})
                        rules.append({"value": " OR ".join(["to:%s" % x for x in clean_user_names]), "tag": "%s/%s/%s/follow accounts - to" % (acc.getName(), camp.getName(), brand.getName())})
                    #BRAND RULES
                    for brule in brand.getIdentificationRules():
                        brule = brule.replace("[m]", "[M]").replace("[p]", "[P]")
                        for bsearch_keyword in brand.getSearchKeywords():
                            brand_replaced_rule = '"' + brule.replace("[M]", bsearch_keyword) + '"'
                            if (brule.upper().find("[P]") >= 0):
                                for product in brand.getProducts():
                                    if product.isUsingBrandIdRules():
                                        for psearch_keyword in product.getSearchKeywords():
                                            product_replaced_rule = brand_replaced_rule.replace("[P]", psearch_keyword)
                                            rules.append({"value": product_replaced_rule, "tag": "%s/%s/%s/%s: %s" % (acc.getName(), camp.getName(),brand.getName(), product.getName(), brule)})
                            else:
                                rules.append({"value": brand_replaced_rule, "tag": "%s/%s/%s: %s" % (acc.getName(), camp.getName(), brand.getName(), brule)})
                    #PRODUCT RULES
                    for product in brand.getProducts():
                        for prule in product.getIdentificationRules():
                            prule = prule.replace("[m]", "[M]").replace("[p]", "[P]")                        
                            for bsearch_keyword in brand.getSearchKeywords():
                                brand_replaced_rule = '"' + prule.replace("[M]", bsearch_keyword) + '"'
                                for psearch_keyword in product.getSearchKeywords():
                                    product_replaced_rule = brand_replaced_rule.replace("[P]", psearch_keyword)
                                    rules.append({"value": product_replaced_rule, "tag": "%s/%s/%s/%s: %s" % (acc.getName(), camp.getName(), brand.getName(), product.getName(), prule)})                                    
            for poll in acc.getActivePolls():
                rules.append({"value": " OR ".join(sorted(poll.getSearchHashtags())), "tag": "%s/poll %s" % (acc.getName(), poll.getName())})                
        return rules
    
    
    def updateGnipRules(self):
        UN = 'federicog@promored.mx'
        PWD = 'ladedarin'
        ACCOUNT = 'promored'
        rm = GnipTwitterManager(ACCOUNT, UN, PWD)    

        current_gnip_rules = rm.getRules()
        current_gnip_rule_values = set([r['value'] for r in current_gnip_rules])
        mongo_rules = self.generateGnipRulesFromMongo()
        
        for r in mongo_rules:
            r['value'] = "(%s) (twitter_lang:es) -is:retweet" % r['value'] #AGREGO FILTRO POR LANG:ES en todas las reglas
        
        mongo_rule_values = set([r['value'] for r in mongo_rules])
        
        rulesToRemove = [r for r in current_gnip_rules if r['value'] not in mongo_rule_values]
        rulesToAdd = [r for r in mongo_rules if r['value'] not in current_gnip_rule_values]
        
        if rulesToAdd:
            print "Rules to ADD:"
            pprint(rulesToAdd)

        if rulesToRemove:
            print "Rules to DELETE:"
            pprint(rulesToRemove)
            
        if rulesToAdd: rm.addRules(rulesToAdd)        
        if rulesToRemove: rm.deleteRules(rulesToRemove)


        
class GnipCollectionRulesManager(object):
    
    def __init__(self):
        pass
    
    def generateGnipRulesFromMongo(self):
        accounts = MongoManager.getActiveAccounts()
        rules = []
        for acc in accounts:
            for camp in acc.getActiveCampaigns():
                for fp in camp.getFacebookFanpages():
                    #rules.append({"value": fp, "tag": "%s/%s/%s" % (acc.getName(), camp.getName(), fp)})
                    rules.append({"value": fp, "tag": None})
        return rules
    
    
    def updateGnipRules(self):
        UN = 'pablobesada'
        PWD = 'pdbpdb'
        ACCOUNT = 'promored'
        rm = GnipCollectionManager(ACCOUNT, UN, PWD)    

        current_gnip_rules = rm.getRules()
        current_gnip_rule_values = set([r['value'] for r in current_gnip_rules])
        mongo_rules = self.generateGnipRulesFromMongo()
                
        mongo_rule_values = set([r['value'] for r in mongo_rules])
        
        rulesToRemove = [r for r in current_gnip_rules if r['value'] not in mongo_rule_values]
        rulesToAdd = [r for r in mongo_rules if r['value'] not in current_gnip_rule_values]
        
        if rulesToAdd:
            print "Rules to ADD:"
            pprint(rulesToAdd)

        if rulesToRemove:
            print "Rules to DELETE:"
            pprint(rulesToRemove)
            
        if rulesToAdd: rm.addRules(rulesToAdd)        
        if rulesToRemove: rm.deleteRules(rulesToRemove)


class RulesMonitor(MyThread):
    INSTANCE = None
    CHECK_PERIOD = 5 #seconds
    def __init__(self):
        MyThread.__init__(self)
        self.finish_flag = False
        RulesMonitor.INSTANCE = self
        self.gnipTwitterRulesManager = GnipTwitterRulesManager()
        self.gnipCollectionRulesManager = GnipCollectionRulesManager()
        
    @classmethod
    def getInstance(cls):
        return cls.INSTANCE
    
    def stopWorking(self):
        self.finish_flag = True
        print "Rules monitor finishing..."
    
    def run(self):
        print "Rules monitor running..."
        while not self.finish_flag:
            try:
                self.gnipTwitterRulesManager.updateGnipRules()
            except:
                traceback.print_exc(file=sys.stdout)
            try:
                self.gnipCollectionRulesManager.updateGnipRules()
            except:
                traceback.print_exc(file=sys.stdout)
            time.sleep(RulesMonitor.CHECK_PERIOD)

    
if __name__ == "__main__":
    """
    t = "marca propia 2 m2"
    bcs = ClassifierManager.getTopicClassifiers()
    pprint(bcs)
    for k, bc in bcs.items():
        print k.__class__
        print bc.__class__
        pms = bc.extract(t)
        for pm in pms: 
            pprint(pm.getDictionary())
            print "-" * 10
        print "-"* 30
    exit(0)
    """
    
    
    rmon = RulesMonitor()
    rmon.start()    
    try:    
        while True:
            time.sleep(1)
    except KeyboardInterrupt, e:
        rmon.stopWorking()
        rmon.join()
        print "Terminado.\n"
        MyThread.checkFinalization()    
    exit(0)
    
    

 
 