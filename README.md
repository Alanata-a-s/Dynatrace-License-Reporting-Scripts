# Dynatrace License Metrics

A simple python script to introduce license metrics. It is intended to be executed on hourly basis.

Following metrics are created:

- `billing.hostunit.consumption`

# Usage:
1. Install Python dependencies

        pip3 install dynatrace-metric-utils
        pip3 install dt

2. Prepare environment variables
- `DT_ENVIRONMENT` - URL to Dynatrace environment such as https://xxx123.dynatrace-managed.com/e/18b37a6a-c0bf-4cef-9f76-3ad018986bfe
- `DT_APITOKEN` - Dynatrace API token with scope of API v2 - Ingest Metrics and API v1 - Access problem and event feed, metrics and topology.


3. Use cron for executing the script on hourly basis

        0 * * * * DT_APITOKEN="<place>" DT_ENVIRONMENT="<environment>" python3 /path/to/licenseHUmetric.py
