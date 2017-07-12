# Welcome to winlogbeat 5.4.3

Winlogbeat ships Windows event logs to Elasticsearch or Logstash.

## Getting Started

To get started with winlogbeat, you need to set up Elasticsearch on your localhost first. After that, start winlogbeat with:

     ./winlogbeat  -c winlogbeat.yml -e

This will start the beat and send the data to your Elasticsearch instance. To load the dashboards for winlogbeat into Kibana, run:

    ./scripts/import_dashboards

For further steps visit the [Getting started](https://www.elastic.co/guide/en/beats/winlogbeat/5.4/winlogbeat-getting-started.html) guide.

## Documentation

Visit [Elastic.co Docs](https://www.elastic.co/guide/en/beats/winlogbeat/5.4/index.html) for the full winlogbeat documentation.

## Release notes

https://www.elastic.co/guide/en/beats/libbeat/5.4/release-notes-5.4.3.html
