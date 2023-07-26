from flask import Flask, render_template, request, redirect, url_for
import os
import random
import threading
from turbo_flask import Turbo

app = Flask(__name__)
turbo = Turbo(app)

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/devices/')
def devices_home():
    return render_template("devices.html")
