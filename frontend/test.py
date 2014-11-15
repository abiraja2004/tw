
from flask import Flask
application = Flask(__name__)
application.config['PROPAGATE_EXCEPTIONS'] = True

@application.route('/')
def hello_world():
    aksjhdkjasdhjas
    return 'Hello World!'
