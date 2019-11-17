#!/bin/bash
NOW=$(date +"%m-%d-%Y_%r")
echo "New session: $NOW" >> src/aq_monitor.log
echo "Starting AQ AIO..."
echo "Starting AQ AIO..." >> src/aq_monitor.log
nohup python3 src/aq_monitor.py >> src/aq_monitor.log &
#echo "Starting ngrok server with subdomain aqmonitor"
#echo "Starting ngrok server with subdomain aqmonitor" >> src/aq_sms_responder.log
#cd src/
#./ngrok http -subdomain=aq_monitor 5000 >> src/aq_sms_responder.log &
#cd ..
echo "Starting AQ SMS Responder..."
echo "Starting AQ SMS Responder..." >> src/aq_sms_responder.log
nohup python3 src/aq_sms_responder.py >> src/aq_sms_responder.log &
echo "Log located at: src/aq_monitor.log"
echo "Running"
