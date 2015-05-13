#encoding: utf-8
import sys
from twython import Twython, TwythonError
from pymongo import MongoClient, DESCENDING
from pymongo.errors import OperationFailure
import bson
from bson import ObjectId
from bson.json_util import dumps
from flask import Flask, render_template, request, Blueprint, redirect, url_for, session
from rulesmanager import getBrandClassifiers, getTopicClassifiers, getAccountsToTrack
from brandclassifier import ProductMatch
import flask 
from flask.ext.compress import Compress
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
from gnip.mongo import MongoManager
from pprint import pprint
from gnip.summarizer import Summarizer

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--auth', action="store_true", default=False)
parser.add_argument('--host', default='')
parser.add_argument('--listenport', default='')
args, known = parser.parse_known_args()
dbuser = "monitor"
dbpasswd = "monitor678"
if args.listenport:
    listenport = int(args.listenport)
else:
    listenport = 5001
if args.host:
    mclient = MongoClient(args.host)
else:
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
app.config['PROPAGATE_EXCEPTIONS'] = True
compress = Compress()
app.debug = True
app.testing = True
app.jinja_options['extensions'].append('jinja2.ext.do')    
app.secret_key = '34fwfwesg4jkebgbywhn56&&fdw3g][]d'
compress.init_app(app)

summarizer = Summarizer()

def onRemoteServer():
    return server_mode == SERVER_REMOTE

def onLocalServer():
    return server_mode == SERVER_LOCAL

"""
@app.route('/')
def root():
    return redirect(url_for('login'))
"""


def getUser(account=None):
    if not account:
        if 'account_id' in session: account = getAccount(session['account_id'])
    if account and 'username' in session and 'users' in account: return account['users'].get(session['username'], None)
    return None
        
def getPasswordHash(user, psw):
    return hashlib.md5(user + psw + PASSWORD_SALT).hexdigest()
        
@app.route('/logout', methods=["GET", "POST"])        
def logout():
    if 'username' in session: del session['username']
    if 'account' in session: del session['account']
    return redirect('/')

@app.route('/contact_request', methods=["POST"])        
def contact_request():
    from mailutils import send_email, EMAIL_RECEIVERS
    content = "nombre: %s\napellido: %s\nemail: %s\ncomentario: %s\n" % (request.form['nombre'],request.form['apellido'],request.form['email'],request.form['comentario'])
    ok=send_email(EMAIL_RECEIVERS, "nueva solicitud de contacto de %s" % request.form['email'], content)
    msg = "Gracias, en breve nos comunicaremos por email"
    if not ok:
        msg = "No hemos podido registrar la solicitud de contacto, por favor envianos un email a: nuev9info@gmail.com"
    return render_template("index.html", msg=msg)

@app.route('/login', methods=["GET", "POST"])
@app.route('/', methods=["GET", "POST"])
def login():
    session['username'] = ''
    template = "index.html"
    print request.host
    if request.host.find("001") >= 0: template = "login.html"
    if request.method == "GET":
        return render_template(template)
    elif request.method == "POST":
        user = request.form["user"]
        password = request.form["password"]
        passwordhash = getPasswordHash(user, password)
        acc = accountdb.accounts.find({"users.%s" % user: {"$exists": True}})
        msg = ""
        if not acc.count() or acc[0]['users'][user]['password'] != passwordhash:
            msg = "El usuario y/o clave son incorrectos"
            return render_template(template, user=user, msg=msg)
        else:
            accountdb.log_logins.insert({"account_id": acc[0]['_id'], "username": user, "timestamp": datetime.now()})
            session['username'] = user
            session['account_id'] = str(acc[0]['_id'])
            return redirect('/app?account_id=%s' % acc[0]['_id']+ '&campaign_id=%s' % acc[0]['campaigns'].keys()[0])
    
def getDateRange(request):
    if 'startdate' in request.cookies and 'enddate' in request.cookies:
        sd = datetime.strptime(request.cookies.get('startdate'), "%Y-%m-%d")
        ed = datetime.strptime(request.cookies.get('enddate'), "%Y-%m-%d")
    else:
        datetime.today()
        sd = datetime.today() - timedelta(days=3)
        ed = datetime.today()
    return (sd, ed)


def getID(s):
    try:
        return ObjectId(s)
    except bson.errors.InvalidId:
        return s

@app.route('/app')
@app.route('/gm')
def home():
    account_id = request.args.get("account_id", "53ff7ae51e076582a6fb7f12") #default: Prueba
    campaign_id = request.args.get("campaign_id", "") #default Campana unilever
    if request.path == "/sivale":
        account_id = "5410f47209109a09a2b5985b"  #SiVale account_id
        campaign_id = "5410f5a52e61d7162c700232"  #SiVale campaign_id   
    elif request.path == "/gm":
        account_id = "54189900d06625fc47e54b76" #general motors
        campaign_id = "54189b93d06625fc47e54b78" 
    logo = "logo.jpg"
    logo2 = None        
    if account_id == "5410f47209109a09a2b5985b": #sivale
        logo = "logoSivale.jpg"
        logo2 = "logoPromored.png"
    elif account_id == "5476951e9babd3b93e31b9a9": #sony
        logo = "logoSony.jpg"
        logo2 = "logoLumia.jpg"
    account = accountdb.accounts.find_one({"_id":getID(account_id)})
    if account and not campaign_id: campaign_id = account['campaigns'].keys()[0]
    template = "index.html"
    dashtemplate = "dashboard.html"
    if request.path == "/app" or request.path == "/sivale" or request.path == "/gm":
        template = "app.html"
        dashtemplate = "dashboard_app.html"
    custom_css= request.args.get("css", None)
    print logo
    has_products = False
    own_brands_list = []
    if not 'brands' in account['campaigns'][campaign_id]: account['campaigns'][campaign_id]['brands'] = {}
    for bid, brand in account['campaigns'][campaign_id]['brands'].items():
        if brand['own_brand']: own_brands_list.append(brand['name'])
        if len(account['campaigns'][campaign_id]['brands'][bid]['products']):
            has_products = True
    return render_template(template, custom_css = custom_css, content_template=dashtemplate, js="dashboard.js", user=getUser(account), account=account, campaign_id = campaign_id, campaign=account['campaigns'][campaign_id], logo=logo, logo2 = logo2,has_products = has_products, own_brands_list = '|'.join(own_brands_list), daterange=getDateRange(request))            


