from geopy.geocoders import *
import time
import cPickle
import datetime
import geopy.geocoders
#print dir(geopy.geocoders)
from pprint import pprint
from pymongo import MongoClient
mongoclient = MongoClient()
#geolocator = Nominatim() #OK
geolocator = GoogleV3() #OK
#geolocator = OpenMapQuest() # OK
#geolocator = OpenCage("3bbbbd5b224ee0abdf0d1b9725bbe623") # OK
#geolocation = Bing("AlClmhhZu3D3SLnW_IcYNakDkn1dtDh91DMiXnkA86NOJQVw2ZcFkDi5qRpelpFp") #OK
#geolocator = ArcGIS() # OK
#geolocator = GeoNames(username="pdbpdb") # OK
#geolocator = GeocodeFarm("b0d5ca4124e2285d917b640976d3a1af354185e9") # OK
#geolocator = MapQuest("Fmjtd%7Cluur25ur29%2C20%3Do5-9w75q4") # OK? por ahora no

db = mongoclient['test']

r = 0
gr = None
k = 0
for f in db.tweets.find({'x_coordinates': {"$exists": False}}):
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
      if gr: print k, gr['requests'],
      print loc, " -> ",
      if loc and isinstance(loc, basestring):
	cached = db.places.find_one({'text': loc.strip().lower()})
	if not cached:		
	  try:
	    try:
	      gr = cPickle.load(open("google_requests","rb"))
	    except:
	      gr = {"date": datetime.date.today(), "requests": 0}
	    if gr['date'] == datetime.date.today() and gr['requests'] > 2400:
	      print "Google daily request limit reached."
	      exit(0)
	    elif gr['date'] < datetime.date.today():
	      gr['requests'] = 0
	      gr['date'] = datetime.date.today()
	    r += 1
	    if r > 9: 
		print "Waiting 1 sec..."
		time.sleep(1)
		r = 0	      
	    geo_calculated_location = geolocator.geocode(loc)
	    if geo_calculated_location:
	      calculated_location = {}
	      calculated_location['text'] = loc.strip().lower()
	      calculated_location['address'] = geo_calculated_location.address
	      calculated_location['longitude'] = geo_calculated_location.longitude
	      calculated_location['latitude'] = geo_calculated_location.latitude
	      db.places.insert(calculated_location)
	      calculated_location['cache'] = False	      
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
	  if calculated_location: print calculated_location['address'],
	  print coordinates, " (from %s) -%s-" % (origin, calculated_location['cache'])
	  db.tweets.update({"_id": f["_id"]}, {"$set": {"x_coordinates": {"type": "point", "coordinates": coordinates}, "x_coordinates_origin": origin}})
      else:
	  print "not found"
	  db.tweets.update({"_id": f["_id"]}, {"$set": {"x_coordinates": None, "x_coordinates_origin": None}})
	  


