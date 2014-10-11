#encoding: utf-8
from twython import Twython
from pymongo import MongoClient, DESCENDING
from bson import ObjectId
from bson.json_util import dumps
from flask import Flask, render_template, request, Blueprint, redirect, url_for
from rulesmanager import getBrandClassifiers
import flask 
import json
import re
from datetime import datetime, timedelta
import time
from oauth2client.client import OAuth2WebServerFlow, Credentials, AccessTokenRefreshError
from apiclient.discovery import build
import analytics_api
import httplib2
import hashlib
from base64 import b64encode, b64decode

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--auth', action="store_true", default=False)
args = parser.parse_args()
dbuser = "monitor"
dbpasswd = "monitor678"
mclient = MongoClient()
tweetdb = mclient['unilever']

PASSWORD_SALT = "relatos salvajes"

SERVER_LOCAL=0
SERVER_REMOTE=1
server_mode = SERVER_LOCAL
server_domain = "localhost"
if args.auth:
    tweetdb.authenticate(dbuser, dbpasswd)
    server_mode = SERVER_REMOTE
    server_domain = "www.nuev9.com"
    
accountdb = mclient['monitor']
if args.auth:
    accountdb.authenticate(dbuser, dbpasswd)


app = Flask(__name__, template_folder='html')

def onRemoteServer():
    return server_mode == SERVER_REMOTE

def onLocalServer():
    return server_mode == SERVER_LOCAL

"""
@app.route('/')
def root():
    return redirect(url_for('login'))
"""

def getPasswordHash(user, psw):
    return hashlib.md5(user + psw + PASSWORD_SALT).hexdigest()
        
@app.route('/login', methods=["GET", "POST"])
def login():    
    if request.method == "GET":
        return render_template("login.html")
    elif request.method == "POST":
        user = request.form["user"]
        password = request.form["password"]
        passwordhash = getPasswordHash(user, password)
        acc = accountdb.accounts.find({"users.%s" % user: {"$exists": True}})
        msg = ""
        if not acc.count():
            msg = "El usuario y/o clave son incorrectos"
            return render_template("login.html", user=user, msg=msg)
        else:
            pass
        
        
            
            
@app.route('/')
@app.route('/app')
@app.route('/sivale')
@app.route('/gm')
def home():
    account_id = request.args.get("account_id", "53ff7ae51e076582a6fb7f12") #default: Prueba
    campaign_id = request.args.get("campaign_id", "5400d1902e61d70aab2e9bdf") #default Campana unilever
    logo = "logo.jpg"
    logo2 = None
    if request.path == "/sivale":
        account_id = "5410f47209109a09a2b5985b"  #SiVale account_id
        campaign_id = "5410f5a52e61d7162c700232"  #SiVale campaign_id   
        logo = "logoSivale.jpg"
        logo2 = "logoLumia.jpg"
    elif request.path == "/gm":
        account_id = "54189900d06625fc47e54b76" #general motors
        campaign_id = "54189b93d06625fc47e54b78" 
    account = accountdb.accounts.find_one({"_id":ObjectId(account_id)})
    template = "index.html"
    dashtemplate = "dashboard.html"
    if request.path == "/app" or request.path == "/sivale" or request.path == "/gm":
        template = "app.html"
        dashtemplate = "dashboard_app.html"
    custom_css= request.args.get("css", None)
    print logo
    has_products = False
    own_brands_list = []
    for bid, brand in account['campaigns'][campaign_id]['brands'].items():
        if brand['own_brand']: own_brands_list.append(brand['name'])
        if len(account['campaigns'][campaign_id]['brands'][bid]['products']):
            has_products = True
            break
    return render_template(template, custom_css = custom_css, content_template=dashtemplate, js="dashboard.js", account=account, campaign_id = campaign_id, campaign=account['campaigns'][campaign_id], logo=logo, logo2 = logo2, has_products = has_products, own_brands_list = '|'.join(own_brands_list))            

