#encoding: utf-8

from datetime import datetime
from pprint import pprint

class Tweet(object):

    def __init__(self):
        self.d = {}

    def __str__(self):
        return "%s: %s" % (self.getUsername(), self.getText())
    
    def __repr__(self):
        return ("<Tweet (%s-%s) %s: %s>" % (self.getLanguage(), self.getTwitterLanguage(), self.getUsername(), self.getText()))

    @classmethod
    def createFromRawGnipActivity(cls, activity):
        res = GnipActivityTweet(activity)
        res.normalize()
        return res
    
    def getText(self):
        pass

    def getUsername(self):
        pass
    
    def getCreatedDate(self):
        pass
    
    def applyBrandClassifiers(self, bc):
        pass

    def applyTopicClassifiers(self, tcs):                            
        pass

    def getMatchedCampaignIds(self):
        pass
                            
    def getDictToSave(self):
        pass
    
class GnipActivityTweet(Tweet):
    
    def __init__(self, activity):
        Tweet.__init__(self)
        self.d = activity
        
    def normalize(self): #should only be called for activities that came directly from gnip, not from mongodb
        self.d['x_created_at'] = datetime.strptime(self.d['postedTime'], "%Y-%m-%dT%H:%M:%S.%fZ")

    def getUsername(self):
        return self.d['actor']['displayName']

    def getText(self):
        return self.d['body']
        
    def getCreatedDate(self):
        return self.d['x_created_at']
    
    def applyBrandClassifiers(self, bc):
        pass
    
    def getLanguage(self):
        return self.getTwitterLanguage()

    def getGnipLanguage(self):
        try:
            return self.d['gnip']['language']['value']
        except KeyError, e:
            return ''
        
    def getTwitterLanguage(self):
        try:
            return self.d['twitter_lang']
        except KeyError, e:
            return ''
        
    def applyBrandClassifiers(self, bcs):
        pms = {}
        for bc in bcs:
            if not bc.campaign_id in pms: pms[bc.campaign_id] = []
            pms[bc.campaign_id].extend([pm.getDictionary() for pm in bc.extract(self.getText())])
        for cid in pms.keys():
            extracted_infos = pms.get(cid, [])
            if extracted_infos:
                extracted_infos.sort(key=lambda x: x['confidence'], reverse=True)
                if extracted_infos[0]['confidence'] > 0:
                    self.d['x_extracted_info'] = extracted_infos
                            
    def applyTopicClassifiers(self, tcs):                            
        #solo aplico topics para las campañas que hayan matcheado el tweet y tengan x_extracted_info
        for extracted_info in self.d.get('x_extracted_info', []):
            cid = extracted_info['campaign_id']
            tms = []
            for topic_id, topic_classiffier in tcs.get(cid, {}).items():
                tm = topic_classiffier.extract(self.getText())
                if tm: tms.append(tm.getDictionary())
            if tms: tms.sort(key=lambda x: x['confidence'], reverse=True)
            self.d['x_extracted_topics'] = tms                            


    def getMatchedCampaignIds(self):
        return [self.d.get('x_extracted_info', []).keys()]
                            

    def getExtractedInfo(self):
        return self.d.get('x_extracted_info', [])
    
    def getExtractedTopics(self):
        return self.d.get('x_extracted_topics', [])    
    
    def getDictToSave(self):
        return self.d