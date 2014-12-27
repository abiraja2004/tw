#encoding: utf-8

from pipeline import Pipeline
from mongo import MongoManager
from datetime import datetime, timedelta
from pprint import pprint
from tweet import Tweet
from classifiermanager import ClassifierManager



class TweetProcessStage_1(Pipeline.Stage):  
    #aca se crea como tweet y se aplica brand classifier / recibe un dict y devuelve un tweet

    
    def processItem(self, item):
        accs = MongoManager.getActiveAccounts(max_age=timedelta(seconds=10))
        tweet = Tweet.createFromRawGnipActivity(item)
        pprint (tweet)
        pprint (tweet.getExtractedInfo())
        tweet.applyBrandClassifiers(ClassifierManager.getBrandClassifiers())
        pprint (tweet.getExtractedInfo())
        #pprint(item['gnip']['matching_rules'])
        print
        return tweet

class TweetProcessStage_2(Pipeline.Stage):  #aca se aplica topic classifier

    
    def processItem(self, tweet):
        accs = MongoManager.getActiveAccounts(max_age=timedelta(seconds=10))
        pprint (tweet.getExtractedTopics())
        tweet.applyTopicClassifiers(ClassifierManager.getTopicClassifiers())
        pprint (tweet.getExtractedTopics())
        return tweet

class TweetSaveStage(Pipeline.Stage): #aca se graba en mongo en las campañas que corresponda

    def processItem(self, tweet):
        
        for pm in tweet.getExtractedInfo():
            cid = pm.get('campaign_id', None)
            if cid:
                MongoManager.saveDocument("tweets_%s" % cid, tweet.getDictionary())
                pprint("tweet %s grabado" % tweet)
        #no devuelvo nada para que no quede encolado en la ultima queue para siempre y se llene la memoria
        return None



def getPipelineStageClasses():
    return [TweetProcessStage_1, TweetProcessStage_2, TweetSaveStage]