@app.route('/campaign')
def campaigns():
    campaign_id = request.args.get("campaign_id", "5400d1902e61d70aab2e9bdf") #default Campana unilever
    account = accountdb.accounts.find_one({"campaigns.%s" % campaign_id: {"$exists": True}})
    custom_css= request.args.get("css", None)
    FLOW = OAuth2WebServerFlow(client_id='442071031907-0ce0m652985ra8030e9n8nfrogk5o6tr.apps.googleusercontent.com',
                           client_secret='43Bf_67s6E9PXIJe4ZY5fUSC',
                           scope='https://www.googleapis.com/auth/analytics.readonly',
                           redirect_uri='http://%s:5001/oauth2callback' % server_domain)    
    analytics_credentials = None
    analytics_profiles = []
    analytics_access =False
    if 'analytics' in account['campaigns'][campaign_id]:
        http = httplib2.Http()
        analytics_credentials = Credentials.new_from_json(account['campaigns'][campaign_id]["analytics"]["credentials"])
        print "CREDENTIAL STATUS", analytics_credentials.invalid, analytics_credentials.access_token_expired, analytics_credentials.token_expiry
        print FLOW.step1_get_authorize_url()+ "&state=" + b64encode("%s,%s" % (campaign_id,account['_id']))
        #if analytics_credentials.access_token_expired:
        #    print "REFRESH:", analytics_credentials.refresh(http)
        print "CREDENTIAL STATUS", analytics_credentials.invalid, analytics_credentials.access_token_expired, analytics_credentials.token_expiry
        print dir(FLOW)
        
        if not analytics_credentials.access_token_expired:
            try:
                http = analytics_credentials.authorize(http)
                service = build('analytics', 'v3', http=http)
                print dir(service)
                analytics_profiles = analytics_api.get_all_profiles(service)
                analytics_access = True
            except AccessTokenRefreshError:
                pass
    analytics_auth_url = FLOW.step1_get_authorize_url()+ "&state=" + b64encode("%s,%s" % (campaign_id,account['_id']))
    print FLOW.revoke_uri
    analytics_revoke_url = ""
    if analytics_credentials:
        analytics_revoke_url = FLOW.revoke_uri + "?token=%s" % analytics_credentials.access_token
    campaign = account['campaigns'][campaign_id]        
    if not 'polls' in campaign: campaign['polls'] = {}
    if not 'datacollections' in campaign: campaign['datacollections'] = {}
    return render_template('app.html', custom_css = custom_css, content_template="campaign.html", js="campaign.js", account=account, campaign_id = campaign_id, campaign=campaign, analytics_auth_url = analytics_auth_url, analytics_profiles=analytics_profiles, analytics_access = analytics_access, analytics_revoke_url= analytics_revoke_url)

@app.route('/sentiment')
def sentiment():
    campaign_id = request.args.get("campaign_id", "5400d1902e61d70aab2e9bdf") #default Campana unilever
    account = accountdb.accounts.find_one({"campaigns.%s" % campaign_id: {"$exists": True}})
    campaign_id = request.args.get('campaign_id')
    custom_css= request.args.get("css", None)
    return render_template('app.html', custom_css = custom_css, content_template="sentiment.html", js="sentiment.js", account=account, campaign_id = campaign_id, campaign=account['campaigns'][campaign_id])

@app.route('/keywordsets')
def keywordsets():
    campaign_id = request.args.get("campaign_id", "5400d1902e61d70aab2e9bdf") #default Campana unilever
    account = accountdb.accounts.find_one({"campaigns.%s" % campaign_id: {"$exists": True}})
    campaign_id = request.args.get('campaign_id')    
    keywordsets = accountdb.keywordset.find({})
    custom_css= request.args.get("css", None)
    return render_template('app.html', custom_css = custom_css, content_template="keywordsets.html", js="keywordset.js", keywordsets = list(keywordsets), account=account, campaign_id = campaign_id, campaign=account['campaigns'][campaign_id])

@app.route('/topics')
def topics():
    campaign_id = request.args.get("campaign_id", "5400d1902e61d70aab2e9bdf") #default Campana unilever
    account = accountdb.accounts.find_one({"campaigns.%s" % campaign_id: {"$exists": True}})
    campaign_id = request.args.get('campaign_id')    
    topics = accountdb.topic.find({})
    custom_css= request.args.get("css", None)
    return render_template('app.html', custom_css = custom_css, content_template="topics.html", js="topic.js", topics = list(topics), account=account, campaign_id = campaign_id, campaign=account['campaigns'][campaign_id])