def get_analytics_credentials(account, campaign_id):
    campaign = account['campaigns'][campaign_id]
    if not ('analytics' in campaign and 'credentials' in campaign['analytics'] and campaign['analytics']['credentials']): return None
    credentials = Credentials.new_from_json(campaign['analytics']['credentials'])
    if credentials.access_token_expired:
        http = httplib2.Http()
        try:
            credentials.refresh(http)
        except AccessTokenRefreshError:
            credentials = None
    if not credentials or credentials.access_token_expired:
        accountdb.accounts.update({"_id": account['_id']}, {"$set": {"campaigns.%s.analytics" % campaign_id: {"credentials": None, "profiles": []}}})
        return None
    else:
        accountdb.accounts.update({"_id": account['_id']}, {"$set": {"campaigns.%s.analytics.credentials" % campaign_id: credentials.to_json()}})
        return credentials    
    
@app.route('/campaign')
def campaigns():
    campaign_id = request.args.get("campaign_id", "5400d1902e61d70aab2e9bdf") #default Campana unilever
    account = accountdb.accounts.find_one({"campaigns.%s" % campaign_id: {"$exists": True}})
    custom_css= request.args.get("css", None)
    FLOW = OAuth2WebServerFlow(client_id='442071031907-0ce0m652985ra8030e9n8nfrogk5o6tr.apps.googleusercontent.com',
                           client_secret='43Bf_67s6E9PXIJe4ZY5fUSC',
                           scope='https://www.googleapis.com/auth/analytics.readonly',
                           redirect_uri='http://%s:5001/oauth2callback' % server_domain)    #HABRIA QUE SACAR EL PUERTO 5001!
    analytics_credentials = get_analytics_credentials(account, campaign_id)
    analytics_access = bool(analytics_credentials)
    analytics_auth_url = FLOW.step1_get_authorize_url()+ "&state=" + b64encode("%s,%s" % (campaign_id,account['_id']))
    analytics_revoke_url = ""
    if analytics_credentials:
        analytics_revoke_url = FLOW.revoke_uri + "?token=%s" % analytics_credentials.access_token
    campaign = account['campaigns'][campaign_id]        
    if not 'brands' in campaign: campaign['brands'] = {}
    if not 'topics' in campaign: campaign['topics'] = {}
    if not 'use_geolocation' in campaign: campaign['use_geolocation'] = False
    if not 'polls' in campaign: campaign['polls'] = {}
    if not 'datacollections' in campaign: campaign['datacollections'] = {}
    if not 'syncversion' in campaign: campaign['syncversion'] = 1

    logo = "logo.jpg"
    logo2 = None        
    if str(account['_id']) == "5410f47209109a09a2b5985b": #sivale
        logo = "logoSivale.jpg"
        logo2 = "logoPromored.png"
    elif str(account['_id']) == "5476951e9babd3b93e31b9a9": #sony
        logo = "logoSony.jpg"
        logo2 = "logoLumia.jpg"
        
    return render_template('app.html', custom_css = custom_css, content_template="campaign.html", js="campaign.js", account=account, user=getUser(account), campaign_id = campaign_id, campaign=campaign, analytics_auth_url = analytics_auth_url, analytics_access = analytics_access, analytics_revoke_url= analytics_revoke_url, logo=logo, logo2 = logo2, daterange=getDateRange(request))

@app.route('/polls')
def polls():
    account_id = request.args.get("account_id")
    account = getAccount(account_id)
    custom_css= request.args.get("css", None)

    if not 'polls' in account: account['polls'] = {}

    logo = "logo.jpg"
    logo2 = None        
    if str(account['_id']) == "5410f47209109a09a2b5985b": #sivale
        logo = "logoSivale.jpg"
        logo2 = "logoPromored.png"
    elif str(account['_id']) == "5476951e9babd3b93e31b9a9": #sony
        logo = "logoSony.jpg"
        logo2 = "logoLumia.jpg"
        
    return render_template('app.html', custom_css = custom_css, content_template="polls.html", js="polls.js", account=account, user=getUser(account), logo=logo, logo2 = logo2, daterange=getDateRange(request))

@app.route('/datacollections')
def datacollections():
    account_id = request.args.get("account_id")
    account = getAccount(account_id)
    custom_css= request.args.get("css", None)

    if not 'datacollections' in account: account['datacollections'] = {}

    logo = "logo.jpg"
    logo2 = None        
    if str(account['_id']) == "5410f47209109a09a2b5985b": #sivale
        logo = "logoSivale.jpg"
        logo2 = "logoPromored.png"
    elif str(account['_id']) == "5476951e9babd3b93e31b9a9": #sony
        logo = "logoSony.jpg"
        logo2 = "logoLumia.jpg"
        
    data = {}
    for dc_id in account['datacollections'].keys():
        records = accountdb['datacollection_%s' % dc_id].find({})
        data[dc_id] = records[:]
    return render_template('app.html', custom_css = custom_css, content_template="datacollections.html", js="datacollections.js", account=account, user=getUser(account), data=data, logo=logo, logo2 = logo2, daterange=getDateRange(request))

@app.route('/api/analytics/get_all_profiles')
def analytics_get_all_profiles():
    campaign_id = request.args.get("campaign_id") #default Campana unilever
    account = accountdb.accounts.find_one({"campaigns.%s" % campaign_id: {"$exists": True}})
    FLOW = OAuth2WebServerFlow(client_id='442071031907-0ce0m652985ra8030e9n8nfrogk5o6tr.apps.googleusercontent.com',
                           client_secret='43Bf_67s6E9PXIJe4ZY5fUSC',
                           scope='https://www.googleapis.com/auth/analytics.readonly',
                           redirect_uri='http://%s:5001/oauth2callback' % server_domain)    
    analytics_credentials = get_analytics_credentials(account, campaign_id)
    analytics_profiles = []
    analytics_access =False
    if analytics_credentials:
        http = httplib2.Http()
        try:
            http = analytics_credentials.authorize(http)
            service = build('analytics', 'v3', http=http)
            analytics_profiles = analytics_api.get_all_profiles(service)
            analytics_access = True
        except AccessTokenRefreshError:
            pass
    res = {}
    res['analytics_profiles']=analytics_profiles
    res['campaign_profiles']=account['campaigns'][campaign_id]['analytics']['profiles']
    if not analytics_access:
        account['campaigns'][campaign_id]['analytics']['credentials'] = {}
        accountdb.accounts.save(account)
    return flask.Response(dumps(res),  mimetype='application/json')


