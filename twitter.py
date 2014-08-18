import twython
from twython import TwythonStreamer
import threading
from time import strptime 
from time import mktime
from datetime import datetime





class Twitter:
    #TEST KEYS
    TWITTER_ADDRESS = "@TestProdeBr2014"
    CONSUMER_KEY = "1qxRMuTzu2I7BP7ozekfRw"
    CONSUMER_SECRET = "whQFHN8rqR78L6su6U32G6TPT7e7W2vCouR4inMfM"
    ACCESS_TOKEN = "2305874377-TTmvLjLuP8aq8q2bT7GPJsOjG9n6uYLAA0tvsYU"
    ACCESS_KEY = "iy4SYpkHK26Zyfr9RhYSGOLVtd9eMNF6Ebl2p552gF4vL"
    twitter = None
    credentials = None
    all_my_tweets = None
    

    @classmethod
    def getTwitter(cls):
        if cls.twitter is None:
            cls.twitter = twython.Twython(Twitter.CONSUMER_KEY, Twitter.CONSUMER_SECRET, Twitter.ACCESS_TOKEN, Twitter.ACCESS_KEY)
        return cls.twitter
        
    @classmethod
    def getMyCredentials(cls):
        if cls.credentials is None:
            cls.credentials = cls.getTwitter().verify_credentials()    
        return cls.credentials
        
    @classmethod
    def sign_in_url(cls, request):
        twitter = twython.Twython(Twitter.CONSUMER_KEY, Twitter.CONSUMER_SECRET)
        ks = '0'
        if 'keep_me_signed_in' in request.GET and request.GET['keep_me_signed_in'].lower() in ('on','true','1'): ks = '1'
        auth = twitter.get_authentication_tokens(callback_url=getServerURL(request) + '/twitter/callback?ks=' + ks)
        url = auth['auth_url']
        request.session['twitter_authentication_token'] = auth['oauth_token']
        request.session['twitter_authentication_token_secret'] = auth['oauth_token_secret']
        return url

    
    @classmethod
    def sign_in_callback(cls, request):
        if request.GET['oauth_token'] == request.session['twitter_authentication_token']:
            twitter = twython.Twython(Twitter.CONSUMER_KEY, Twitter.CONSUMER_SECRET, request.session['twitter_authentication_token'],request.session['twitter_authentication_token_secret'])
            auth = twitter.get_authorized_tokens(request.GET['oauth_verifier'])
            request.session['twitter_access_token'] = auth['oauth_token']
            request.session['twitter_access_token_secret'] = auth['oauth_token_secret']
        else:
            raise "error en token login twitter"

    @classmethod
    def verify_credentials(cls, request):
        twitter = twython.Twython(Twitter.CONSUMER_KEY, Twitter.CONSUMER_SECRET, request.session['twitter_access_token'], request.session['twitter_access_token_secret'])
        return twitter.verify_credentials()
            
    @classmethod
    def post(cls, msg):
        return cls.getTwitter().update_status(status=msg)
        
    @classmethod
    def home_timeline(cls):
        return cls.getTwitter().get_home_timeline()

    @classmethod
    def getAllMyTweets(cls):    
        if cls.all_my_tweets is None:
            print "FETCHING ALL TWEETS FROM TWITTER", "*"*20
            chunk = 200
            tweets = cls.getTwitter().get_home_timeline(count=chunk)
            cls.all_my_tweets = tweets[:]
            while len(tweets) == chunk:
                tweets = cls.getTwitter().get_home_timeline(count=chunk, max_id = tweets[-1]['id']-1)
                cls.all_my_tweets.extend(tweets[:])
            for tweet in cls.all_my_tweets:
                tweet = processTweet(tweet)
            MyThread().start() #inicio el streamer de tweets para empezar a recibir los twitter que salgan ahora.                
        else:
            print "FETCHING ALL TWEETS FROM BUFFER", "*"*20
        return cls.all_my_tweets
        
    @classmethod
    def retweet(cls,tweet_id):
        return cls.getTwitter().retweet(id=tweet_id)


def processTweet(tweet):
    tweet['date'] = getDateTime(tweet['created_at'])                
    if not tweet['retweeted']:
        tweet['original_user'] = tweet['user']
        tweet['original_text'] = tweet['text']
    else:
        tweet['original_user'] = tweet['retweeted_status']['user']
        tweet['original_text'] = tweet['retweeted_status']['text'].replace(Twitter.TWITTER_ADDRESS + " ", "").replace(Twitter.TWITTER_ADDRESS, "")
    return tweet
    
def getDateTime(created_at):
    p = strptime(created_at, "%a %b %d %H:%M:%S +0000 %Y")
    return datetime.fromtimestamp(mktime(p))        
    

class MyStreamer(TwythonStreamer):
    def on_success(self, data):
        if 'text' in data and 'user' in data and 'id' in data: #esto parece ser un tweet
            if data['user']['id'] == Twitter.getMyCredentials()['id']: #tweet mio
                if data['id'] not in [tweet['id'] for tweet in Twitter.all_my_tweets]:
                    data = processTweet(data)
                    Twitter.all_my_tweets = [data] + Twitter.all_my_tweets
                #print "tweet mio: ", data['text'].encode('latin1', errors='ignore')
            else: 
                #print "tweet de %s: "% data['user']['screen_name'], data['text'].encode('latin1', errors='ignore')
                print "retweeteando..."
                Twitter.retweet(data['id'])

    def on_error(self, status_code, data):
        print status_code

        # Want to stop trying to get data because of the error?
        # Uncomment the next line!
        # self.disconnect()



class MyThread(threading.Thread):
    def run(self):
        stream = MyStreamer(Twitter.CONSUMER_KEY, Twitter.CONSUMER_SECRET, Twitter.ACCESS_TOKEN, Twitter.ACCESS_KEY)
        stream.user()

if __name__ == "__main__":
    for tweet in Twitter.getAllMyTweets():
    	pass
        #print tweet['user']['screen_name']+ ": "+tweet['text']
else:
    pass
    #MyThread().start()