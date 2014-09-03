from flask import Flask, render_template, request, Blueprint
import flask 
import json

app = Flask(__name__)

@app.route("/")
def home():
    return render_template('manage.html')

"""
@app.route('/html/<path:filename>')
def send_js(filename):
    return flask.send_from_directory('html', filename)
"""

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

@app.route('/<path:filename>')
def html_folder(filename):
    return flask.send_from_directory(app.root_path + '/html/', filename)

if __name__ == "__main__":
    app.debug = True
    app.run(host="0.0.0.0", port=5001)

