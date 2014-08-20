from pymongo import MongoClient
from bson import ObjectId
mongoclient = MongoClient("prodedelmundial.com.ar")
db = mongoclient['test']
datasift = mongoclient['datasiftmongodb']
from flask import Flask, render_template, request
import flask 

app = Flask(__name__)

@app.route("/")
def home():
    tweets = db.tweets.find({"x_sentiment": {"$exists": False}, "lang": {"$eq": "es"}, "x_coordinates": {"$ne": None}}).limit(120) 
    #tweets = db.tweets.find({"$and": [{'x_coordinates': {"$exists": True}}, {'x_coordinates': {"$ne": None}}, {'lang': {'$eq': 'es'}}]}).limit(120)
    return render_template('rate_tweets.html', tweets=tweets)

@app.route("/rate", methods=['POST'])
def rate():
    print request.form['id'], request.form['sent']
    print db.tweets.update({"_id": ObjectId(request.form['id'])}, {"$set": {"x_sentiment": request.form['sent']}})    
    return "OK"

@app.route("/explore", methods=['GET'])
def explore():
    cnt = 30
    page = int(request.args.get("page", "1"))
    if page < 1: page = 1
    search = request.args.get("search", "")
    lang = request.args.get("lang", "")
    cond = {}
    if search: cond = {"$text": {"$search": search}}
    if lang: cond['lang2'] = lang
    print cond
    tweets = datasift.my_first_test.find(cond).skip((page-1)*cnt).limit(30)
    return render_template('explore_tweets.html', tweets=tweets, page=page)

@app.route("/showtweet", methods=['GET'])
def showtweet():
    tweet = datasift.my_first_test.find_one({"_id": ObjectId(request.args['id'])})
    tweet['_id'] = str(tweet['_id'])
    return flask.jsonify(**tweet)
  
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