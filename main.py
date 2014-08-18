from twitter import Twitter
import cPickle

new_request = False
if new_request:
  twitter = Twitter.getTwitter()
  q = twitter.search(q='python')
  f = open("obj.txt", 'wb')
  cPickle.dump(q,f) 
else:
  f = open("obj.txt", 'rb')
  q = cPickle.load(f)
print dir(q)
print
print
print q.keys()
print
print
print q['statuses'][0].keys()
print
print
for t in q['statuses']:
  print t['geo'], t['coordinates'], t['place'], t['user']['location']
print
print
t = q['statuses'][10]['user']
print t.keys()
print t['geo_enabled']
print t['location']
print t['description']
print t['name']
