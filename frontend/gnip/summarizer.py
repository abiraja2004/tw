from mongo import MongoManager
from pprint import pprint
from datetime import datetime, timedelta
import time
import numbers
from collections import Counter
from copy import deepcopy

class SumDict(dict):
    
    def __add__(self, o):
        res = SumDict()
        for k in set(o.keys()) | set(self.keys()):
            #if self[k].__class__ == o[k].__class__:
            if k in self:
                if k in o:
                    if isinstance(self[k], (numbers.Number, self.__class__)): res[k] = self[k] + o[k]
                    elif isinstance(self[k], dict): res[k] = SumDict(self[k]) + o[k]
                else:
                    if isinstance(self[k], (numbers.Number, self.__class__)): res[k] = self[k]
                    elif isinstance(self[k], dict): res[k] = SumDict(self[k])
            else:
                if isinstance(o[k], (numbers.Number, self.__class__)): res[k] = o[k]
                elif isinstance(o[k], dict): res[k] = SumDict(o[k])
               
        return res
            
class Summarizer(object):

    def getCurrentSummarizationEnd(self):
        end = datetime.utcnow()
        if end.minute < 15: end = end - timedelta(hours=1)
        end = end.replace(minute=0, second=0, microsecond=0)
        return end
    
    def start(self, only_campaign=None, regenerate_all=False):
        
        while True:
            end = self.getCurrentSummarizationEnd()
            for account in MongoManager.getActiveAccounts(max_age=timedelta(hours=1)):
                for campaign in account.getActiveCampaigns():
                    if only_campaign and only_campaign.getId() != campaign.getId(): continue
                    if regenerate_all:
                        collection_name = 'tweets_%s' % campaign.getId()
                        MongoManager.remove('summarized_tweets_%s' % campaign.getId())
                        res = MongoManager.findTweets(collection_name, sort=("x_created_at", 1), limit=1)
                        if res.count():
                            lsd = res[0]['x_created_at'].replace(minute=0, second=0, microsecond=0)
                        else:
                            lsd = datetime.now().replace(minute=0, second=0, microsecond=0)
                    else:
                        lsd = self.getLastSummarizedDate(campaign)
                    if lsd < end:
                        while lsd < end:
                            self.summarize(campaign, lsd, min(end, lsd + timedelta(days=1)), timedelta(hours=1), None)
                            lsd = lsd + timedelta(days=1)
            pprint("sleeping 30 minutes")        
            time.sleep(1800)

    
    def getLastSummarizedDate(self, campaign):
        collection_name = 'summarized_tweets_%s' % campaign.getId()
        res = MongoManager.find(collection_name, sort=("start", -1), limit=1)
        if res.count():
            return res[0]['end']
        else:
            collection_name = 'tweets_%s' % campaign.getId()
            res = MongoManager.findTweets(collection_name, sort=("x_created_at", 1), limit=1)
            if res.count():
                return res[0]['x_created_at'].replace(minute=0, second=0, microsecond=0)
            return datetime.now().replace(minute=0, second=0, microsecond=0)

    
    
        
    def summarize(self, campaign, start, end, interval, tweetlist=None):
        collection_name = 'summarized_tweets_%s' % campaign.getId()
        timerange = self.calculateSummarizedIntervals(campaign, start, end, interval, tweetlist)
        for interv in timerange:
            res = MongoManager.findOne(collection_name, filters={'start': start, 'end': end})
            if res: interv['_id'] = res['_id']
            MongoManager.saveDocument(collection_name, interv)

    def calculateSummarizedIntervals(self, campaign, start, end, interval, tweetlist=None):
        pprint("summarizing tweets for campaign %s between %s and %s" % (campaign.getName(), start, end))
        collection_name = 'summarized_tweets_%s' % campaign.getId()
        if tweetlist is None:
            tweetlist = MongoManager.findTweets("tweets_%s" % campaign.getId(), filters={"retweeted_status": {"$exists": False}, "x_created_at": {"$gte": start, "$lte": end}})
        own_fa = campaign.getOwnFollowAccounts()
        timerange = []
        d = start
        while d < end:
            data = SumDict({'start': d, 'end': d+interval})
            data['stats'] = SumDict()
            data['stats']['total_tweets'] = 0
            data['stats']['own_tweets'] = SumDict({'total': 0, 'accounts': SumDict([(a,0) for a in own_fa])})
            data['stats']['own_tweets']['retweets']  = SumDict({'total': 0, 'accounts': SumDict([(a,0) for a in own_fa])})
            data['stats']['own_tweets']['favorites']  = SumDict({'total': 0, 'accounts': SumDict([(a,0) for a in own_fa])})
            data['stats']['mentions']  = SumDict({'total': 0, 'accounts': SumDict([(a,0) for a in own_fa])})
            data['sentiment'] = SumDict()
            timerange.append(data)
            d = d + interval
            
        for t in tweetlist:
            for interv in timerange:
                if t.getCreatedDate() >= interv['start'] and t.getCreatedDate() < interv['end']:
                    interv['stats']['total_tweets'] += 1
                    if t.getUsername() in own_fa:
                        interv['stats']['own_tweets']['total'] += 1
                        interv['stats']['own_tweets']['accounts'][t.getUsername()] += 1                    
                        interv['stats']['own_tweets']['retweets']['total'] += t.getRetweetsCount()
                        interv['stats']['own_tweets']['retweets']['accounts'][t.getUsername()] += t.getRetweetsCount()
                        interv['stats']['own_tweets']['favorites']['total'] += t.getFavoritesCount()
                        interv['stats']['own_tweets']['favorites']['accounts'][t.getUsername()] += t.getRetweetsCount()
                    for k,v in t.getFollowAccountsMentionCount().items():
                        if k in own_fa:
                            interv['stats']['mentions']['total'] += 1
                            interv['stats']['mentions']['accounts'][k] += 1
                    if t.getSentiment():
                        if not t.getSentiment() in interv['sentiment']: interv['sentiment'][t.getSentiment()] = {"total": 0}
                        interv['sentiment'][t.getSentiment()]['total'] += 1
        return timerange
    
    def getSummarizedData(self, campaign, start, end):
        collection_name = 'summarized_tweets_%s' % campaign.getId()
        res = MongoManager.find(collection_name, filters={'start': {"$gte": start}, 'end': {"$lte": end}})
        #timerange = [SumDict(r) for r in res]
        timerange = list(res)
        if timerange and timerange[-1]['end'] < end:
            d = self.calculateSummarizedIntervals(campaign, timerange[-1]['end'], end, end - timerange[-1]['end'])
            for k in d:
                k['calculated'] = True
            timerange.extend(d)
        for r in timerange:
            print r['start'], r['end'], r['stats']['total_tweets'], r.get('calculated', '')
        
        return timerange

            
    def aggregate(self, data):
        def toZero(d):
            for k,v in d.items():
                if isinstance(v, (dict, SumDict)):
                    d[k] = toZero(v)
                elif isinstance(v, numbers.Number):
                    d[k] = 0
            return d

        res = SumDict(deepcopy(data[0]))
        res = toZero(res)
        
        for r in data:
            res = res + r
        return res
        """
        res={}
        if isinstance(data, list):
            for r in data:
                for k, v in r.items():
                    if isinstance(v, numbers.Number):
                        if k not in res: res[k] = 0
                        res[k] += v
                        print k,v
                    if isinstance(v, dict): 
                        m[k] for m in data
                        res[k] = self.aggregate(m[k] for m in data)
        elif isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, numbers.Number):
                    if k not in res: res[k] = 0
                    res[k] += v
                if isinstance(v, dict): res[k] = self.aggregate(data[k])
        return res
        """

            
    


if __name__ == '__main__':
    campaign = MongoManager.getAccount(name='IAE').getActiveCampaigns()[0]
    summarizer = Summarizer()
    summarizer.start(campaign, True)
    exit(0)
    #d = SumDict({'a': 1, 'b':2, 'c': 'pablo', 'd': SumDict({'aa': 4})})
    #d2 = SumDict({'a': 10, 'b':20, 'c': 'pablo', 'd': SumDict({'aa': 40})})
    #pprint(summarizer.aggregate([d,d2]))
    #exit(0)
    
    
    records = summarizer.getSummarizedData(campaign, datetime(2014,12,1,0), datetime(2014,12,2,0))
    #pprint(records)
    r = summarizer.aggregate(records)
    pprint(r)
    print campaign.getId()
    #summarizer.start()
    """
    print summarizer.getCurrentSummarizationEnd()
    
    
    pprint(summarizer.getLastSummarizedDate(campaign))
    
    summarizer.summarize(MongoManager.getAccount(name='Sony').getActiveCampaigns()[0], datetime(2015,1,8,0), datetime(2015,1,8,1), timedelta(hours=1), None)
    
    """