#!/usr/bin/env python3
from flask import Flask, render_template, send_file, send_from_directory, request, Markup, redirect, url_for
app = Flask(__name__)


retrospectives = dict()

class Retrospective():
    COMMENT_TYPES = ["good", "bad", "suggestion", "thanks"]
    def __init__(self, name):
        self.name = name
        self.comments = { k:[] for k in self.COMMENT_TYPES }
    def add(self, kind, comment):
        if kind in self.COMMENT_TYPES:
            self.comments[kind].append(comment)

@app.route("/")
def index():
    return render_template("index.html", retrospectives=retrospectives.keys())

@app.route('/retrospective/<name>')
def retrospective(name):
    return render_template("retrospective.html", this=retrospectives[name]) 

@app.route('/new', methods=['POST'])
def newRetrospective():
    if request.method == 'POST':
        name = request.form['name']
        if name in retrospectives:
            raise Exception("Invalid method")
        retrospectives[name] = Retrospective(name)
        return redirect(url_for("retrospective", name=name))
    else:
        raise Exception("Invalid method")

@app.route('/comment/<name>')
def comment(name):
    if name in retrospectives:
        return render_template("comment.html", this=retrospectives[name])

@app.route('/newcomment/<name>', methods=["POST"])
def newComment(name):
    if name in retrospectives:
        if request.method == 'POST':
            kind = request.form['type']
            message = request.form['comment']
            retrospectives[name].add(kind, message)
            return redirect(url_for("comment", name=name))

@app.route('/join', methods=["POST"])
def join():
    if request.method == 'POST':
        name = request.form['name']
        return redirect(url_for("comment", name=name))
    else:
        raise Exception("Invalid method")

@app.route("/static/")
def img():
    return send_from_directory('img', path)

if __name__ == "__main__":
    app.run()
