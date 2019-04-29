#!/home/httpd/vhosts/trajtest.mcdir.ru/private/venvs/myvenv/bin/python
# coding: utf-8

from __future__ import unicode_literals
from main import elephant
import logging

from flask import Flask

app = Flask(__name__)


logging.basicConfig(level=logging.DEBUG)

app.register_blueprint(elephant)
# app.run()

app.debug = False
@app.route("/", methods=['POST', 'GET'])
def main():
    return 'I AM ANDREY'

if __name__ == "__main__":
    app.run()