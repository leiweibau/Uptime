#!/usr/bin/env python
from __future__ import unicode_literals
from time import sleep, time, strftime
import requests
import io
#import smtplib
import sys
#from smtp_config import sender, password, receivers, host, port
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import sqlite3
import pwd
import os

con = sqlite3.connect("monitoring.db")
cur = con.cursor()

#DELAY = 60  # Delay between site queries
EMAIL_INTERVAL = 1800  # Delay between alert emails

last_email_time = {}  # Monitored sites and timestamp of last alert sent

# Message template for alert
MESSAGE = """From: {sender}
To: {receivers}
Subject: Monitor Service Notification

You are being notified that {site} is experiencing a {status} status!
"""
# -----------------------------------------------------------------------------
def prepare_service_monitoring_env ():
    global con
    global cur
    print()
    sql_create_table = """ CREATE TABLE IF NOT EXISTS Services_Events(
                                moneve_URL TEXT NOT NULL,
                                moneve_DateTime TEXT NOT NULL,
                                moneve_StatusCode NUMERIC NOT NULL,
                                moneve_Latency TEXT NOT NULL,
                                PRIMARY KEY(moneve_URL)
                            ); """
    cur.execute(sql_create_table)

    sql_create_table = """  CREATE TABLE IF NOT EXISTS Services(
                                mon_URL TEXT NOT NULL,
                                mon_MAC TEXT,
                                mon_LastStatus NUMERIC NOT NULL,
                                mon_LastLatency TEXT NOT NULL,
                                mon_LastScan TEXT NOT NULL,
                                mon_Tags TEXT,
                                mon_AlertEvents INTEGER DEFAULT 0,
                                mon_AlertDown INTEGER DEFAULT 0,
                                PRIMARY KEY(mon_URL)
                            ); """
    cur.execute(sql_create_table)

# -----------------------------------------------------------------------------
def colorize(text, color):
    """Return input text wrapped in ANSI color codes for input color."""
    return COLOR_DICT[color] + str(text) + COLOR_DICT['end']

# -----------------------------------------------------------------------------
def service_monitoring_log(site, status, latency):
    global monitor_logfile

    # Log status message to log file
    monitor_logfile.write("{} | {} | {} | {}\n".format(strftime("%Y-%m-%d %H:%M:%S"),
                                                site,
                                                status,
                                                latency,
                                                )
                  )

# -----------------------------------------------------------------------------
def send_alert(site, status):
    """If more than EMAIL_INTERVAL seconds since last email, resend email"""
    if (time() - last_email_time[site]) > EMAIL_INTERVAL:
        try:
            smtpObj = smtplib.SMTP(host, port)  # Set up SMTP object
            smtpObj.starttls()
            smtpObj.login(sender, password)
            smtpObj.sendmail(sender,
                             receivers,
                             MESSAGE.format(sender=sender,
                                            receivers=", ".join(receivers),
                                            site=site,
                                            status=status
                                            )
                             )
            last_email_time[site] = time()  # Update time of last email
            print("Successfully sent email")
        except smtplib.SMTPException:
            print("Error sending email ({}:{})".format(host, port))

# -----------------------------------------------------------------------------
def check_services_health(site):
    # Enable self signed SSL
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    """Send GET request to input site and return status code"""
    try:
        resp = requests.get(site, verify=False)
        latency = resp.elapsed
        latency_str = str(latency)
        latency_str_seconds = latency_str.split(":")
        return resp.status_code, latency_str_seconds[2].replace("00.", "0.")
    except requests.exceptions.SSLError:
        pass
    except:
        latency = "99999"
        return 503, latency

# ----------------------------------------------------------------------------- Duplicat
def get_username():

    return pwd.getpwuid(os.getuid())[0]

# -----------------------------------------------------------------------------
def get_services_list():
    global cur
    global con

    cur.execute("SELECT mon_URL FROM Services")
    rows = cur.fetchall()

    sites = []
    for row in rows:
        sites.append(row[0])

    return sites

# -----------------------------------------------------------------------------
def service_monitoring():
    global cur
    global con
    
    # Empty Log and write new header
    with open('monitor.log', 'w') as monitor_logfile:
        monitor_logfile.write("Pi.Alert [Prototype]:\n---------------------------------------------------------\n")
        monitor_logfile.write("Current User: %s \n\n" % get_username())
        monitor_logfile.write("Monitor Web-Services\n")
        monitor_logfile.write("Timestamp: " + strftime("%Y-%m-%d %H:%M:%S") + "\n\n")
        monitor_logfile.write("| Timestamp | URL | StatusCode | ResponseTime |\n-----------------------------------------------")

    sites = get_services_list()

    for site in sites:
        last_email_time[site] = 0  # Initialize timestamp as 0

    while sites:
        for site in sites:
            status,latency = check_services_health(site)

            print("({}) {} STATUS: {} ... {}".format(strftime("%Y-%m-%d %H:%M:%S"),
                                site,
                                colorize(status, "green"),
                                latency
                                )
                 )
            service_monitoring_log(site, status, latency)
            # sqlite_insert_with_param = """INSERT INTO Services
            #                  (mon_URL, mon_MAC, mon_LastStatus, mon_LastLatency, mon_LastScan, mon_Tags, mon_AlertEvents, mon_AlertDown) 
            #                  VALUES (?, ?, ?, ?, ?, ?, ?, ?);"""

            # data_tuple = (site, "s", status, latency, strftime("%Y-%m-%d %H:%M:%S"), "s", 1, 1)
            # cur.execute(sqlite_insert_with_param, data_tuple)
            # con.commit()
            sys.stdout.flush()

        monitor_logfile.close()
        exit()

    else:
        with open('monitor.log', 'a') as monitor_logfile:
            monitor_logfile.write("\n\nNo site(s) to monitor!")
            monitor_logfile.close()
        exit()

# Workflow
prepare_service_monitoring_env()
service_monitoring()