@app.route('/sentiment')
def sentiment():
    account_id = request.args.get("account_id", "") #default: Prueba
    campaign_id = request.args.get("campaign_id", "") #default Campana unilever
    account = getAccount(account_id)
    if account and not campaign_id: campaign_id = account['campaigns'].keys()[0]
    custom_css= request.args.get("css", None)

    logo = "logo.jpg"
    logo2 = None        
    if str(account['_id']) == "5410f47209109a09a2b5985b": #sivale
        logo = "logoSivale.jpg"
        logo2 = "logoPromored.png"
    elif str(account['_id']) == "5476951e9babd3b93e31b9a9": #sony
        logo = "logoSony.jpg"
        logo2 = "logoLumia.jpg"
        
    own_brands_list = []
    for bid, brand in account['campaigns'][campaign_id]['brands'].items():
        if brand['own_brand']: own_brands_list.append(brand['name'])
    return render_template('app.html', custom_css = custom_css, content_template="sentiment.html", js="sentiment.js", account=account, user=getUser(account), campaign_id = campaign_id, campaign=account['campaigns'][campaign_id], logo=logo, logo2 = logo2, own_brands_list = '|'.join(own_brands_list), daterange=getDateRange(request))

@app.route('/keywordsets')
def keywordsets():
    campaign_id = request.args.get("campaign_id", "")
    account_id = request.args.get("account_id", "") #default: Prueba
    account = getAccount(account_id)
    campaign_id = request.args.get('campaign_id')    
    keywordsets = accountdb.keywordset.find({})
    custom_css= request.args.get("css", None)

    if account and not campaign_id: campaign_id = account['campaigns'].keys()[0]
    logo = "logo.jpg"
    logo2 = None        
    if str(account['_id']) == "5410f47209109a09a2b5985b": #sivale
        logo = "logoSivale.jpg"
        logo2 = "logoPromored.png"
    elif str(account['_id']) == "5476951e9babd3b93e31b9a9": #sony
        logo = "logoSony.jpg"
        logo2 = "logoLumia.jpg"
        
    restricted = request.args.get("restricted", "true") == "true"
    return render_template('app.html', custom_css = custom_css, content_template="keywordsets.html", js="keywordset.js", keywordsets = list(keywordsets), account=account, user=getUser(account), campaign_id = campaign_id, campaign=account['campaigns'][campaign_id], logo=logo, logo2 = logo2,restricted=restricted, daterange=getDateRange(request))

@app.route('/topics')
def topics():
    account_id = request.args.get("account_id", "") #default: Prueba
    account = getAccount(account_id)
    campaign_id = request.args.get('campaign_id')    
    if account and not campaign_id: campaign_id = account['campaigns'].keys()[0]
    topics = accountdb.topic.find({})
    custom_css= request.args.get("css", None)

    logo = "logo.jpg"
    logo2 = None        
    if str(account['_id']) == "5410f47209109a09a2b5985b": #sivale
        logo = "logoSivale.jpg"
        logo2 = "logoPromored.png"
    elif str(account['_id']) == "5476951e9babd3b93e31b9a9": #sony
        logo = "logoSony.jpg"
        logo2 = "logoLumia.jpg"
        
    restricted = request.args.get("restricted", "true") == "true"
    return render_template('app.html', custom_css = custom_css, content_template="topics.html", js="topic.js", topics = list(topics), account=account, user=getUser(account), campaign_id = campaign_id, campaign=account['campaigns'][campaign_id], logo=logo, logo2 = logo2, restricted=restricted, daterange=getDateRange(request))

@app.route('/api/create_index', methods=['POST'])
def create_index():
    collection_name = request.form['collection_name']
    fields = request.form['fields'].split("|")
    d = []
    for ff in fields:
        f, o = ff.split(",")
        if o in ("1", "-1"): o = int(o)
        d.append((f, o))
    res = accountdb[collection_name].ensure_index(d)
    res = {"result": "OK"}
    return flask.Response(dumps(res),  mimetype='application/json')

@app.route('/account_admin')
def account_admin():
    accounts = list(accountdb.accounts.find({}))
    account = getAccount(session['account_id'])
    campaign_id = request.args.get('campaign_id')    
    if account and not campaign_id: campaign_id = account['campaigns'].keys()[0]
    custom_css= request.args.get("css", None)
    collection_data = {}
   
    for acc in accounts:
        for camp_id in acc['campaigns'].keys():
            data={}
            try:
                data['stats'] = accountdb.command('collstats', 'tweets_%s' % camp_id)
            except OperationFailure, e:
                data['stats'] = {}
            try:
                data['indexes'] = accountdb['tweets_%s' % camp_id].index_information()
            except OperationFailure, e:
                data['indexes'] = {}
            collection_data['tweets_%s' % camp_id] = data
            
            data = {}
            try:
                data['stats'] = accountdb.command('collstats', 'summarized_tweets_%s' % camp_id)
            except OperationFailure, e:
                data['stats'] = {}
            try:
                data['indexes'] = accountdb['summarized_tweets_%s' % camp_id].index_information()
            except OperationFailure, e:
                data['indexes'] = {}                
            collection_data['summarized_tweets_%s' % camp_id] = data

            data = {}
            try:
                data['stats'] = accountdb.command('collstats', 'feeds_%s' % camp_id)
            except OperationFailure, e:
                data['stats'] = {}
            try:
                data['indexes'] = accountdb['feeds_%s' % camp_id].index_information()
            except OperationFailure, e:
                data['indexes'] = {}                
            collection_data['feeds_%s' % camp_id] = data
        
    logo = "logo.jpg"
    logo2 = None        
    return render_template('app.html', custom_css = custom_css, content_template="account_admin.html", js="account_admin.js", collection_data = collection_data, account=account, accounts=list(accounts), user=getUser(account), campaign_id = campaign_id, logo=logo, logo2 = logo2, daterange=getDateRange(request))

@app.route('/api/account/campaign/topics/reassign')
def reassign_topics():
    account_id = request.args.get("account_id", "")
    campaign_id = request.args.get('campaign_id')
    account = getAccount(account_id)
    campaign = account['campaigns'][campaign_id]
    tcs = getTopicClassifiers()
    collection_name = "tweets_%s" % campaign_id
    dbtweets = accountdb[collection_name].find({})
    now = datetime.now()
    n = 0
    c = 0
    topics = tcs.get(campaign_id, {}).items()
    for t in dbtweets:
        oldtms = t.get('x_extracted_topics', [])
        if c % 10 == 0: print "\rtweet %s, %s      " % (c,n)
        tms = []
        for topic_id, topic_classiffier in topics:
            tm = topic_classiffier.extract(t['text'])
            if tm: tms.append(tm.getDictionary())
        if tms: tms.sort(key=lambda x: x['confidence'], reverse=True)
        if oldtms != tms:
            t['x_extracted_topics'] = tms
            #accountdb[collection_name].save(t)
            n += 1
        c += 1
    print datetime.now() - now
    res = {"result": "OK", "tweets_updated": n}
    return flask.Response(dumps(res),  mimetype='application/json')
    
