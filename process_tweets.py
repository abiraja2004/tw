from pymongo import MongoClient
from brandclassifier import BrandClassifier
from datetime import datetime
import re
mclient = MongoClient()
tweetsdb = mclient['unilever']


def process_tweets():
    process_version = 1
    
    query = {"$or": [{"x_process_version": {"$exists": False}}, {"x_process_version": {"$lt": process_version}}]}
    process_version = 1
    tweets_count = tweetsdb.tweets.find(query).count()
    tweets = tweetsdb.tweets.find(query)
    c = 0
    for tweet in tweets:
        c = c+1
        tweet['x_process_version'] = process_version
        tweet['x_created_at'] = datetime.strptime(tweet['created_at'], "%a %b %d %H:%M:%S +0000 %Y")
        tweetsdb.tweets.save(tweet)
        print "%s/%s (%.0f%%)" % (c,tweets_count, (100.0 * c/tweets_count))
        


process_tweets()