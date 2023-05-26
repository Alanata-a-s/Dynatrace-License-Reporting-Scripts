import os
import json
import requests

from dynatrace.metric.utils import (
    DynatraceMetricsSerializer,
    DynatraceMetricsFactory,
    MetricError,
    DynatraceMetricsApiConstants,
)

dtClusterApiToken=os.environ.get("DT_CLUSTER_APITOKEN")
dtCluster=os.environ.get("DT_CLUSTER")
dtEnvironmentApiToken=os.environ.get("DT_ENVIRONMENT_APITOKEN")
dtEnvironment=os.environ.get("DT_ENVIRONMENT")
dtDryRun=os.environ.get("DT_DRYRUN", False)

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
serializer = DynatraceMetricsSerializer(metric_key_prefix="billing.environments",enrich_with_dynatrace_metadata=False)
consumptionMetrics=[]


# Query metric data
firstQuery = True
pageKey = None
while (firstQuery or pageKey is not None):
    firstQuery = False
    params = {
        "includeConsumptionInfo": "true",
        "includeUncachedConsumptionInfo": "true"
    }
    if pageKey is not None:
        params["nextPageKey"]=pageKey
    response = requests.get(f"{dtCluster}/api/cluster/v2/environments", params, headers={"Authorization": f"api-token {dtClusterApiToken}"}, verify=certVerify)
    if response.status_code==200:
        jr = response.json()
        pageKey = jr.get("nextPageKey")
        for env in jr["environments"]:
            dimensions = {}
            try:
                dimensions["environment"]=env.get("name")
                dimensions["id"]=env.get("id")
                dimensions["state"]=env.get("state")
            except KeyError:
                pass

            metricKeys = {
                "hostUnits.current_usage": env['quotas']['hostUnits']['currentUsage'],
                "demUnits.consumedThisMonth": env['quotas']['demUnits']['consumedThisMonth'],
                "demUnits.consumedThisYear": env['quotas']['demUnits']['consumedThisYear'],
                "davisDataUnits.consumedThisMonth": env['quotas']['davisDataUnits']['consumedThisMonth'],
                "davisDataUnits.consumedThisYear": env['quotas']['davisDataUnits']['consumedThisYear'],
            }
            metricMetadata = {
                "hostUnits.current_usage": { "dt.meta.displayName": "Host units - current environment usage" },
                "demUnits.consumedThisMonth": { "dt.meta.displayName": "DEM units - consumed this month" },
                "demUnits.consumedThisYear": { "dt.meta.displayName": "DEM units - consumed this year" },
                "davisDataUnits.consumedThisMonth": { "dt.meta.displayName": "Davis Data Units - consumed this month" },
                "davisDataUnits.consumedThisYear": { "dt.meta.displayName": "Davis Data Units - consumed this year" },
            }

            for metricKey in metricKeys:
                try:                   
                    metric = factory.create_float_gauge(metric_name=metricKey, value=metricKeys.get(metricKey), dimensions={ **dimensions, **metricMetadata.get(metricKey)})
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
            consumptionMetrics[i:i+chunkSize]), headers={"Authorization": f"api-token {dtEnvironmentApiToken}"}, verify=certVerify)
        if metricResponse.status_code != 202 or metricResponse.json()["linesInvalid"] > 0:
            print(metricResponse.status_code)
            print(metricResponse.text)    

