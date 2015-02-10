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
    def createFromMongoDoc(cls, doc):
        res = GnipActivityTweet(doc)
        if not 'user' in doc:  #xq se grabaron inicialmente algunos tweets sin estos campos
            res.d['user'] = {}
            res.d['user']['screen_name'] = res.getUsername()        
            res.d['user']['profile_image_url_https'] = res.getUserProfileImageURL()
        if not 'text' in doc:  #xq se grabaro inicialmente algunos tweets sin estos campos
            res.d['text'] = res.getText()
        if not 'x_coordinates' in doc:
            res.d['x_coordinates'] = {"country": "", "country_code": "", "origin": ""}
        if not 'x_feed_type' in res.d:
            res.d['x_feed_type'] = 'twitter'            
        return res

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
    
    def getUserProfileImageURL(self):
        pass
    
    def getCountryCode(self):
        try:
            return self.d['x_coordinates']['country_code']
        except KeyError, e:
            return ""

    def getCountryName(self):
        try:
            return self.d['x_coordinates']['country']
        except KeyError, e:
            return ""
    
class GnipActivityTweet(Tweet):
    
    def __init__(self, activity):
        Tweet.__init__(self)
        self.d = activity
        
    def normalize(self): #should only be called for activities that came directly from gnip, not from mongodb
        self.d['x_created_at'] = datetime.strptime(self.d['postedTime'], "%Y-%m-%dT%H:%M:%S.%fZ")
        self.d['x_feed_type'] = 'twitter'
        self.d['user'] = {}
        self.d['user']['screen_name'] = self.getUsername()
        self.d['user']['profile_image_url_https'] = self.getUserProfileImageURL()
        self.d['text'] = self.getText()
        self.d['favorite_count'] = self.getFavoritesCount()
        self.d['retweet_count'] = self.getRetweetsCount()
        self.d['x_coordinates'] = {}
        try:
            self.d['x_coordinates']['country_code'] = self.d['location']['twitter_country_code'].lower()
            self.d['x_coordinates']['country'] = self.d['location']['country_code']
            self.d['x_coordinates']['origin'] = "place"
        except KeyError, e:
            try:
                self.d['x_coordinates']['country_code'] = self.d['gnip']['profileLocations'][0]['address']['countryCode'].lower()
                self.d['x_coordinates']['country'] = self.d['gnip']['profileLocations'][0]['address']['country'].lower()
                self.d['x_coordinates']['origin'] = "user.location"
            except IndexError, e:
                pass
            except KeyError, e:
                pass
        

    def getUsername(self):
        try:
            return '@'+self.d['actor']['preferredUsername']
        except KeyError, e:
            return '@'+self.d['user']['screen_name']

    def getText(self):
        try:
            return self.d['body']
        except KeyError, e:
            return self.d['text']
            
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
        
    def getSentiment(self):
        return self.d.get("x_sentiment", '')
    
    def setSentiment(self, s):
        self.d['x_sentiment'] = s

    def getMatchedCampaignIds(self):
        return [self.d.get('x_extracted_info', []).keys()]

    def resetFollowAccountsMentionCount(self):
        self.d['x_mentions_count'] = {}
                            
    def getFollowAccountsMentionCount(self):
        return self.d.get('x_mentions_count', {})

    def setFollowAccountsMentionCount(self, username, cnt):
        try:
            self.d['x_mentions_count'][username] = cnt
        except KeyError, e:
            self.d['x_mentions_count'] = {username: cnt}
        
    def getExtractedInfo(self):
        return self.d.get('x_extracted_info', [])

    def setExtractedInfo(self, pms):
        self.d['x_extrated_info'] = pms
    
    def getExtractedTopics(self):
        return self.d.get('x_extracted_topics', [])    
    
    def setExtractedTopics(self, tms):
        self.d['x_extrated_topics'] = tms
        
    def getUserProfileImageURL(self):
        return self.d.get('actor', {}).get('image', '')
    
    def getDictionary(self):
        return self.d
    
    def getHashtags(self):
        hts = self.d.get('twitter_entities', {}).get('hashtags', [])
        return set(["#"+x['text'] for x in hts])
    
    def getUserMentions(self):
        um = self.d.get('twitter_entities', {}).get('user_mentions', [])
        return dict([('@' + x['screen_name'], x['name']) for x in um])
    
    def getFavoritesCount(self):
        return self.d.get('favoritesCount', 0)
    
    def getRetweetsCount(self):
        return self.d.get('retweetCount', 0)    