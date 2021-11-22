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

factory = DynatraceMetricsFactory()
serializer = DynatraceMetricsSerializer(metric_key_prefix="billing",enrich_with_dynatrace_metadata=False)
consumptionMetrics=[]

# Query metric data
firstQuery = True
pageKey = None
while (firstQuery or pageKey is not None):
    firstQuery = False
    params = {
        "includeDetails": "false",
        "relativeTime": "hour"
    }
    if pageKey is not None:
        params["nextPageKey"]=pageKey
    response = requests.get(f"{dtEnvironment}/api/v1/oneagents", params, headers={"Authorization": f"api-token {dtApiToken}"}, verify=certVerify)
    if response.status_code==200:
        jr = response.json()
        pageKey = jr["nextPageKey"]
        for host in jr["hosts"]:
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
for i in range(0,len(consumptionMetrics), chunkSize):    
    # Uncomment to print metric lines
    # print("\n".join(consumptionMetrics[i:i+chunkSize]))
    metricResponse = requests.post(f"{dtEnvironment}/api/v2/metrics/ingest", data="\n".join(consumptionMetrics[i:i+chunkSize]), headers={"Authorization": f"api-token {dtApiToken}"}, verify=certVerify)
    if metricResponse.status_code!=202 or metricResponse.json()["linesInvalid"]>0:
        print(metricResponse.status_code)
        print(metricResponse.text)