@app.route('/api/account/campaign/brands/reassign')
def reassign_brands():
    account_id = request.args.get("account_id", "")
    campaign_id = request.args.get('campaign_id')
    account = getAccount(account_id)
    campaign = account['campaigns'][campaign_id]
    bcs = getBrandClassifiers()
    collection_name = "tweets_%s" % campaign_id
    dbtweets = accountdb[collection_name].find({})
    n = 0
    accountsToTrack, accountsToTrackIds= getAccountsToTrack()
    for t in dbtweets:
        print "\rtweet %s      " % n
        pms = {}
        for bc in bcs:
            if not bc.campaign_id in pms: pms[bc.campaign_id] = []
            pms[bc.campaign_id].extend([pm.getDictionary() for pm in bc.extract(t['text'])])
        x_mentions_count = {}
        if not 'entities' in t: t['entities']={}
        if not 'user_mentions' in t['entities']: t['entities']['user_mentions']=[]
        for m in t['entities']['user_mentions']:
            if ("@" + m["screen_name"]) in accountsToTrack: 
                x_mentions_count["@" + m['screen_name']] = 1
                pm = ProductMatch()
                pm.brand = accountsToTrack["@" + m['screen_name']]['brand']
                pm.campaign_id = accountsToTrack["@" + m['screen_name']]['cid']
                pm.confidence = 5
                pms[pm.campaign_id].append(pm.getDictionary())
                                
        if 'user' in t and 'id_str' in t['user']:
            if t['user']['id_str'] in accountsToTrackIds:
                pm = ProductMatch()
                pm.brand = accountsToTrackIds[t['user']['id_str']]['brand']
                pm.campaign_id = accountsToTrackIds[t['user']['id_str']]['cid']
                pm.confidence = 5
                pms[pm.campaign_id].append(pm.getDictionary())
                if accountsToTrackIds[t['user']['id_str']]['own_brand']:
                   if not 'x_sentiment' in t: t['x_sentiment'] = '='
                
        if 'x_extracted_info' in t: del t['x_extracted_info']
        if 'x_mentions_count' in t: del t['x_mentions_count']
        if pms or x_mentions_count:
            t['x_mentions_count'] = x_mentions_count
            extracted_infos = pms.get(campaign_id, [])
            if extracted_infos:
                extracted_infos.sort(key=lambda x: x['confidence'], reverse=True)
                if extracted_infos[0]['confidence'] > 0:
                    t['x_extracted_info'] = extracted_infos

        accountdb[collection_name].save(t)
        n += 1
        
    res = {"result": "OK", "tweets_updated": n}
    return flask.Response(dumps(res),  mimetype='application/json')
    
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
        start = datetime.strptime(start + " 00:00:00", "%Y-%m-%d %H:%M:%S")
        end = datetime.strptime(end + " 23:59:59", "%Y-%m-%d %H:%M:%S")
        docfilter = { "retweeted_status": {"$exists": False}, "x_created_at": {"$gte": start, "$lte": end}}
        if not include_sentiment_tagged_tweets: docfilter['x_sentiment'] = {"$exists": False}
        #dbtweets = accountdb[collection_name].find(docfilter).sort("x_created_at", -1).skip(page*tweets_per_page).limit(tweets_per_page) 
        dbtweets = MongoManager.findTweets(collection_name, filters=docfilter, sort=("x_created_at", -1), skip=page*tweets_per_page, limit=tweets_per_page) 
        if not brands_to_include:
            if campaign_id == '5410f5a52e61d7162c700232': #SiVale:
                for t in dbtweets:
                    if 'x_coordinates' in t.d and t.d['x_coordinates'] and 'country_code' in t.d['x_coordinates'] and t.d['x_coordinates']['country_code'] != 'MX': continue
                    res['tweets'].append(t.getDictionary())                    
            else:
                res['tweets'].extend([t.getDictionary() for t in dbtweets])  #esta sola linea es la que va cuando se saque la condicion de sivale
        else:
            bti = [x.strip() for x in brands_to_include.split("|") if x.strip()]
            for t in dbtweets:
                if 'x_extracted_info' in t and [pm for pm in t['x_extracted_info'] if pm['brand'] in bti]:
                    if campaign_id == '5410f5a52e61d7162c700232': #SiVale:
                        if 'x_coordinates' in t and t['x_coordinates'] and 'country_code' in t['x_coordinates'] and t['x_coordinates']['country_code'] != 'MX': continue
                    res['tweets'].append(t.getDictionary())   #esta sola linea es la que va cuando se saque la condicion de sivale
    return flask.Response(dumps(res),  mimetype='application/json')