@app.route('/<path:filename>')
def send_js(filename):
    return flask.send_from_directory('html', filename)


@app.route('/js/<path:filename>')
def js_folder(filename):
    return flask.send_from_directory(app.root_path + '/js/', filename)

@app.route('/img/<path:filename>')
def img_folder(filename):
    return flask.send_from_directory(app.root_path + '/img/', filename)

@app.route('/css/<path:filename>')
def css_folder(filename):
    return flask.send_from_directory(app.root_path + '/css/', filename)

@app.route('/fonts/<path:filename>')
def fonts_folder(filename):
    return flask.send_from_directory(app.root_path + '/fonts/', filename)


@app.route('/api/objectid/new')
def objectid_new():
    return str(ObjectId())
    
@app.route('/api/tweets/list')
def tweets_list():
    start = request.args.get("start", "")
    end = request.args.get("end", "")
    page = int(request.args.get('page',"1"))-1
    tweets_per_page = int(request.args.get('tpp',"20"))
    campaign_id = request.args.get("campaign_id", "")
    brands_to_include = request.args.get("brands_to_include", "")
    include_sentiment_tagged_tweets = bool(request.args.get("include_sentiment_tagged_tweets", "true") == "true")
    res = {"tweets": [], "mentions": 0}
    if start and end and campaign_id:
        collection_name = "tweets_%s" % campaign_id
        print collection_name
        start = datetime.strptime(start + " 00:00:00", "%Y-%m-%d %H:%M:%S")
        end = datetime.strptime(end + " 23:59:59", "%Y-%m-%d %H:%M:%S")
        docfilter = { "retweeted_status": {"$exists": False}, "x_created_at": {"$gte": start, "$lte": end}}
        if not include_sentiment_tagged_tweets: docfilter['x_sentiment'] = {"$exists": False}
        dbtweets = accountdb[collection_name].find(docfilter).sort("x_created_at", -1).skip(page*tweets_per_page).limit(tweets_per_page) 
        if not brands_to_include:
            res['tweets'].extend(dbtweets)
        else:
            bti = [x.strip() for x in brands_to_include.split("|") if x.strip()]
            for t in dbtweets:
                if 'x_extracted_info' in t and [pm for pm in t['x_extracted_info'] if pm['brand'] in bti]:
                    res['tweets'].append(t)
    return flask.Response(dumps(res),  mimetype='application/json')

@app.route('/api/tweets/tag/sentiment', methods=['POST'])
def tweets_tag_sentiment():
    sent = request.form["sentiment"]
    tweet_id = request.form["tweet_id"]
    campaign_id = request.form["campaign_id"]
    res = []
    if sent and tweet_id and campaign_id:
        collection_name = "tweets_%s" % campaign_id
        accountdb[collection_name].update({"_id": ObjectId(tweet_id)}, {"$set": {"x_sentiment": sent}}); 
        return "OK"
    return "ERROR"

