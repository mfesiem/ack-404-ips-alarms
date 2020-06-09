# Acknowledge irrelevants McAfee IPS alarms

Automatically acknowledge irrelevants IPS - High Severity Event alarms based on filters


This script is designed to check and automatically acknowledge irrelevant alarms triggered by McAfee IPS (also known as NSM) because they refer to pages that are inexistent.


Exemple: Acknowledge last 24 hours IPS alarms regarding any URLs matching "login.php" returning a HTTP error or a network error. Do not ask user for confirmation.

```
python3 ./ack-irrelevants-ips-alarms.py -t last_24_hours -r 404,403,503,error -s login.php --force
```
