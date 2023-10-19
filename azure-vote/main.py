from flask import Flask, request, render_template
import os
import redis
import socket
import logging

# App Insights
# TODO: Import required libraries for App Insights
from opencensus.ext.azure.log_exporter import AzureLogHandler
from opencensus.ext.azure.trace_exporter import AzureExporter
from opencensus.trace.samplers import ProbabilitySampler
from opencensus.trace.tracer import Tracer
from opencensus.ext.flask.flask_middleware import FlaskMiddleware
from opencensus.trace import config_integration
from opencensus.ext.azure.log_exporter import AzureEventHandler
from opencensus.ext.azure import metrics_exporter
from opencensus.stats import stats as stats_module



# MOVE TO SECRETS FOR PRODUCTION!
instrumentation_key = "acb6a5f1-1598-40c0-aec9-7b755e4804cd"


# For metrics
stats = stats_module.stats
view_manager = stats.view_manager


config_integration.trace_integrations(['logging'])
config_integration.trace_integrations(['requests'])

# Logging
# TODO: Setup logger
logger = logging.getLogger(__name__)
handler = AzureLogHandler(connection_string=f"InstrumentationKey={instrumentation_key}")
handler.setFormatter(logging.Formatter('%(message)s'))
logger.addHandler(handler)
# Logging custom Events 
logger.addHandler(AzureEventHandler(connection_string=f"InstrumentationKey={instrumentation_key}"))
# Set the logging level
logger.setLevel(logging.INFO)

# Metrics
# TODO: Setup exporter
# NEED TO CONFIGURE APPLICATIONINSIGHTS_CONNECTION_STRING
exporter = metrics_exporter.new_metrics_exporter(
  enable_standard_metrics=True,
  connection_string=f"InstrumentationKey={instrumentation_key}")
view_manager.register_exporter(exporter)

# Tracing
tracer = Tracer(
    exporter=AzureExporter(
        connection_string=f"InstrumentationKey={instrumentation_key}"),
    sampler=ProbabilitySampler(1.0),
)

app = Flask(__name__)

# Requests
# TODO: Setup flask middleware
middleware = FlaskMiddleware(
    app,
    exporter=AzureExporter(
        connection_string=f"InstrumentationKey={instrumentation_key}"
    ),
    sampler=ProbabilitySampler(rate=1.0),
)

# Load configurations from environment or config file
app.config.from_pyfile("config_file.cfg")

if "VOTE1VALUE" in os.environ and os.environ["VOTE1VALUE"]:
    button1 = os.environ["VOTE1VALUE"]
else:
    button1 = app.config["VOTE1VALUE"]

if "VOTE2VALUE" in os.environ and os.environ["VOTE2VALUE"]:
    button2 = os.environ["VOTE2VALUE"]
else:
    button2 = app.config["VOTE2VALUE"]

if "TITLE" in os.environ and os.environ["TITLE"]:
    title = os.environ["TITLE"]
else:
    title = app.config["TITLE"]

# Redis Connection
r = redis.Redis()

# Change title to host name to demo NLB
if app.config["SHOWHOST"] == "true":
    title = socket.gethostname()

# Init Redis
if not r.get(button1):
    r.set(button1, 0)
if not r.get(button2):
    r.set(button2, 0)


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        # Get current values
        vote1 = r.get(button1).decode("utf-8")
        # TODO: use tracer object to trace cat vote
        with tracer.span(name="Cats Vote") as span:
            print("Cats Vote")

        vote2 = r.get(button2).decode("utf-8")
        # TODO: use tracer object to trace dog vote
        with tracer.span(name="Dogs Vote") as span:
            print("Dogs Vote")

        # Return index with values
        return render_template(
            "index.html",
            value1=int(vote1),
            value2=int(vote2),
            button1=button1,
            button2=button2,
            title=title,
        )

    elif request.method == "POST":
        if request.form["vote"] == "reset":
            # Empty table and return results
            r.set(button1, 0)
            r.set(button2, 0)
            vote1 = r.get(button1).decode("utf-8")
            properties = {"custom_dimensions": {"Cats Vote": vote1}}
            # TODO: use logger object to log cat vote
            logger.info("Cats Vote", extra=properties)

            vote2 = r.get(button2).decode("utf-8")
            properties = {"custom_dimensions": {"Dogs Vote": vote2}}
            # TODO: use logger object to log dog vote
            logger.info("Dogs Vote", extra=properties)

            return render_template(
                "index.html",
                value1=int(vote1),
                value2=int(vote2),
                button1=button1,
                button2=button2,
                title=title,
            )

        else:
            # Insert vote result into DB
            vote = request.form["vote"]
            r.incr(vote, 1)

            vote0 = r.get(vote).decode('utf-8')
            
            # log current vote
            properties = {'custom_dimensions': {'{}_vote'.format(vote): vote0}}
            logger.info('new_{}_vote'.format(vote), extra=properties)
            
            # Get current values
            vote1 = r.get(button1).decode('utf-8')
            properties = {'custom_dimensions': {'Cats Vote': vote1}}
            # TODO: use logger object to log cat vote
            logger.info('Cats Vote', extra=properties)

            vote2 = r.get(button2).decode('utf-8')
            properties = {'custom_dimensions': {'Dogs Vote': vote2}}
            # TODO: use logger object to log dog vote
            logger.info('Dogs Vote', extra=properties) 

            # Return results
            return render_template(
                "index.html",
                value1=int(vote1),
                value2=int(vote2),
                button1=button1,
                button2=button2,
                title=title,
            )


if __name__ == "__main__":
    # TODO: Use the statement below when running locally
    # app.run()
    # TODO: Use the statement below before deployment to VMSS
    app.run(host="0.0.0.0", threaded=True, debug=True)  # remote
