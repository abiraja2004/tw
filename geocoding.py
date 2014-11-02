from geopy.geocoders import *
import re
import time
import cPickle
import datetime
from datetime import timedelta
import geopy.geocoders
from pprint import pprint
from pymongo import MongoClient
import argparse

geolocator = GoogleV3() #OK


parser = argparse.ArgumentParser()
parser.add_argument('--auth', action="store_true", default=False)
args = parser.parse_args()
dbuser = "monitor"
dbpasswd = "monitor678"
mclient = MongoClient()
monitor = mclient['monitor']
if args.auth:
    monitor.authenticate(dbuser, dbpasswd)


r = 0
gr = None
k = 0
w = 0

limitperiod = timedelta(days=1, minutes=1)
max_requests_per_period = 2400

limitperiod = timedelta(seconds=5)
max_requests_per_period = 20

def geolocate(account, cid):
    global gr,r,k,w, limitperiod
    campaign = account['campaigns'][cid]
    print "fetching locations for campaign: %s (%s) from account %s" % (campaign['name'],cid,  account['name'])
    collection_name = "tweets_%s" % cid
    collection = monitor[collection_name]
    for f in collection.find({'x_coordinates': {"$exists": False}}):    
        loc = None
        coordinates = f['coordinates']
        origin = "coordinates"
        calculated_location = None
        if not coordinates:
            loc = None
        if not loc: 
            loc = f['place']
            origin = "place"
        if not loc:
            loc = f['user']['location']
            origin = "user.location"
        if gr: print k, w, gr['requests'],
        print loc, " -> ",
        if loc and isinstance(loc, basestring):
            cached = monitor.places.find_one({'text': loc.strip().lower()})
            if not cached:      
                try:
                    try:
                        gr = cPickle.load(open("google_requests","rb"))
                    except:
                        gr = {"date": datetime.date.today(), "requests": 0}
                    if (datetime.date.today() - gr['date']) < limitperiod and gr['requests'] >= max_requests_per_period:
                        print "Google daily request limit reached. waiting %s" % limitperiod
                        #time.sleep() #espero 1 dia + 1 minuto
                        time.sleep(3600*limitperiod.days + limitperiod.seconds) #espero el periodo
                        gr['requests'] = 0
                        gr['date'] = datetime.date.today()
                    elif not ((datetime.date.today() - gr['date']) < limitperiod):
                        gr['requests'] = 0
                        gr['date'] = datetime.date.today()
                    r += 1
                    if r > 8: 
                        print "Waiting 1 sec..."
                        time.sleep(1.1)
                        r = 0         
                        geo_calculated_location = geolocator.geocode(loc)
                        if geo_calculated_location:
                            calculated_location = {}
                            calculated_location['text'] = loc.strip().lower()
                            calculated_location['address'] = geo_calculated_location.address
                            calculated_location['longitude'] = geo_calculated_location.longitude
                            calculated_location['latitude'] = geo_calculated_location.latitude
                            monitor.places.insert(calculated_location)
                            calculated_location['cache'] = False          
                        else:
                            w += 1
                finally:
                    gr['requests'] += 1
                    cPickle.dump(gr, open("google_requests","wb"))
            else:
                calculated_location = cached
                calculated_location['cache'] = True
            
        if calculated_location:
            coordinates = [calculated_location['longitude'], calculated_location['latitude']]
        
        
        if coordinates:
            k += 1
            if calculated_location: 
                print calculated_location['address'],
                print coordinates, " (from %s) -%s-" % (origin, calculated_location['cache'])
            else:
                print coordinates, " from tweet coordinates"
            collection.update({"_id": f["_id"]}, {"$set": {"x_coordinates": {"type": "Point", "coordinates": coordinates}, "x_coordinates_origin": origin}})
        else:
            print "not found"
            collection.update({"_id": f["_id"]}, {"$set": {"x_coordinates": None, "x_coordinates_origin": None}})
        
if __name__ == "__main__":
    while True:
        for account in monitor.accounts.find({}):
            for cid, campaign in account['campaigns'].items():
                if 'use_geolocation' in campaign and campaign['use_geolocation']:
                    geolocate(account, cid)
        time.sleep(10)
            
            