@app.route('/api/tweets/count')
def tweets_count():
    start = request.args.get("start", "")
    end = request.args.get("end", "")
    group_by = request.args.get("group_by", "day")
    account_id = request.args.get("account_id", "")
    campaign_id = request.args.get("campaign_id", "")
    brands_to_include = request.args.get("brands_to_include", "")
    res = {'timerange': []}
    if start and end and campaign_id:
        account = getAccount(account_id)
        accs = getCampaignFollowAccounts(account, campaign_id)
        collection_name = "tweets_%s" % campaign_id
        bti = [x.strip() for x in brands_to_include.split("|") if x.strip()]
        start = datetime.strptime(start + "T00:00:00", "%Y-%m-%dT%H:%M:%S")
        end = datetime.strptime(end + "T23:59:59", "%Y-%m-%dT%H:%M:%S")
        timerange = []
        params = {}
        timeformat = ""
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
        d = start
        while d <= end:
            timerange.append(d.strftime("%Y-%m-%dT%H:00:00Z"))
            d = d + delta
        res['timerange'] = timerange
        dbtweets = accountdb[collection_name].find({ "retweeted_status": {"$exists": False}, "x_created_at": {"$gte": start, "$lte": end}})
        res['brand'] = {}
        res['product'] = {}
        res['sentiment'] = {}
        res['polls'] = {}
        res['datacollections'] = {}
        res['stats'] = {}
        res['stats']['own_tweets'] = {'total': 0, 'accounts': dict([(a,0) for a in accs])}
        res['stats']['own_tweets']['retweets'] = {'total': 0, 'accounts': dict([(a,0) for a in accs])}
        res['stats']['own_tweets']['favorites'] = {'total': 0, 'accounts': dict([(a,0) for a in accs])}
        res['stats']['total_tweets'] = 0
        res['stats']['mentions'] = {'total': 0, 'accounts': dict([(a,0) for a in accs])}

        polls = {}
        if 'polls' in account['campaigns'][campaign_id]:
            polls = account['campaigns'][campaign_id]['polls']
        poll_hashtags = {}
        for poll_id, poll in polls.items():
            poll['data'] = {}
            for ht in poll['hashtags'].split(","):
                ht = ht.strip()
                if not ht: continue
                if not ht in poll_hashtags: poll_hashtags[ht] = []
                poll_hashtags[ht].append(poll_id)
                poll['data'][ht] = {'total': 0}
            res['polls'][poll_id] = poll
        
        datacollections = {}
        if 'datacollections' in account['campaigns'][campaign_id]:
            datacollections = account['campaigns'][campaign_id]['datacollections']

        for datacollection_id, datacollection in datacollections.items():
            datacollection['data'] = {}
            for field in datacollection['fields']:
                datacollection['data'][field['name']] = {}
            
            for dcitem in accountdb['datacollection_%s' % datacollection_id].find({}): #habria que filtrar por fecha??
                for field in datacollection['fields']:
                    if field['type'] != "combobox": continue #por ahora solo cuento los comboboxes
                    if field['name'] in dcitem['fields']:
                        if dcitem['fields'][field['name']] not in datacollection['data'][field['name']]:
                            datacollection['data'][field['name']][dcitem['fields'][field['name']]] = {'total': 1}
                        else:
                            datacollection['data'][field['name']][dcitem['fields'][field['name']]]['total'] += 1
            res['datacollections'][datacollection_id] = datacollection    
            
            
        for tweet in dbtweets:
            pms = tweet.get('x_extracted_info', [])
            if brands_to_include:
                if not [pm for pm in pms if pm['brand'] in bti]: continue
            if pms:
                pm = pms[0]
                if not pm['brand'] in res['brand']: res['brand'][pm['brand']] = {}
                d = tweet['x_created_at']
                key = d.strftime(timeformat)
                if not key in res['brand'][pm['brand']]:
                    res['brand'][pm['brand']][key] = 1
                else:
                    res['brand'][pm['brand']][key] += 1   
                if pm['product']: 
                    p = pm['brand'] + "/" + pm['product']
                    if not p in res['product']: res['product'][p] = {}
                    d = tweet['x_created_at']
                    key = d.strftime(timeformat)
                    if not key in res['product'][p]:
                        res['product'][p][key] = 1
                    else:
                        res['product'][p][key] += 1   
            if 'x_sentiment' in tweet:
                if not tweet['x_sentiment'] in res['sentiment']: res['sentiment'][tweet['x_sentiment']] = {"total": 0}
                d = tweet['x_created_at']
                key = d.strftime(timeformat)
                res['sentiment'][tweet['x_sentiment']]['total'] += 1
                if not key in res['sentiment'][tweet['x_sentiment']]:
                    res['sentiment'][tweet['x_sentiment']][key] = 1
                else:
                    res['sentiment'][tweet['x_sentiment']][key] += 1                   
            res['stats']['total_tweets'] += 1                    
            if 'x_mentions_count' in tweet:
                for k,v in tweet['x_mentions_count'].items():
                    if k in accs:
                        res['stats']['mentions']['total'] += 1
                        res['stats']['mentions']['accounts'][k] += 1
            if 'user' in tweet and 'screen_name' in tweet['user']:
                if ('@' + tweet['user']['screen_name']) in accs:
                    res['stats']['own_tweets']['total'] += 1
                    res['stats']['own_tweets']['accounts']['@' + tweet['user']['screen_name']] += 1
                    if 'retweet_count' in tweet:
                        res['stats']['own_tweets']['retweets']['total'] += int(tweet['retweet_count'])
                        res['stats']['own_tweets']['retweets']['accounts']['@' + tweet['user']['screen_name']] += int(tweet['retweet_count'])
                    if 'favorite_count' in tweet:
                        res['stats']['own_tweets']['favorites']['total'] += int(tweet['favorite_count'])
                        res['stats']['own_tweets']['favorites']['accounts']['@' + tweet['user']['screen_name']] += int(tweet['favorite_count'])
            if polls and 'entities' in tweet and 'hashtags' in tweet['entities']:
                for ht in tweet['entities']['hashtags']:
                    if ("#" + ht['text']) in poll_hashtags:
                        for poll_id in poll_hashtags['#'+ht['text']]:
                            res['polls'][poll_id]['data']['#'+ht['text']]['total'] += 1
    return flask.Response(dumps(res),  mimetype='application/json')


