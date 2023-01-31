#!/usr/bin/env python
from __future__ import unicode_literals
from time import sleep, time, strftime
import requests
import io
import smtplib
import sys
from smtp_config import sender, password, receivers, host, port
#import pandas as pd


DELAY = 60  # Delay between site queries
EMAIL_INTERVAL = 1800  # Delay between alert emails

last_email_time = {}  # Monitored sites and timestamp of last alert sent

# Define escape sequences for colored terminal output
COLOR_DICT = {
    "green": "\033[92m",
    "red": "\033[91m",
    "yellow": "\033[93m",
    "bold": "\033[1m",
    "end": "\033[0m",
    }

# Message template for alert
MESSAGE = """From: {sender}
To: {receivers}
Subject: Monitor Service Notification

You are being notified that {site} is experiencing a {status} status!
"""

def colorize(text, color):
    """Return input text wrapped in ANSI color codes for input color."""
    return COLOR_DICT[color] + str(text) + COLOR_DICT['end']


def error_log(site, status, latency):
    """Log errors to stdout and log file, and send alert email via SMTP."""
    # Print colored status message to terminal
    print("({}) {} STATUS: {}... {}".format(strftime("%Y-%m-%d %H:%M:%S"),
                                        site,
                                        colorize(status, "yellow"),
                                        latency
                                        )
         )
    # Log status message to log file
    with open('monitor.log', 'a') as log:
        log.write("({}) {} STATUS: {}... {}\n".format(strftime("%Y-%m-%d %H:%M:%S"),
                                                site,
                                                status,
                                                latency,
                                                )
                  )


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
            print(colorize("Successfully sent email", "green"))
        except smtplib.SMTPException:
            print(colorize("Error sending email ({}:{})".format(host, port), "red"))


def ping(site):
    """Send GET request to input site and return status code"""
    try:
        resp = requests.get(site)
        latency = resp.elapsed
        latency_str = str(latency)
        latency_str_seconds = latency_str.split(":")
        return resp.status_code, latency_str_seconds[2].replace("00.", "0.")
    except:
        latency = "99999"
        return 503, latency


def get_sites():
    """Return list of unique URLs from input and sites.txt file."""
    sites = sys.argv[1:]  # Accept sites from command line input

    # Read in additional sites to monitor from sites.txt file
    try:
        sites += [site.strip() for site in io.open('sites.txt', mode='r').readlines()]
    except IOError:
        print(colorize("No sites.txt file found", "red"))

    # Add protocol if missing in URL
    for site in range(len(sites)):
        if sites[site][:7] != "http://" and sites[site][:8] != "https://":
            sites[site] = "http://" + sites[site]

    # Eliminate exact duplicates in sites
    sites = list(set(sites))
    return sites

def main():
    # Empty Log
    open('monitor.log', 'w').close()
    sites = get_sites()

    for site in sites:
        #print(colorize("Beginning monitoring of {}".format(site), "bold"))
        last_email_time[site] = 0  # Initialize timestamp as 0

    while sites:
        try:
            for site in sites:
                status,latency = ping(site)
                if status == 200:
                    print("({}) {} STATUS: {} ... {}".format(strftime("%Y-%m-%d %H:%M:%S"),
                                        site,
                                        colorize(status, "green"),latency
                                        )
                         )
                    sys.stdout.flush()
                else:
                    error_log(site, status, latency)
                    #send_alert(site, status)
            #sleep(DELAY)
            exit()
        # except requests.exceptions.ConnectionError:
        #     print(colorize("No Connection ({})".format(site), "red"))
        except KeyboardInterrupt:
            print(colorize("\n-- Monitoring canceled --", "red"))
            break
    else:
        print(colorize("No site(s) input to monitor!", "red"))
        exit()

#if __name__ == '__main__':
main()
