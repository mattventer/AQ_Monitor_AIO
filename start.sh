#!/bin/bash
NOW=$(date +"%m-%d-%Y_%r")
echo "New session: $NOW" >> src/aq_monitor.log
echo "Starting AQ AIO..."
nohup ./src/aq_monitor.py >> src/aq_monitor.log &
echo "Log located at: src/aq_monitor.log"
echo "Running"
