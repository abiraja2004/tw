import os
from pymongo import MongoClient
from bson import ObjectId
from brandclassifier import *
import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--auth', action="store_true", default=False)
args = parser.parse_args()
dbuser = "monitor"
dbpasswd = "monitor678"
mclient = MongoClient()
db = mclient['unilever']
if args.auth:
    db.authenticate(dbuser, dbpasswd)
monitor = mclient['monitor']
if args.auth:
    monitor.authenticate(dbuser, dbpasswd)
from flask import Flask, render_template, request
import flask 
import json

app = Flask(__name__)

knorr = KnorrClassifier()
ades = AdesClassifier()
axe = AXEClassifier()
iberia = IberiaClassifier()
jumex = JumexClassifier()
veet = VeetClassifier()
america = AmericaClassifier()

def highlightText(text, pm, d):
    res = text
    dd = d
    if min({-1: 99999}.get(pm.brand_matched_pos[0],pm.brand_matched_pos[0]), {-1: 99999}.get(pm.product_matched_pos[0],pm.product_matched_pos[0])) == pm.brand_matched_pos[0]:
        bl = len(res)
        res = res[:pm.brand_matched_pos[0]+dd] + "<B>" + pm.brand_matched_word + "</B>" + res[dd+pm.brand_matched_pos[1]:]
        dd = dd + len(res) - bl
        if pm.product:
            bl = len(res)
            res = res[:pm.product_matched_pos[0]+dd] + "<B>" + pm.product_matched_word + "</B>" + res[dd+pm.product_matched_pos[1]:]
            dd = dd + len(res) - bl            
    else:
        bl = len(res)
        res = res[:pm.product_matched_pos[0]+dd] + "<B>" + pm.product_matched_word + "</B>" + res[dd+pm.product_matched_pos[1]:]
        dd = dd + len(res) - bl
        if pm.brand:
            bl = len(res)
            res = res[:pm.brand_matched_pos[0]+dd] + "<B>" + pm.brand_matched_word + "</B>" + res[dd+pm.brand_matched_pos[1]:]
            dd = dd + len(res) - bl            
    return res

@app.route("/bootstrap")
def bootstrap():
	return render_template('bootstrap_example.html')
	
@app.route("/")
def root():
    from rulesmanager import getBrandClassifiers
    # MEXICO
    #[(-119.834226, 32.945683), (-105.068602, 31.608167), (-86.172119, 25.037495), (-86.084228, 19.094994), (-90.654540, 16.921944), (-93.027587, 13.102661), (-117.197508, 19.509744)]
    #dbtweets = db.tweets.find({"x_sentiment": {"$exists": False}, "lang": {"$eq": "es"}, "retweeted_status": {"$exists": False}}).limit(1000)
    #dbtweets = db.tweets.find({"text": re.compile("(ades|del valle|jumex)", re.I)}).limit(120)
    tpp = 120
    page = int(request.args.get('page',"1"))-1
    #dbtweets = db.tweets.find({ "retweeted_status": {"$exists": False}, "text": re.compile("(\\bades\\b)", re.I), "x_coordinates": { "$nearSphere": { "$geometry": { "type": "Point", "coordinates": [-99.1521845,19.3200988]}, "$maxDistance": 500000}}}).skip(page*tpp).limit(120)
    dbtweets = db.tweets.find({ "retweeted_status": {"$exists": False}}).sort("x_created_at", -1).skip(page*tpp).limit(120) 
    #tweets = db.tweets.find({"$and": [{'x_coordinates': {"$exists": True}}, {'x_coordinates': {"$ne": None}}, {'lang': {'$eq': 'es'}}]}).limit(120)
    tweets = []
    bcs = getBrandClassifiers()
    for t in dbtweets:
        pms = []
        #pms.extend(ades.extract(t['text']))
        #pms.extend(knorr.extract(t['text']))
        #pms.extend(axe.extract(t['text']))
        #pms.extend(iberia.extract(t['text']))
        for bc in bcs:
            #print bc.extract(t['text'])
            pms.extend(bc.extract(t['text']))
        if pms:
            ht = t['text']
            #pms.sort(key=lambda x: min({-1: 99999}.get(x.brand_matched_pos[0],x.brand_matched_pos[0]), {-1: 99999}.get(x.product_matched_pos[0],x.product_matched_pos[0])))
            pms.sort(key=lambda x: x.confidence, reverse=True)
            d = 0
            for pm in pms:
                bl = len(ht)
                ht = highlightText(ht, pm, d)
                d = d + len(ht) - bl
                
            t['x_extracted_info'] = pms
            t['x_highlighted_text'] = ht
        if pms or request.args.get('onlymatches', 'false') != "true":
            tweets.append(t)
    return render_template('rate_tweets.html', tweets=tweets)

