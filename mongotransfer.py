from pymongo import MongoClient
remotedb = MongoClient("prodedelmundial.com.ar")
localdb = MongoClient("127.0.0.1")
remote = remotedb['datasiftmongodb']
remote.authenticate("pablo", "1234")
local = localdb['datasiftmongodb']

#tweets = remote.my_first_test.find({}).skip(250000).limit(350000)
k = 0
for t in tweets:
    local.my_first_test.insert(t)
    k +=1
    print k