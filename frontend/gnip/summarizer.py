#encoding: utf-8
import argparse
from mongo import MongoManager
from pprint import pprint
from datetime import datetime, timedelta
import time
import numbers
from collections import Counter
from copy import deepcopy
import re
import sys

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

    global_trend_stop_words = {}
    
    @classmethod
    def getGlobalTrendStopWords(cls, language,  **kwargs):
        max_age = kwargs.get('max_age', timedelta(seconds=0))
        if not max_age or not cls.global_trend_stop_words.get(language, None) or (datetime.now() - cls.global_trend_stop_words[language]['fetch_time'] > max_age):
            cls.global_trend_stop_words[language] = {'data': set(MongoManager.getGlobalTrendStopWords(language)['words']), 'fetch_time': datetime.now()}
        return cls.global_trend_stop_words[language]['data']

    def getCurrentSummarizationEnd(self):
        end = datetime.utcnow()
        if end.minute < 7: end = end - timedelta(hours=1)
        end = end.replace(minute=0, second=0, microsecond=0)
        return end
    
    def clearSummarization(self, campaign):
        MongoManager.remove('summarized_tweets_%s' % campaign.getId())
        
    def start(self, **kwargs):
        only_campaign= kwargs.get('campaign', None)
        regenerate_all = kwargs.get('regenerate', False)
        while True:
            end = self.getCurrentSummarizationEnd()
            for account in MongoManager.getActiveAccounts(max_age=timedelta(hours=1)):
                for campaign in account.getActiveCampaigns():
                    if only_campaign and only_campaign.getId() != campaign.getId(): continue
                    if regenerate_all:
                        self.clearSummarization(campaign)
                        collection_name = 'tweets_%s' % campaign.getId()
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
    
    def getWordsList(self, text):
        text = re.sub("[:.,(){}!?¿/&%$#]", " ", text)
        return text.split()

    def getTrendWordsSynonyms(self, campaign):
        return {'vende': 'vender', 'vendiendo': 'vender', 'vendo': 'vender'}
    
    def getTrendStopWords(self, campaign):
        return self.__class__.getGlobalTrendStopWords("es", max_age=timedelta(seconds=20))

        
    def summarize(self, campaign, start, end, interval, tweetlist=None):
        collection_name = 'summarized_tweets_%s' % campaign.getId()
        timerange = self.calculateSummarizedIntervals(campaign, start, end, interval, tweetlist)
        for interv in timerange:
            res = MongoManager.findOne(collection_name, filters={'start': start, 'end': end})
            if res: interv['_id'] = res['_id']
            MongoManager.saveDocument(collection_name, interv)

    def calculateSummarizedIntervals(self, campaign, start, end, interval, tweetlist=None):
        pprint("summarizing tweets for campaign %s between %s and %s" % (campaign.getName(), start, end))
        synonyms = self.getTrendWordsSynonyms(campaign)
        trend_stop_words_set = self.getTrendStopWords(campaign)
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
            data['brand'] = SumDict()
            data['product'] = SumDict()
            data['topic'] = SumDict()
            data['words'] = SumDict()
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
                    pms = t.getExtractedInfo()
                    if pms:
                        pm = pms[0]
                        try:
                            interv['brand'][pm['brand']] += 1
                        except KeyError,e: 
                            interv['brand'][pm['brand']] = 1
                        if pm['product']: 
                            p = pm['brand'] + "/" + pm['product']
                            try:
                                interv['product'][p] += 1
                            except KeyError, e:
                                interv['product'][p] = 1                        
                    for k in t.getExtractedTopics():
                        try:
                            interv['topic'][k['topic_name']]['total'] += 1
                        except KeyError, e:
                            interv['topic'][k['topic_name']] = {'total': 1}
                    for word in self.getWordsList(t.getText()):
                        if word in trend_stop_words_set: continue
                        word = word.lower()
                        nword = synonyms.get(word, word)
                        data['words'][nword] = data['words'].get(nword, 0) + 1
        return timerange
    
    def getSummarizedData(self, campaign, start, end):
        collection_name = 'summarized_tweets_%s' % campaign.getId()
        res = MongoManager.find(collection_name, filters={'start': {"$gte": start}, 'end': {"$lte": end}})
        #timerange = [SumDict(r) for r in res]
        timerange = list(res)
        
        if timerange and timerange[-1]['end'] < end:
            d = self.calculateSummarizedIntervals(campaign, timerange[-1]['end'], end, end - timerange[-1]['end'])
            #for k in d:
            #    k['calculated'] = True
            timerange.extend(d)
        #for r in timerange:
        #    print r['start'], r['end'], r['stats']['total_tweets'], r['sentiment'], r.get('calculated', '')
        return timerange

            
    def aggregate(self, campaign, data, group_by):
        def toZero(d):
            for k,v in d.items():
                if isinstance(v, (dict, SumDict)):
                    d[k] = toZero(v)
                elif isinstance(v, numbers.Number):
                    d[k] = 0
            return d

        if group_by == "day":
            params = {"days": 1}
            timeformat = "%Y-%m-%dT00:00:00Z"
        elif group_by == "hour":
            params = {"hours": 1}
            timeformat = "%Y-%m-%dT%H:00:00Z"
        elif group_by == "week":
            params = {"weeks": 1}
            timeformat = "%Y-%m-%dT00:00:00Z"
        delta = timedelta(**params)

        res = SumDict(deepcopy(data[0]))
        start = res['start']
        end = data[-1]['end']
        res = toZero(res)
        res['brand_2'] = {}
        res['product_2'] = {}
        
        for r in data:
            res = res + r
            key = r['start'].strftime(timeformat)
            for sent, q in r['sentiment'].items():
                try:
                    res['sentiment'][sent][key] += r['sentiment'][sent]['total']
                except KeyError,e:
                    if key not in res['sentiment'][sent]: res['sentiment'][sent][key] = r['sentiment'][sent]['total']
            for brand, q in r['brand'].items():
                if not brand in res['brand_2']: res['brand_2'][brand] = {}
                try:
                    res['brand_2'][brand][key] += r['brand'][brand]
                except KeyError,e:
                    if key not in res['brand_2'][brand]: res['brand_2'][brand][key] = r['brand'][brand]
            for product, q in r['product'].items():
                if not product in res['product_2']: res['product_2'][product] = {}
                try:
                    res['product_2'][product][key] += r['product'][product]
                except KeyError,e:
                    if key not in res['product_2'][product]: res['product_2'][product][key] = r['product'][product]
        res['brand'] = res['brand_2']
        del res['brand_2']
        res['product'] = res['product_2']
        del res['product_2']
        res['words'] = SumDict([(x,y) for x,y in res['words'].items() if x not in self.getTrendStopWords(campaign)])
        res['words'] = sorted(res['words'].items(), key=lambda x: (x[1], x[0]),reverse=True)
        res['start'] = start
        res['end'] = end
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
    parser = argparse.ArgumentParser()
    parser.add_argument('--regenerate', action="store_true", default=False)
    parser.add_argument('--account', default=None)
    parser.add_argument('--list', action="store_true", default=False)
    parser.add_argument('--start', default=None)
    parser.add_argument('--end', default=None)
    parser.add_argument('--clear', action="store_true", default=False)
    args, known = parser.parse_known_args()
    campaign = None
    if args.account:
        account = MongoManager.getAccount(name=args.account)
        if not account:
            pprint("Account %s not found" % args.account)
            exit(1)
        campaign = account.getActiveCampaigns()[0]    
    
    summarizer = Summarizer()    
    if not args.list and not args.clear:
        summarizer.start(campaign=campaign, regenerate=args.regenerate)
    elif args.clear and campaign:
        summarizer.clearSummarization(campaign)
    elif campaign and args.start and args.end:
        print args
        start = datetime.strptime(args.start, "%Y-%m-%dT%H")
        end = datetime.strptime(args.end, "%Y-%m-%dT%H")
        records = summarizer.calculateSummarizedIntervals(campaign,start,end,timedelta(hours=1))    
        pprint(records)
        res = summarizer.aggregate(campaign, records, 'day')
        pprint(res)
    exit(0)