@app.route("/api/keywordset/prefetch", methods=['GET'])
def prefetch_keywordset():
    res = []
    resultset = accountdb.keywordset.find({}).limit(100)
    for r in resultset:
        res.append({"value": r['name'], "id": str(r['_id']), 'label': r['name'] })
    return flask.Response(json.dumps(res),  mimetype='application/json')

@app.route("/api/keywordset/search", methods=['GET'])
def search_keywordset():
    res = []
    resultset = accountdb.keywordset.find({"name": re.compile(request.args['term'], re.I|re.U)}).limit(100)
    for r in resultset:
        res.append({"value": r['name'], "id": str(r['_id']) })
    return flask.Response(json.dumps(res),  mimetype='application/json')

def getAccountsToTrack():
    accounts = monitor.accounts.find({})
    s = dict()
    for acc in accounts:
        for cid, campaign in acc['campaigns'].items():
            if not 'active' in campaign or not campaign['active']: continue
            for bid, brand in campaign['brands'].items():
                if brand.get('follow_accounts','').strip():
                    for kw in [kw.strip() for kw in brand['follow_accounts'].split(",") if kw.strip()]:
                            s[kw] = cid
    return s

@app.route("/api/account/campaign/save", methods=['POST'])
def save_campaign():
    data = request.get_json()
    campaign = data['campaign']
    
    account = accountdb.accounts.find_one({"_id":ObjectId(data['account_id'])})
    oldcamp = account['campaigns'][data['campaign_id']]
    credentials = {}
    if 'analytics' in oldcamp and 'credentials' in oldcamp['analytics']:
        credentials = oldcamp['analytics']['credentials']
    campaign['analytics']['credentials'] = credentials
    account['campaigns'][data['campaign_id']] = campaign
    
    #traigo los ids de las cuentas a seguir
    t = Twython("1qxRMuTzu2I7BP7ozekfRw", "whQFHN8rqR78L6su6U32G6TPT7e7W2vCouR4inMfM", "2305874377-TTmvLjLuP8aq8q2bT7GPJsOjG9n6uYLAA0tvsYU", "iy4SYpkHK26Zyfr9RhYSGOLVtd9eMNF6Ebl2p552gF4vL")    
    for bid, brand in campaign['brands'].items():
        follow_ids = []
        if brand.get('follow_accounts','').strip():
            for kw in [kw.strip() for kw in brand['follow_accounts'].split(",") if kw.strip()]:
                    follow_ids.append(t.lookup_user(screen_name=kw[1:])[0]['id_str'])
        campaign['brands'][bid]['follow_account_ids'] = ','.join(follow_ids)
    accountdb.accounts.save(account)
    print
    
    return flask.Response(json.dumps({}),  mimetype='application/json')

