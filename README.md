# Dynatrace License Metrics

A simple python script to introduce license metrics and sending events about unmonitored hosts if unmonitored unintentionally. It is intended to be executed on hourly basis by default. 

Following metrics are created:

- `billing.hostunit.consumption`

If OneAgent on a host has UNMONITORED status, script verifies if the agent is set to enabled and sends problem opening events to trigger problem in Dynatace.

# Usage:
1. Install Python dependencies

        pip3 install dynatrace-metric-utils
        
2. Create API token
API token with following scopes must be created:
- API v2 - Ingest Metrics
- API v2 - Read Settings
- API v2 - Ingest events
- API v1 - Access problem and event feed, metrics and topology

3. Prepare environment variables
- `DT_ENVIRONMENT` - URL to Dynatrace environment such as https://xxx123.dynatrace-managed.com/e/18b37a6a-c0bf-4cef-9f76-3ad018986bfe
- `DT_APITOKEN` - Dynatrace API token 
- `DT_CERTVERIFY` - Set to `true` or `false` to enable/disable cerificate validation or set to path to CA certificate bundle file (PEM)
- `DT_RELATIVETIME` - Relative time to fetch data back, defaults to **hour**, possible values min, 5mins, 10mins, 15mins, 30mins, hour, 2hours, 6hours, day, 3days, month, week
- `DT_DRYRUN` - Set to True for a dry-run execution (no data is sent to Dynatrace)
- `DT_UNMONITORED_EVENTS` - Determines if events about unmonitored hosts which should be monitored will be sent (defaults to True)
- `DT_UNMONITORED_EVENT_TITLE` - (optional) Event title for unmonitored host
- `DT_UNMONITORED_EVENT_SEVERITY` - (optional) Event severity for unmonitored host, defaults to AVAILABLITY_EVENT
- `DT_UNMONITORED_EVENT_TIMEOUT` - (optional) Event timeout in seconds for unmonitored host, defaults to 3600


3. Use cron for executing the script on hourly basis

        0 * * * * DT_APITOKEN="<place>" DT_ENVIRONMENT="<environment>" python3 /path/to/licenseHUmetric.py