@app.route("/account")
def account():
    account = monitor.accounts.find_one({"name":"Prueba"})
    return render_template('manage.html', account = account)

@app.route("/account/campaign")
def account_campaign():
    account = monitor.accounts.find_one({"name":"Prueba"})
    campaign_id = request.args['campaign_id']
    campaign = account['campaigns'][campaign_id]
    return render_template('campaign_container.html', account = account, campaign_id = campaign_id, campaign = campaign)
    

@app.route("/account/campaign/add", methods=['POST'])
def create_campaign():
    account = monitor.accounts.find_one({"_id": ObjectId(request.form['account_id'])})
    oid = str(ObjectId())
    account['campaigns'][oid] = {'brands': {}}
    monitor.accounts.update({"_id": ObjectId(request.form['account_id'])}, account)
    return oid

@app.route("/account/campaign/remove", methods=['POST'])
def remove_campaign():
    #account = monitor.accounts.find_one({"_id": ObjectId(request.form['account_id'])})
    monitor.accounts.update({"_id": ObjectId(request.form['account_id'])}, {"$unset": {"campaigns.%s" % (request.form['campaign_id']): "" }});
    return "OK"

@app.route("/account/campaign/brand/add", methods=['POST'])
def add_brand():
    #account = monitor.accounts.find_one({"_id": ObjectId(request.form['account_id'])})
    oid = ObjectId()
    monitor.accounts.update({"_id": ObjectId(request.form['account_id'])}, {"$set": {"campaigns.%s.brands.%s" % (request.form['campaign_id'], oid): {'products':{}}}});
    return str(oid)

@app.route("/account/campaign/brand/remove", methods=['POST'])
def remove_brand():
    #account = monitor.accounts.find_one({"_id": ObjectId(request.form['account_id'])})
    monitor.accounts.update({"_id": ObjectId(request.form['account_id'])}, {"$unset": {"campaigns.%s.brands.%s" % (request.form['campaign_id'], request.form['brand_id']): "" }});
    return "OK"

@app.route("/account/campaign/brand/product/add", methods=['POST'])
def add_product():
    #account = monitor.accounts.find_one({"_id": ObjectId(request.form['account_id'])})
    oid = ObjectId()
    monitor.accounts.update({"_id": ObjectId(request.form['account_id'])}, {"$set": {"campaigns.%s.brands.%s.products.%s" % (request.form['campaign_id'], request.form['brand_id'], oid): {}}});
    return str(oid)

@app.route("/account/campaign/brand/product/remove", methods=['POST'])
def remove_product():
    #account = monitor.accounts.find_one({"_id": ObjectId(request.form['account_id'])})
    monitor.accounts.update({"_id": ObjectId(request.form['account_id'])}, {"$unset": {"campaigns.%s.brands.%s.products.%s" % (request.form['campaign_id'], request.form['brand_id'], request.form['product_id']): ""}});
    return "OK"

@app.route("/account/campaign/update/name", methods=['POST'])
def update_campaign_name():
    monitor.accounts.update({"_id": ObjectId(request.form['account_id'])}, {"$set": {"campaigns.%s.name" % request.form['campaign_id']: request.form['value']}})
    return "OK"