@app.route('/api/feeds/list')
def feeds_list():
    start = request.args.get("start", "")
    end = request.args.get("end", "")
    page = int(request.args.get('page',"1"))-1
    tweets_per_page = int(request.args.get('tpp',"20"))
    campaign_id = request.args.get("campaign_id", "")
    brands_to_include = request.args.get("brands_to_include", "")
    include_sentiment_tagged_tweets = bool(request.args.get("include_sentiment_tagged_feeds", "true") == "true")
    res = {"feeds": []}
    if start and end and campaign_id:
        collection_name = "feeds_%s" % campaign_id
        start = datetime.strptime(start + " 00:00:00", "%Y-%m-%d %H:%M:%S")
        end = datetime.strptime(end + " 23:59:59", "%Y-%m-%d %H:%M:%S")
        docfilter = { "x_created_at": {"$gte": start, "$lte": end}}
        if not include_sentiment_tagged_tweets: docfilter['x_sentiment'] = {"$exists": False}
        #dbtweets = accountdb[collection_name].find(docfilter).sort("x_created_at", -1).skip(page*tweets_per_page).limit(tweets_per_page) 
        dbtweets = MongoManager.findFeeds(collection_name, filters=docfilter, sort=("x_created_at", -1), skip=page*tweets_per_page, limit=tweets_per_page) 
        if not brands_to_include:
            if campaign_id == '5410f5a52e61d7162c700232': #SiVale:
                for t in dbtweets:
                    if 'x_coordinates' in t.d and t.d['x_coordinates'] and 'country_code' in t.d['x_coordinates'] and t.d['x_coordinates']['country_code'] != 'MX': continue
                    res['feeds'].append(t.getDictionary())                    
            else:
                res['feeds'].extend([t.getDictionary() for t in dbtweets])  #esta sola linea es la que va cuando se saque la condicion de sivale
        else:
            bti = [x.strip() for x in brands_to_include.split("|") if x.strip()]
            for t in dbtweets:
                if 'x_extracted_info' in t and [pm for pm in t['x_extracted_info'] if pm['brand'] in bti]:
                    res['feeds'].append(t.getDictionary())   #esta sola linea es la que va cuando se saque la condicion de sivale
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
    #print 1, datetime.now()
    start = request.args.get("start", "")
    end = request.args.get("end", "")
    group_by = request.args.get("group_by", "day")
    account_id = request.args.get("account_id", "")
    campaign_id = request.args.get("campaign_id", "")
    brands_to_include = request.args.get("brands_to_include", "")
    res = {'timerange': []}
    if start and end and campaign_id:
        #print 2, datetime.now()
        account = MongoManager.getAccount(id=account_id)
        campaign = account.getCampaign(id=campaign_id)
        #accs = getCampaignFollowAccounts(account.getId(), campaign_id)
        accs = campaign.getFollowAccounts()
        collection_name = "tweets_%s" % campaign_id
        bti = [x.strip() for x in brands_to_include.split("|") if x.strip()]
        start = datetime.strptime(start + "T00:00:00", "%Y-%m-%dT%H:%M:%S")
        end = datetime.strptime(end + "T00:00:00", "%Y-%m-%dT%H:%M:%S") + timedelta(days=1)
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
        #dbtweets = MongoManager.findTweets(collection_name, filters={ "retweeted_status": {"$exists": False}, "x_created_at": {"$gte": start, "$lte": end}})
        
        #accountdb[collection_name].find(, {'_id': 0, 'x_coordinates': 1, 'x_sentiment': 1, 'x_extracted_info': 1, 'x_extracted_topics': 1, 'user': 1, 'x_mentions_count': 1, 'retweet_count': 1, 'favorite_count':  1, 'x_created_at': 1})
        #print 3, datetime.now()
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
        res['topic'] = {}
        res['words'] = {}
        #print 4, datetime.now()
        rrr = summarizer.getSummarizedData(campaign, start, end)
        #pprint(rrr)
        if rrr:
            #print 5, datetime.now()
            rrr = summarizer.aggregate(campaign, rrr, group_by)
            #print 6, datetime.now()
            res['stats'] = rrr['stats']
            res['sentiment'] = rrr['sentiment']
            res['brand'] = rrr['brand']
            res['product'] = rrr['product']
            res['topic'] = rrr['topic']
            res['words'] = rrr['words']
            if len(res['words']) > 100: res['words'] = res['words'][:100]
        #print 7, datetime.now()
        polls = account.getActivePolls()
        poll_hashtags = {}
        for poll in polls:
            poll_id = poll.getId()
            data = {}
            for ht in poll.getOptionHashtags():
                if not ht in poll_hashtags: poll_hashtags[ht] = []
                poll_hashtags[ht].append(poll_id)
                data[ht] = {'total': 0} 
            d = poll.getDictionary()
            d['data'] = data
            res['polls'][poll_id] = d
            
        for poll in polls:
            poll_id = poll.getId()
            collection_name = "polls_%s" % poll_id
            polltweets = accountdb[collection_name].find({ "retweeted_status": {"$exists": False}, "x_created_at": {"$gte": start, "$lte": end}})
            options = poll.getOptionHashtags()
            for tweet in polltweets:
                if campaign_id == '5410f5a52e61d7162c700232': #SiVale:
                    if 'x_coordinates' in tweet and tweet['x_coordinates'] and 'country_code' in tweet['x_coordinates'] and tweet['x_coordinates']['country_code'] != 'MX': continue                
                if 'entities' in tweet and 'hashtags' in tweet['entities']:
                    for ht in tweet['entities']['hashtags']:
                        if ("#" + ht['text']) in options:
                            res['polls'][poll_id]['data']['#'+ht['text']]['total'] += 1
                
        datacollections = account.getActiveDataCollections()

        for datacollection in datacollections:
            datacollection_id = datacollection.getId()            
            data = {}
            for field in datacollection.getFields():
                data[field['name']] = {}
            
            for dcitem in accountdb['datacollection_%s' % datacollection_id].find({}): #habria que filtrar por fecha??
                for field in datacollection.getFields():
                    if field['type'] != "combobox": continue #por ahora solo cuento los comboboxes
                    if field['name'] in dcitem['fields']:
                        if dcitem['fields'][field['name']] not in data[field['name']]:
                            data[field['name']][dcitem['fields'][field['name']]] = {'total': 1}
                        else:
                            data[field['name']][dcitem['fields'][field['name']]]['total'] += 1
            d = datacollection.getDictionary()
            d['data'] = data
            res['datacollections'][datacollection_id] = d
        #pprint(dbtweets.explain())
        #dbtweets = list(dbtweets)
        """
        for tweet in dbtweets:
            cc += 1
            if campaign_id == '5410f5a52e61d7162c700232': #SiVale:
                if 'x_coordinates' in tweet and tweet['x_coordinates'] and 'country_code' in tweet['x_coordinates'] and tweet['x_coordinates']['country_code'] != 'MX': continue                
            
            pms = tweet.getExtractedInfo()
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
            if tweet.getSentiment():
                if not tweet.getSentiment() in res['sentiment']: res['sentiment'][tweet.getSentiment()] = {"total": 0}
                d = tweet.getCreatedDate()
                key = d.strftime(timeformat)
                res['sentiment'][tweet.getSentiment()]['total'] += 1
                if not key in res['sentiment'][tweet.getSentiment()]:
                    res['sentiment'][tweet.getSentiment()][key] = 1
                else:
                    res['sentiment'][tweet.getSentiment()][key] += 1                   
            res['stats']['total_tweets'] += 1                    
            for k in tweet.getExtractedTopics():
                if not k['topic_name'] in res['topic']: res['topic'][k['topic_name']] = {'total': 0}
                res['topic'][k['topic_name']]['total'] += 1
            for k,v in tweet.getFollowAccountsMentionCount().items():
                if k in accs:
                    res['stats']['mentions']['total'] += 1
                    res['stats']['mentions']['accounts'][k] += 1
            if tweet.getUsername() in accs:
                res['stats']['own_tweets']['total'] += 1
                res['stats']['own_tweets']['accounts'][tweet.getUsername()] += 1
                if tweet.getRetweetsCount():
                    res['stats']['own_tweets']['retweets']['total'] += tweet.getRetweetsCount()
                    res['stats']['own_tweets']['retweets']['accounts'][tweet.getUsername()] += tweet.getRetweetsCount()
                if tweet.getFavoritesCount():
                    res['stats']['own_tweets']['favorites']['total'] += tweet.getFavoritesCount()
                    res['stats']['own_tweets']['favorites']['accounts'][tweet.getUsername()] += tweet.getFavoritesCount()
        """
        #print 8, datetime.now()
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

