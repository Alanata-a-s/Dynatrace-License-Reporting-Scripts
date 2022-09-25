import os
import requests
from pprint import pprint
from dynatrace.metric.utils import (
    DynatraceMetricsSerializer,
    DynatraceMetricsFactory,
    MetricError,
    DynatraceMetricsApiConstants,
)

dtApiToken=os.environ.get("DT_APITOKEN")
dtEnvironment=os.environ.get("DT_ENVIRONMENT")
dtCertVerify=os.environ.get("DT_CERTVERIFY")
certVerify=True
if dtCertVerify is not None:
    if dtCertVerify.lower()=="false":
        certVerify=False
    elif dtCertVerify.lower()=="true":
        certVerify=True
    else:
        certVerify=dtCertVerify
dtRelativeTime=os.environ.get("DT_RELATIVETIME", "hour")
if (os.environ.get("DT_DRYRUN", "false").lower()=="true"):
    dtDryRun = True
else:
    dtDryRun = False
if (os.environ.get("DT_UNMONITORED_EVENTS", "true").lower()=="true"):
    dtUnmonitoredEvents = True
else: 
    dtUnmonitoredEvents = False
dtUnmonitoredEventTitle=os.environ.get("DT_UNMONITORED_EVENT_TITLE","Host is unmonitored")
dtUnmonitoredEventSeverity=os.environ.get("DT_UNMONITORED_EVENT_SEVERITY", "AVAILABLITY_EVENT")
dtUnmonitoredEventTimeout=os.environ.get("DT_UNMONITORED_EVENT_TIMEOUT", "3600")

factory = DynatraceMetricsFactory()
serializer = DynatraceMetricsSerializer(metric_key_prefix="billing",enrich_with_dynatrace_metadata=False)
consumptionMetrics=[]
disabledHosts=[]

# Query metric data
firstQuery = True
pageKey = None
while (firstQuery or pageKey is not None):
    firstQuery = False
    params = {
        "includeDetails": "false",
        "relativeTime": dtRelativeTime
    }
    if pageKey is not None:
        params["nextPageKey"]=pageKey
    response = requests.get(f"{dtEnvironment}/api/v1/oneagents", params, headers={"Authorization": f"api-token {dtApiToken}"}, verify=certVerify)
    if response.status_code==200:
        jr = response.json()
        pageKey = jr["nextPageKey"]
        for host in jr["hosts"]:
            # Find disabled hosts
            try:
                if host['availabilityState']=="UNMONITORED":
                    disabledHosts.append(host['hostInfo']['entityId'])
            except KeyError:
                pass

            # Provide HU consumption metric value
            dimensions = {}
            try:
                dimensions["dt.entity.host"]=f"{host['hostInfo']['entityId']}"
                dimensions["configuredMonitoringMode"]=f"{host['configuredMonitoringMode']}"
                dimensions["availabilityState"]=f"{host['availabilityState']}"
                dimensions["monitoringType"]=f"{host['monitoringType']}"
                dimensions["detailedAvailabilityState"]=f"{host['detailedAvailabilityState']}"
                dimensions["monitoringMode"]=f"{host['hostInfo']['monitoringMode']}"
            except KeyError:
                pass
            try:
                metric = factory.create_int_gauge("hostunit.consumption", 
                    host['hostInfo']['consumedHostUnits'], 
                    dimensions)
                consumptionMetrics.append(serializer.serialize(metric))
            except MetricError as err:
                print("MetricError", err)
    else:
        print(response.text)
        pageKey=None

# Post metric data
chunkSize = 500
for i in range(0, len(consumptionMetrics), chunkSize):
    if (dtDryRun):
        print("\n".join(consumptionMetrics[i:i+chunkSize]))
    else: 
        metricResponse = requests.post(f"{dtEnvironment}/api/v2/metrics/ingest", data="\n".join(
            consumptionMetrics[i:i+chunkSize]), headers={"Authorization": f"api-token {dtApiToken}"}, verify=certVerify)
        if metricResponse.status_code != 202 or metricResponse.json()["linesInvalid"] > 0:
            print(metricResponse.status_code)
            print(metricResponse.text)    

if (dtUnmonitoredEvents):
    # Check disabled hosts to validate if disabled intentionally and send events
    for host in disabledHosts:
        response = requests.get(f"{dtEnvironment}/api/v2/settings/effectiveValues", params={
                                "schemaIds": "builtin:host.monitoring", "scope": host}, 
                                headers={"Authorization": f"api-token {dtApiToken}"}, verify=certVerify)
        if response.status_code == 200:
            for hostMonitoringConfig in response.json()["items"]:
                if hostMonitoringConfig['value']['enabled']:
                    event = {
                        "eventType": dtUnmonitoredEventSeverity,
                        "title": dtUnmonitoredEventTitle,
                        "timeout": dtUnmonitoredEventTimeout,
                        "entitySelector": f"type(HOST),entityId({host})",
                        "properties": {
                            "Actual monitoring state": "UNMONITORED",
                            "Desired monitoring state": "enabled",
                            "Desired fullstack mode": hostMonitoringConfig['value']['fullStack'],
                            "Desired autoinjection mode": hostMonitoringConfig['value']['autoInjection']
                        }
                    }
                    if (dtDryRun):
                        print(f"Will send event {event}")
                    else:
                        response = requests.post(f"{dtEnvironment}/api/v2/events/ingest", json=event, 
                                headers={"Authorization": f"api-token {dtApiToken}"}, verify=certVerify)
                        if response.status_code!=201:
                            print(f"Error while sending event for {host}, {response}")                