@app.route("/search_keywordset", methods=['GET'])
def search_keywordset():
    res = []
    resultset = monitor.keywordset.find({"name": re.compile(request.args['term'], re.I|re.U)}).limit(100)
    for r in resultset:
        res.append({"value": r['name'], "id": str(r['_id']), 'label': r['name'] })
    return flask.Response(json.dumps(res),  mimetype='application/json')

@app.route("/account/campaign/brand/update", methods=['POST'])
def update_campaign_brand():
    v = request.form['value']
    if request.form['field'] == "keywords":
        v = processKeywords(v) 
    elif request.form['field'] == "identification_rules":
        v = processIdRules(v)        
    if request.form['field'] == "keyword_sets":
        v = processKeywordSets(v)            
    monitor.accounts.update({"_id": ObjectId(request.form['account_id'])}, {"$set": {"campaigns.%s.brands.%s.%s" % (request.form['campaign_id'],request.form['brand_id'], request.form['field']): v}})
    return "OK"

def processKeywords(kw):
    kw = kw.strip()
    if not kw: return []
    tups = kw.split("|")
    v = [w.split("%") for w in tups]
    v = [(vv[0].strip(), vv[1].strip()) for vv in v]
    return v

def processKeywordSets(kw):
    kw = kw.strip()
    if not kw: return []
    tups = kw.split("|")
    v = [w.split("%") for w in tups]
    v = [{"_id": ObjectId(vv[0].strip()), "name": vv[1].strip(), "value": int(vv[2].strip())} for vv in v]
    return v

def processIdRules(kw):
    v = [v.strip() for v in kw.strip().split("|") if kw.strip()]
    return v

@app.route("/account/campaign/brand/product/update", methods=['POST'])
def update_campaign_brand_product():
    v = request.form['value']
    if request.form['field'] == "keywords":
        v = processKeywords(v)
    elif request.form['field'] == "identification_rules":
        v = processIdRules(v)
    elif request.form['field'] == "keyword_sets":
        v = processKeywordSets(v)
    elif request.form['field'] == "use_brand_id_rules":
        v = bool(v == "on")
    monitor.accounts.update({"_id": ObjectId(request.form['account_id'])}, {"$set": {"campaigns.%s.brands.%s.products.%s.%s" % (request.form['campaign_id'],request.form['brand_id'],request.form['product_id'],request.form['field']): v}})
    return "OK"


@app.route('/js/<path:filename>')
def send_js(filename):
    return flask.send_from_directory('js', filename)

@app.route('/styles/<path:filename>')
def send_style(filename):
    return flask.send_from_directory('styles', filename)


@app.route("/showtweet2", methods=['GET'])
def showtweet2():
    tweet = db.tweets.find_one({"_id": ObjectId(request.args['id'])})
    tweet['_id'] = str(tweet['_id'])
    return flask.jsonify(**tweet)

@app.route("/rate", methods=['POST'])
def rate():
    print request.form['id'], request.form['sent']
    print db.tweets.update({"_id": ObjectId(request.form['id'])}, {"$set": {"x_sentiment": request.form['sent']}})    
    return "OK"

  
if __name__ == "__main__":
    app.debug = True
    app.run(host="0.0.0.0")



"""
for t in db.tweets.find({"$and": [{'x_coordinates': {"$exists": True}}, {'x_coordinates': {"$ne": None}}, {'lang': {'$eq': 'es'}}]}):
  print
  print '@' + t['user']['screen_name'] 
  print t['text']
  v = raw_input("Sentiment [Positivo (+)/Negativo (-)/Neutral (=) / Not sure (?) / Quit (q)] Default: q? ").lower()
  if v == "q": exit(0)
  elif v == "+": 
    db.tweets.update({"_id": t["_id"]}, {"$set": {"x_sentiment": "+"}})
  elif v == "-": 
    db.tweets.update({"_id": t["_id"]}, {"$set": {"x_sentiment": "-"}})
  elif v == "=": 
    db.tweets.update({"_id": t["_id"]}, {"$set": {"x_sentiment": "="}})
  elif v == "=": 
    db.tweets.update({"_id": t["_id"]}, {"$set": {"x_sentiment": null}})
"""