"""def getAccountsToTrack():
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
"""

@app.route("/api/account/campaign/save", methods=['POST'])
def save_campaign():
    data = request.get_json()
    campaign = data['campaign']
    
    account = accountdb.accounts.find_one({"_id":ObjectId(data['account_id'])})
    oldcamp = account['campaigns'][data['campaign_id']]
    if 'syncversion' in oldcamp and int(oldcamp['syncversion']) != int(campaign['syncversion']): 
        return flask.Response(json.dumps({"result": "error", "error": "syncversion"}),  mimetype='application/json')
    credentials = {}
    
    #tengo en cuenta se si cargaron los profiles desde la web o no
    profiles = campaign['analytics']['profiles']
    if not data['analytics_profiles_loaded'] and 'analytics' in oldcamp and 'profiles' in oldcamp['analytics']:
        profiles = oldcamp['analytics']['profiles']
    campaign['analytics']['profiles'] = profiles
    
    if 'analytics' in oldcamp and 'credentials' in oldcamp['analytics']:
        credentials = oldcamp['analytics']['credentials']
    campaign['analytics']['credentials'] = credentials
    
    #traigo los ids de las cuentas a seguir  // Esto solo habria que hacerlo si el campo follow_accounts fue modificado!!!
    ## ESTO YA NO ES NECESARIO!
    t = Twython("1qxRMuTzu2I7BP7ozekfRw", "whQFHN8rqR78L6su6U32G6TPT7e7W2vCouR4inMfM", "2305874377-TTmvLjLuP8aq8q2bT7GPJsOjG9n6uYLAA0tvsYU", "iy4SYpkHK26Zyfr9RhYSGOLVtd9eMNF6Ebl2p552gF4vL")    
    for bid, brand in campaign['brands'].items():
        follow_ids = []
        if brand.get('follow_accounts','').strip():
            for kw in [kw.strip() for kw in brand['follow_accounts'].split(",") if kw.strip()]:
                    try:
                        follow_ids.append(t.lookup_user(screen_name=kw[1:])[0]['id_str'])
                    except TwythonError, e:
                        return flask.Response(json.dumps({"result": "error", "error": "twitter account error", "message": "No se pudo identificar el id de la cuenta a seguir: %s en la marca: %s" % (kw, brand.get("name", ""))}),  mimetype='application/json')
        campaign['brands'][bid]['follow_account_ids'] = ','.join(follow_ids)
    ## ESTO YA NO ES NECESARIO!
    
    campaign['syncversion'] = int(campaign.get('syncversion',1))+1
    account['campaigns'][data['campaign_id']] = campaign        
    accountdb.accounts.save(account)
    print
    
    return flask.Response(json.dumps({"result": "ok", "syncversion": campaign['syncversion']}),  mimetype='application/json')



@app.route("/api/account/save", methods=['POST'])
def save_account():
    data = request.get_json()
    print data
    print data['account']['campaigns']
    try:
        cid = ObjectId(data['account_id'])
    except bson.errors.InvalidId:
        cid = data['account_id']
    account = accountdb.accounts.find_one({"_id":cid})
    if not account: account = {'_id': cid, 'campaigns': {}, 'users': {}}
    account['name'] = data['account']['name']
    if not 'users' in account: account['users'] = {}
    for campaign_id, campaign in data['account']['campaigns'].items():
        if campaign_id not in account['campaigns']:
            account['campaigns'][campaign['_id']] = campaign
     
    for username, user in data['account']['users'].items():
        
        if username in account['users'] and not user['password']:
            user['password'] = account['users'][username]['password']
        else:
            user['password'] = getPasswordHash(username, user['password'])
        account['users'][username] = user
    for username, user in account['users'].items():
        if username not in data['account']['users']:
            del account['users'][username]
    accountdb.accounts.save(account)    
    return flask.Response(json.dumps({"result": "ok"}),  mimetype='application/json')



@app.route("/api/account/poll/save", methods=['POST'])
def save_poll():
    data = request.get_json()
    poll = data['poll']
    
    account = accountdb.accounts.find_one({"_id":ObjectId(data['account_id'])})
    if not 'polls' in account: account['polls'] = {}
    account['polls'][data['poll_id']] = poll
    accountdb.accounts.save(account)
    print
    
    return flask.Response(json.dumps({}),  mimetype='application/json')

@app.route("/api/account/datacollection/save", methods=['POST'])
def save_datacollection():
    data = request.get_json()
    datacollection = data['datacollection']
    
    account = accountdb.accounts.find_one({"_id":ObjectId(data['account_id'])})
    if not 'datacollections' in account: account['datacollections'] = {}
    account['datacollections'][data['datacollection_id']] = datacollection
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

@app.route("/api/server/killprocess", methods=['GET'])
def kill_process():
    import subprocess
    from subprocess import PIPE    
    output = subprocess.Popen('kill -9 %s' % request.args.get("pid"), shell=True, stdout=PIPE).stdout.read()
    return server_status()