@app.route("/api/account/keywordset/save", methods=['POST'])
def save_keywordset():
    data = request.get_json()
    kwset = data['keywordset']
    kwset['_id'] = ObjectId(data['keywordset_id'])
    accountdb.keywordset.save(kwset)
    return flask.Response(json.dumps({}),  mimetype='application/json')

@app.route("/api/account/topic/save", methods=['POST'])
def save_topic():
    data = request.get_json()
    topic= data['topic']
    topic['_id'] = ObjectId(data['topic_id'])
    accountdb.topic.save(topic)
    return flask.Response(json.dumps({}),  mimetype='application/json')

@app.route("/api/account/analytics/sessions", methods=['GET'])
def analytics_sessions():
    res = 0
    error = "No Access"
    data = request.args
    account = accountdb.accounts.find_one({"_id":ObjectId(data['account_id'])})
    start = request.args.get("start", "")
    end = request.args.get("end", "")    
    if start and end and "analytics" in account['campaigns'][data['campaign_id']] and 'profiles' in account['campaigns'][data['campaign_id']]['analytics'] and 'credentials' in account['campaigns'][data['campaign_id']]["analytics"] and account['campaigns'][data['campaign_id']]["analytics"]["credentials"]:
        profile_ids = account['campaigns'][data['campaign_id']]['analytics']['profiles']
        analytics_credentials = Credentials.new_from_json(account['campaigns'][data['campaign_id']]["analytics"]["credentials"])
        if analytics_credentials.access_token_expired: error = "Access Token Expired"
        try:
            http = httplib2.Http()
            http = analytics_credentials.authorize(http)
            service = build('analytics', 'v3', http=http)
            start = datetime.strptime(start + "T00:00:00", "%Y-%m-%dT%H:%M:%S")
            end = datetime.strptime(end + "T23:59:59", "%Y-%m-%dT%H:%M:%S")        
            error = ""
            for profile_id in profile_ids:
                results = analytics_api.get_sessions(service, profile_id, start, end)
                if 'rows' in results:
                    res = res + int(results.get('rows')[0][0])
        except AccessTokenRefreshError:                    
            error = "No Access"
    return flask.Response(json.dumps({"res": res, "error": error}),  mimetype='application/json')


def getAccount(account_id):
    return accountdb.accounts.find_one({"_id": ObjectId(account_id)})

def getCampaignFollowAccounts(account, campaign_id):
    #account = accountdb.accounts.find_one({"_id": ObjectId(account_id)})
    s = set()
    campaign = account['campaigns'][campaign_id]
    for bid, brand in campaign['brands'].items():
        if brand.get('follow_accounts','').strip():
            for kw in [kw.strip() for kw in brand['follow_accounts'].split(",") if kw.strip()]:
                    s.add(kw)
    return s

@app.route("/api/account/mentions", methods=['GET'])
def twitter_mentions():
    start = request.args.get("start", "")
    end = request.args.get("end", "")
    account_id = request.args.get("account_id", "")
    campaign_id = request.args.get("campaign_id", "")
    res = {}
    if start and end and campaign_id:
        collection_name = "tweets_%s" % campaign_id
        start = datetime.strptime(start + "T00:00:00", "%Y-%m-%dT%H:%M:%S")
        end = datetime.strptime(end + "T23:59:59", "%Y-%m-%dT%H:%M:%S")
        group = {"_id": None}
        account = getAccount(account_id)
        for tacc in getCampaignFollowAccounts(account, campaign_id):
            group[tacc] = {"$sum": "$x_mentions_count.%s" % tacc}
        docs = accountdb[collection_name].aggregate([{"$match": { "retweeted_status": {"$exists": False}, "x_mentions_count": {"$exists": True}, "x_created_at": {"$gte": start, "$lte": end}}}, {"$group": group}])
        if len(docs['result']):
            res = docs['result'][0]
            del res['_id']
    return flask.Response(json.dumps({"res": res}),  mimetype='application/json')

