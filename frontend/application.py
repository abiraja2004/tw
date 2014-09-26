from pymongo import MongoClient, DESCENDING
from bson import ObjectId
from bson.json_util import dumps
from flask import Flask, render_template, request, Blueprint
from rulesmanager import getBrandClassifiers
import flask 
import json
import re
from datetime import datetime, timedelta
from oauth2client.client import OAuth2WebServerFlow, Credentials
from apiclient.discovery import build
import analytics_api
import httplib2
from base64 import b64encode, b64decode

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--auth', action="store_true", default=False)
args = parser.parse_args()
dbuser = "monitor"
dbpasswd = "monitor678"
mclient = MongoClient()
tweetdb = mclient['unilever']
if args.auth:
    tweetdb.authenticate(dbuser, dbpasswd)
accountdb = mclient['monitor']
if args.auth:
    accountdb.authenticate(dbuser, dbpasswd)


app = Flask(__name__, template_folder='html')



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
    return render_template(template, custom_css = custom_css, content_template=dashtemplate, js="dashboard.js", account=account, campaign_id = campaign_id, campaign=account['campaigns'][campaign_id], logo=logo, logo2 = logo2)            

@app.route('/campaign')
def campaigns():
    campaign_id = request.args.get("campaign_id", "5400d1902e61d70aab2e9bdf") #default Campana unilever
    account = accountdb.accounts.find_one({"campaigns.%s" % campaign_id: {"$exists": True}})
    campaign_id = request.args.get('campaign_id')
    custom_css= request.args.get("css", None)
    FLOW = OAuth2WebServerFlow(client_id='442071031907-0ce0m652985ra8030e9n8nfrogk5o6tr.apps.googleusercontent.com',
                           client_secret='43Bf_67s6E9PXIJe4ZY5fUSC',
                           scope='https://www.googleapis.com/auth/analytics.readonly',
                           redirect_uri='http://localhost:5001/oauth2callback')
    analytics_auth_url = FLOW.step1_get_authorize_url()+ "&state=" + b64encode("%s,%s" % (campaign_id,account['_id']))
    return render_template('app.html', custom_css = custom_css, content_template="campaign.html", js="campaign.js", account=account, campaign_id = campaign_id, campaign=account['campaigns'][campaign_id], analytics_auth_url = analytics_auth_url)

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
        res['tweets'].extend(dbtweets)
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
    account = request.args.get("account_id", "")
    campaign_id = request.args.get("campaign_id", "")
    group_dimension = request.args.get("group_dimension", "")
    res = {'timerange': []}
    if start and end and campaign_id and group_dimension:
        collection_name = "tweets_%s" % campaign_id
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
        res['dimensions'] = {}
        print timerange, campaign_id
        dbtweets = accountdb[collection_name].find({ "retweeted_status": {"$exists": False}, "x_created_at": {"$gte": start, "$lte": end}})
        for tweet in dbtweets:
            if group_dimension == "brand":
                pms = tweet.get('x_extracted_info', [])
                if pms:
                    pm = pms[0]
                    if not pm['brand'] in res['dimensions']: res['dimensions'][pm['brand']] = {}
                    d = tweet['x_created_at']
                    key = d.strftime(timeformat)
                    if not key in res['dimensions'][pm['brand']]:
                        res['dimensions'][pm['brand']][key] = 1
                    else:
                        res['dimensions'][pm['brand']][key] += 1   
            if group_dimension == "product":
                pms = tweet.get('x_extracted_info', [])
                if pms:
                    pm = pms[0]
                    if not pm['product']: continue                    
                    p = pm['brand'] + "/" + pm['product']
                    if not p in res['dimensions']: res['dimensions'][p] = {}
                    d = tweet['x_created_at']
                    key = d.strftime(timeformat)
                    if not key in res['dimensions'][p]:
                        res['dimensions'][p][key] = 1
                    else:
                        res['dimensions'][p][key] += 1   
            elif group_dimension == "sentiment":
                if 'x_sentiment' in tweet:
                    if not tweet['x_sentiment'] in res['dimensions']: res['dimensions'][tweet['x_sentiment']] = {}
                    d = tweet['x_created_at']
                    key = d.strftime(timeformat)
                    if not key in res['dimensions'][tweet['x_sentiment']]:
                        res['dimensions'][tweet['x_sentiment']][key] = 1
                    else:
                        res['dimensions'][tweet['x_sentiment']][key] += 1   
                
    return flask.Response(dumps(res),  mimetype='application/json')
    #return flask.jsonify({"results": res})    
    #return flask.Response(json.dumps(res),  mimetype='application/json')

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

@app.route("/api/account/campaign/save", methods=['POST'])
def save_campaign():
    data = request.get_json()
    campaign = data['campaign']
    
    account = accountdb.accounts.find_one({"_id":ObjectId(data['account_id'])})
    
    account['campaigns'][data['campaign_id']] = campaign
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
    data = request.args
    account = accountdb.accounts.find_one({"_id":ObjectId(data['account_id'])})
    start = request.args.get("start", "")
    end = request.args.get("end", "")    
    if start and end and "analytics" in account['campaigns'][data['campaign_id']]:
        analytics_credentials = Credentials.new_from_json(account['campaigns'][data['campaign_id']]["analytics"]["credentials"])
        http = httplib2.Http()
        http = analytics_credentials.authorize(http)
        service = build('analytics', 'v3', http=http)
        profile_id = analytics_api.get_first_profile_id(service)
        start = datetime.strptime(start + "T00:00:00", "%Y-%m-%dT%H:%M:%S")
        end = datetime.strptime(end + "T23:59:59", "%Y-%m-%dT%H:%M:%S")        
        results = analytics_api.get_sessions(service, profile_id, start, end)
        if 'rows' in results:
            res = results.get('rows')[0][0]
    return flask.Response(json.dumps({"res": res}),  mimetype='application/json')

@app.route("/oauth2callback", methods=['GET'])
def analytics_auth_callback():
    if "code" in request.args:
        cid, aid = b64decode(request.args["state"]).split(",")
        
        FLOW = OAuth2WebServerFlow(client_id='442071031907-0ce0m652985ra8030e9n8nfrogk5o6tr.apps.googleusercontent.com',
                           client_secret='43Bf_67s6E9PXIJe4ZY5fUSC',
                           scope='https://www.googleapis.com/auth/analytics.readonly',
                           redirect_uri='http://localhost:5001/oauth2callback')
        credentials = FLOW.step2_exchange(request.args['code'])
        accountdb.accounts.update({"_id": ObjectId(aid)}, {"$set": {"campaigns.%s.analytics" % cid: {"credentials": credentials.to_json()}}})        
        print dir(credentials)
        print credentials.to_json()
        http = httplib2.Http()
        http = credentials.authorize(http)
        
        service = build('analytics', 'v3', http=http)
        profile_id = analytics_api.get_first_profile_id(service)
        return profile_id
    return "something went wrong"

if __name__ == "__main__":
    app.debug = True
    app.jinja_options['extensions'].append('jinja2.ext.do')    
    app.run(host="0.0.0.0", port=5001)