@app.route("/api/server/status", methods=['GET'])
def server_status():
    
    def findProcessPID(matchstr, output):
        if output.find(matchstr) >= 0:
            return [ln for ln in output.split("\n") if ln.find(matchstr) >= 0][0].strip().split()[0]
        return -1            

    import subprocess
    from subprocess import PIPE
    output = subprocess.Popen('ps ax | grep python', shell=True, stdout=PIPE).stdout.read()
    
    processes = {}
    processes['Gnip Twitter & Facebook fetcher service'] = findProcessPID("python gnip.py", output)
    processes['Summarizer'] = findProcessPID("python summarizer.py", output)
    processes['Gnip Rules Manager'] = findProcessPID("python rules_manager.py", output)
    processes['Forums Monitor Service'] = findProcessPID("python feed.py", output)
    processes['FLASK Web Server'] = findProcessPID("python application.py", output)
    processes['Google Geocoding Service'] = findProcessPID("python geocoding.py", output)
    #processes['Gnip Datacollection Service'] = output.find("python datacollection.py") >= 0
    processes['Twitter API Connection Service'] = findProcessPID("python twfetch.py", output)
    
    output = subprocess.Popen('ps ax | grep uwsgi', shell=True, stdout=PIPE).stdout.read()
    processes['UWSGI Service'] = findProcessPID("uwsgi uwsgi.ini", output)

    output = subprocess.Popen('ps ax | grep nginx', shell=True, stdout=PIPE).stdout.read()
    processes['NGINX Service'] = findProcessPID("nginx: master process", output)

    storage = subprocess.Popen('df -h', shell=True, stdout=PIPE).stdout.read().decode("utf-8")

    backups = subprocess.Popen('ls -lh /mnt/volume1/backups', shell=True, stdout=PIPE).stdout.read().decode("utf-8")
    return render_template('server_status.html', processes=processes, storage=storage, backups=backups)

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
        analytics_credentials = get_analytics_credentials(account, data['campaign_id'])
        if not analytics_credentials.access_token_expired: error = "No access to Analytics"
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
    if not 'brands' in campaign: return s
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
        print "REFRESH TOKEN:" , credentials.refresh_token
        if not credentials.refresh_token:
            account = getAccount(aid)
            campaign = account['campaigns'][cid]
            if 'analytics' in campaign and 'credentials' in campaign['analytics'] and campaign['analytics']['credentials']:
                oldcredentials = Credentials.new_from_json(campaign['analytics']['credentials'])
                print "OLD REFRESH TOKEN:" , oldcredentials.refresh_token
                credentials.refresh_token = oldcredentials.refresh_token
        accountdb.accounts.update({"_id": ObjectId(aid)}, {"$set": {"campaigns.%s.analytics" % cid: {"credentials": credentials.to_json(), "profiles": []}}})        
        
        ##todo lo siguiente no parece necesario
        print dir(credentials)
        print credentials.to_json()
        http = httplib2.Http()
        http = credentials.authorize(http)
        
        service = build('analytics', 'v3', http=http)
        profile_id = analytics_api.get_first_profile_id(service)
        ##todo lo anterior no parece necesario
        
        return u"Acceso a analytics (solo lectura) obtenido. Ya puede cerrar esta ventana y refrescar la ventana de administracion de la campaña"
    if "error" in request.args and request.args['error'] == "access_denied":
        return u"Acceso a analytics (solo lectura) revocado. Ya puede cerrar esta ventana y refrescar la ventana de administracion de la campaña"
    return "something went wrong"

@app.route('/api/account/user/create', methods=["GET"])
def create_user():
    account_id = request.args.get("account_id", "")
    username = request.args.get("username", "")
    password = request.args.get("password", "")
    access = request.args.get("access", "basic")
    if account_id and username and password:
        account = getAccount(account_id)
        if account:
            if not 'users' in account: account['users'] = {}
            user = {"username": username, "password": getPasswordHash(username, password), "access": access}
            
            account['users'][username] = user
            accountdb.accounts.save(account)
            return "Usuario %s creado" % username
    return "No se pudo crear el usuario"

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

@app.route('/dc/<account_id>/<datacollection_id>', methods=['GET'])
def datacollection_landing_page_get(account_id, datacollection_id):
    account = getAccount(account_id)
    if datacollection_id not in account['datacollections']:
        return "La página no existe", 404
    datacollection = account['datacollections'][datacollection_id]
    return render_template("datacollection_landing_pages/generic/datacollection_landing_page.html", dc = datacollection, account= account, datacollection_id = datacollection_id)

@app.route('/dc/<account_id>/<datacollection_id>', methods=['POST'])
def datacollection_landing_page_post(account_id, datacollection_id):
    account = getAccount(account_id)
    datacollection = account['datacollections'][datacollection_id]
    obj = {}
    obj['created_at'] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+00:00")
    fields = {}
    for f in datacollection['fields']:
        fields[f['name']] = request.form[f['name']]
    obj['fields'] = fields
    collection = "datacollection_%s" % datacollection_id
    accountdb[collection].insert(obj)
    return "GRABADO"

@app.route('/log/logins')
def logs_login():
    docs = accountdb.log_logins.find({}).sort("timestamp",-1).limit(20)
    lines = []
    for doc in docs:
        lines.append("%s: %s  --  %s" % (doc['timestamp'], doc['account_id'], doc['username']))
    return "<br>".join(lines)

@app.route('/api/trends/global/stopwords/add', methods=["POST"])
def global_trends_stop_words_add():
    user = getUser()
    if user and user.get('access', 'basic') == 'admin':
        lang = request.form["lang"]
        word = request.form["word"]
        if lang and word:
            sw = MongoManager.getGlobalTrendStopWords(lang)
            sw['words'].append(word)
            sw['words'] = list(set(sw['words'])) #para eliminar cualquier posible duplicado
            MongoManager.saveGlobalTrendStopWords(sw)
        return "OK"        
    return 'ACCESS ERROR'

@app.route('/feeds_explorer')
def feeds_explorer():
    campaign_id = request.args.get("campaign_id", "") #default Campana unilever
    account_id = request.args.get("account_id", "")
    object_id = request.args.get("object_id", "")
    sentiment = request.args.get("sentiment", "")
    account = getAccount(account_id)
    if account and not campaign_id: campaign_id = account['campaigns'].keys()[0]
    custom_css= request.args.get("css", None)
    campaign = account['campaigns'][campaign_id]        

    logo = "logo.jpg"
    logo2 = None        
    if str(account['_id']) == "5410f47209109a09a2b5985b": #sivale
        logo = "logoSivale.jpg"
        logo2 = "logoPromored.png"
    elif str(account['_id']) == "5476951e9babd3b93e31b9a9": #sony
        logo = "logoSony.jpg"
        logo2 = "logoLumia.jpg"
        
    own_brands_list = []
    for bid, brand in account['campaigns'][campaign_id]['brands'].items():
        if brand['own_brand']: own_brands_list.append(brand['name'])

    #topics = accountdb.topic.find({})[:]
    if 'topics' in campaign:
        topics = [y for x,y in campaign['topics'].items()]
    else:
        topics = []
    return render_template('app.html', custom_css = custom_css, content_template="feeds_explorer.html", js="feeds_explorer.js", account=account, user=getUser(account), campaign_id = campaign_id, campaign=campaign, logo=logo, logo2 = logo2, own_brands_list = '|'.join(own_brands_list), object_id=object_id, sentiment=sentiment, topics=topics, daterange=getDateRange(request))

