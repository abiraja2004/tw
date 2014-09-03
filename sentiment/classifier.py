import nltk
from nltk import word_tokenize
from nltk.corpus import stopwords
from pymongo import MongoClient
mongoclient = MongoClient("127.0.0.1")
db = mongoclient['datasiftmongodb']
#db.authenticate("pablo", "1234")
collection = db['my_first_test']

TRAIN = 200
TEST = 20
dbtweets_train = collection.find({"$or": [{"interaction.salience.content.sentiment": {"$gt": 0}}, {"interaction.salience.content.sentiment": {"$lt": 0}}]}, {"interaction.interaction.content": 1, "interaction.salience.content.sentiment": 1}).limit(TRAIN)
dbtweets_test = collection.find({"$or": [{"interaction.salience.content.sentiment": {"$gt": 0}}, {"interaction.salience.content.sentiment": {"$lt": 0}}]}, {"interaction.interaction.content": 1, "interaction.salience.content.sentiment": 1}).skip(TRAIN).limit(TEST)

def make_set(dbtweet_list):
  res = []
  for t in dbtweet_list:
    try:
      content = t['interaction']['interaction']['content']
      sentiment = int(t['interaction']['salience']['content']['sentiment'])
      sent = None
      if sentiment < 0: 
	  sent = "negative"
      elif sentiment > 0:
	  sent = "positive"
      if sent:
	  res.append((word_tokenize(content), sent))
    except KeyError, e:
      continue
  return res

training_tweets = make_set(dbtweets_train)
test_tweets = make_set(dbtweets_test)

def get_words_in_tweets(tweets):
    all_words = []
    for (words, sentiment) in tweets:
      all_words.extend(words)
    return all_words

def get_word_features(wordlist):
    wordlist = nltk.FreqDist(wordlist)
    print wordlist
    word_features = [w for w in wordlist.keys() if w not in stopwords.words("spanish")]
    return word_features
 
#wordlist = ["mal", "malo", "bueno", "buen", "genial", "excelente", "mierda", "ladron", "genio"]
word_features = get_word_features(get_words_in_tweets(training_tweets))
#word_features = get_word_features(wordlist)

def extract_features(document):
    document_words = set(document)
    features = {}
    for word in word_features:
        features['contains(%s)' % word] = (word in document_words)
    return features
  
training_set = nltk.classify.apply_features(extract_features, training_tweets)
test_set = nltk.classify.apply_features(extract_features, test_tweets)
#print test_set
classifier = nltk.NaiveBayesClassifier.train(training_set)

print classifier.show_most_informative_features(32)


print nltk.classify.accuracy(classifier, test_set)