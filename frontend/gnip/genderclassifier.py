import re
from pprint import pprint
from mongo import MongoManager
from datetime import datetime, timedelta


class GenderClassifier(object):

    cached_names_database = {}

    @classmethod
    def getNamesDatabase(cls, **kwargs):
        max_age = kwargs.get('max_age', timedelta(seconds=0))
        if not max_age or not cls.cached_names_database or (datetime.now() - cls.cached_names_database['fetch_time'] > max_age):
            namesdb = MongoManager.find("gender_names")
            res = {}
            for name in namesdb:
                res[name["name"].lower()] = name["gender"]
            cls.cached_names_database = {'data': res, 'fetch_time': datetime.now()}
        return cls.cached_names_database['data']


    @classmethod
    def extractGender(cls, name):
        #nname = re.sub(ur'[_]+', u' ', name, flags=re.UNICODE)
        nname = re.sub(ur'[_\-\.]', u' ', name)
        nname = re.sub(ur'[^\w ]+', u'', nname)
        words = [w.lower() for w in name.split() if len(w) > 1]
        names = cls.getNamesDatabase(max_age = timedelta(seconds=300)) #5 minutes
        k = 100
        M = 0
        F = 0
        for w in words:
            g = names.get(w, "U")
            if g == "M": M += k
            elif g == "F": F += k
            k -=1
        if M+F == 0: return "U"
        if M>F: return "M"
        return "F"



if __name__ == "__main__":
    print GenderClassifier.getNamesDatabase()
    tweets = MongoManager.findTweets("tweets_g1", limit=40)
    for t in tweets:
        g = GenderClassifier.extractGender(t.getDisplayName())
        print t.getDisplayName(), g

    for n in ("pablo romina XX", "romina pablo"):
        g = GenderClassifier.extractGender(n)
        print n, g