@app.route("/oauth2callback", methods=['GET'])
def analytics_auth_callback():
    if "code" in request.args:
        cid, aid = b64decode(request.args["state"]).split(",")
        
        FLOW = OAuth2WebServerFlow(client_id='442071031907-0ce0m652985ra8030e9n8nfrogk5o6tr.apps.googleusercontent.com',
                           client_secret='43Bf_67s6E9PXIJe4ZY5fUSC',
                           scope='https://www.googleapis.com/auth/analytics.readonly',
                           redirect_uri='http://%s:5001/oauth2callback' % server_domain)
        credentials = FLOW.step2_exchange(request.args['code'])
        accountdb.accounts.update({"_id": ObjectId(aid)}, {"$set": {"campaigns.%s.analytics" % cid: {"credentials": credentials.to_json(), "profiles": []}}})        
        print dir(credentials)
        print credentials.to_json()
        http = httplib2.Http()
        http = credentials.authorize(http)
        
        service = build('analytics', 'v3', http=http)
        profile_id = analytics_api.get_first_profile_id(service)
        return u"Acceso a analytics (solo lectura) obtenido. Ya puede cerrar esta ventana y refrescar la ventana de administracion de la campaña"
    if "error" in request.args and request.args['error'] == "access_denied":
        return u"Acceso a analytics (solo lectura) revocado. Ya puede cerrar esta ventana y refrescar la ventana de administracion de la campaña"
    return "something went wrong"


@app.route('/api/fb_posts/list')
def fb_posts_list():
    start = request.args.get("start", "")
    end = request.args.get("end", "")
    page = int(request.args.get('page',"1"))-1
    posts_per_page = int(request.args.get('ppp',"20"))
    campaign_id = request.args.get("campaign_id", "")
    brands_to_include = request.args.get("brands_to_include", "")
    include_sentiment_tagged_posts = bool(request.args.get("include_sentiment_tagged_posts", "true") == "true")
    res = {"posts": [], "mentions": 0}
    if start and end and campaign_id:
        collection_name = "fb_posts_%s" % campaign_id
        start = datetime.strptime(start + " 00:00:00", "%Y-%m-%d %H:%M:%S")
        end = datetime.strptime(end + " 23:59:59", "%Y-%m-%d %H:%M:%S")
        docfilter = {"x_created_at": {"$gte": start, "$lte": end}}
        if not include_sentiment_tagged_posts: docfilter['x_sentiment'] = {"$exists": False}
        dbposts = accountdb[collection_name].find(docfilter).sort("x_created_at", -1).skip(page*posts_per_page).limit(posts_per_page) 
        if not brands_to_include:
            res['posts'].extend(dbposts)
        else:
            bti = [x.strip() for x in brands_to_include.split("|") if x.strip()]
            for t in dbposts:
                if 'x_extracted_info' in t and [pm for pm in t['x_extracted_info'] if pm['brand'] in bti]:
                    res['posts'].append(t)
    return flask.Response(dumps(res),  mimetype='application/json')

@app.route('/dc/<account_id>/<campaign_id>/<datacollection_id>', methods=['GET'])
def datacollection_landing_page_get(account_id, campaign_id, datacollection_id):
    account = getAccount(account_id)
    campaign = account['campaigns'][campaign_id]
    datacollection = campaign['datacollections'][datacollection_id]
    return render_template("datacollection_landing_page.html", dc = datacollection, account= account, campaign_id=campaign_id, datacollection_id = datacollection_id)

@app.route('/dc/<account_id>/<campaign_id>/<datacollection_id>', methods=['POST'])
def datacollection_landing_page_post(account_id, campaign_id, datacollection_id):
    account = getAccount(account_id)
    campaign = account['campaigns'][campaign_id]
    datacollection = campaign['datacollections'][datacollection_id]
    obj = {}
    obj['created_at'] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+00:00")
    fields = {}
    for f in datacollection['fields']:
        fields[f['name']] = request.form[f['name']]
    obj['fields'] = fields
    collection = "datacollection_%s" % datacollection_id
    accountdb[collection].insert(obj)
    return "GRABADO"

if __name__ == "__main__":
    app.debug = True
    app.jinja_options['extensions'].append('jinja2.ext.do')    
    app.run(host="0.0.0.0", port=5001)