@app.route('/api/feeds/search')
def search_feeds():
    start = request.args.get("start", "")
    end = request.args.get("end", "")
    text= request.args.get("text", "")
    source_twitter = request.args.get("source_twitter", "true").lower() == "true"
    source_facebook = request.args.get("source_facebook", "true").lower() == "true"
    source_forums = request.args.get("source_forums", "true").lower() == "true"
    campaign_id = request.args.get("campaign_id", "")
    brands_to_include = request.args.get("brands_to_include", "")
    filter_product = request.args.get("filter_product", "")
    filter_country = request.args.get("filter_country", "")
    filter_sentiment = request.args.get("filter_sentiment", "")
    filter_topic = request.args.get("filter_topic", "")
    skip = int(request.args.get("skip", 0))
    limit = int(request.args.get("limit", 80))
    object_id = request.args.get("object_id", "")
    count_only = bool(request.args.get("count_only", "false") == "true")
    include_sentiment_tagged_tweets = bool(request.args.get("include_sentiment_tagged_tweets", "true") == "true")
    res = {"feeds": [], "count": 0}
    if start and end and campaign_id:
        start = datetime.strptime(start + " 00:00:00", "%Y-%m-%d %H:%M:%S")
        end = datetime.strptime(end + " 23:59:59", "%Y-%m-%d %H:%M:%S")
        docfilter = { "retweeted_status": {"$exists": False}, "x_created_at": {"$gte": start, "$lte": end}}
        if not include_sentiment_tagged_tweets: docfilter['x_sentiment'] = {"$exists": False}
        if filter_sentiment:
            if filter_sentiment == "UNDEFINED":
                docfilter['x_sentiment'] = {'$exists': False}
            else:
                docfilter['x_sentiment'] = filter_sentiment
        if filter_country:                
            if filter_country == "UNDEFINED":
                docfilter['x_coordinates.country_code'] = {'$exists': False}
            else:
                docfilter['x_coordinates.country_code'] = filter_country
        if filter_topic:
            docfilter['x_extracted_topics.topic_name'] = filter_topic
        if text: docfilter['$text'] = {"$search": text}
        try:
            if object_id: docfilter['_id'] = ObjectId(object_id)
        except bson.errors.InvalidId:
            pass
        if filter_product:
            docfilter['x_extracted_info'] = {"$exists": True, "$elemMatch": {"product": filter_product, "confidence": {"$gt": 0}}}
        if brands_to_include:
            bti = [x.strip() for x in brands_to_include.split("|") if x.strip()]
            if not 'x_extracted_info' in docfilter: docfilter['x_extracted_info'] = {"$exists": True}
            if not '$elemMatch' in docfilter['x_extracted_info']: docfilter['x_extracted_info']['$elemMatch'] = {"confidence": {"$gt": 0}}
            docfilter['x_extracted_info']["$elemMatch"]["brand"] = {'$in': bti}
        #dbtweets = accountdb[collection_name].find(docfilter)
        if source_twitter:
            collection_name = "tweets_%s" % campaign_id        
            if count_only:
                res['count'] += MongoManager.countDocuments(collection_name, filters=docfilter)
            else:
                skipfilter = None
                if skip: skipfilter = skip
                dbtweets = MongoManager.findTweets(collection_name, filters=docfilter ,sort = ("x_created_at", -1), skip=skipfilter, limit=limit)
                #dbtweets = MongoManager.findFeeds(collection_name, filters=docfilter ,sort = ("x_created_at", -1), skip=skipfilter, limit=limit)
                res['feeds'].extend([t.getDictionary() for t in dbtweets])
        if source_forums:
            collection_name = "feeds_%s" % campaign_id        
            if count_only:
                res['count'] += MongoManager.countDocuments(collection_name, filters=docfilter)
            else:
                skipfilter = None
                if skip: skipfilter = skip
                dbtweets = MongoManager.findFeeds(collection_name, filters=docfilter ,sort = ("x_created_at", -1), skip=skipfilter, limit=limit)
                res['feeds'].extend([t.getDictionary() for t in dbtweets])
        if source_facebook:
            collection_name = "fb_posts_%s" % campaign_id        
            if count_only:
                res['count'] += MongoManager.countDocuments(collection_name, filters=docfilter)
            else:
                skipfilter = None
                if skip: skipfilter = skip
                dbtweets = MongoManager.findFBPosts(collection_name, filters=docfilter ,sort = ("x_created_at", -1), skip=skipfilter, limit=limit)
                res['feeds'].extend([t.getDictionary() for t in dbtweets])
            
    return flask.Response(dumps(res),  mimetype='application/json')

@app.route('/api/feeds/remove')
def remove_feed():
    campaign_id = request.args.get("campaign_id", "")
    feed_object_id = request.args.get("feed_object_id", "")
    res = {'result': 'error'}
    if campaign_id and feed_object_id:
        collection_name = "tweets_%s" % campaign_id
        accountdb[collection_name].remove({"_id": ObjectId(feed_object_id)})
        res['result']="ok"
    return flask.Response(dumps(res),  mimetype='application/json')

@app.route('/api/test/alive')
def test_alive():
    return flask.Response("ALIVE!", 200)

@app.route('/persons')
def persons():
    account_id = request.args.get("account_id", "")
    custom_css= request.args.get("css", None)
    account = getAccount(account_id)
    logo = "logo.jpg"
    logo2 = None
    if str(account['_id']) == "5410f47209109a09a2b5985b": #sivale
        logo = "logoSivale.jpg"
        logo2 = "logoPromored.png"
    elif str(account['_id']) == "5476951e9babd3b93e31b9a9": #sony
        logo = "logoSony.jpg"
        logo2 = "logoLumia.jpg"
    return render_template('app.html', custom_css = custom_css, content_template="persons.html", js="persons.js", account=account, user=getUser(account), logo=logo, logo2 = logo2, daterange=getDateRange(request))

@app.route('/api/persons/fetch_followers')
def persons_fetch_followers():
    account_id = request.args.get("account_id", "")
    twitter_accounts = request.args.get("twitter_accounts", "")
    twitter = Twython("1qxRMuTzu2I7BP7ozekfRw", "whQFHN8rqR78L6su6U32G6TPT7e7W2vCouR4inMfM", "2305874377-TTmvLjLuP8aq8q2bT7GPJsOjG9n6uYLAA0tvsYU", "iy4SYpkHK26Zyfr9RhYSGOLVtd9eMNF6Ebl2p552gF4vL")
    accs = [a.replace("@", "").strip() for a in twitter_accounts.split(",") if a.replace("@", "").strip()]
    users = []
    n = 0
    for acc in accs:
        nc = -1
        while nc != 0:
            followers = twitter.get_followers_list(screen_name = acc, count=200, cursor=nc)
            users.extend(followers['users'])
            nc = followers['next_cursor']
            n += 1
            if n >= 15: break
        if n >= 15: break

    res = {"ok": True, "users": users}
    return flask.Response(dumps(res),  mimetype='application/json')

if __name__ == "__main__":

    app.run(host="0.0.0.0", port=listenport)
