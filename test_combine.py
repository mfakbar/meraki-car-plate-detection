from flask import Flask
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from flask_server import mainApp as mainApp
from test_card_server import webexApp as webexApp
from werkzeug.serving import run_simple

application = DispatcherMiddleware(mainApp, {
    '/card_action': webexApp
})

if __name__ == '__main__':
    run_simple('localhost', 5000, application, use_reloader=True,
               use_debugger=True, use_evalex=True)
