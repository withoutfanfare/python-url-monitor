#!/usr/bin/env python3

"""
@author
@date
A simple Web service to monitor a set of websites

Usage:
monitor.py
"""

import smtplib
import time
import _thread
import socket
import os
import os.path
import math
import logging
import sys
import json
from datetime import datetime
from subprocess import check_call
from urllib.parse import urlencode, quote_plus
from octopus import Octopus
from datetime import datetime
from repeat_timer import RepeatTimer
from mqtt_pub import pub
import paho.mqtt.client as mqtt
from monitor_config import monitor_config
from servers import server_list
from server import Server

args = []
kwargs = {}

logging.basicConfig(filename='debug.log', level=logging.DEBUG)

def create_request(urls, method, kwargs):
    data = []
    otto = Octopus(
           concurrency=1, auto_start=True, cache=False, expiration_in_seconds=20
    )

    def handle_url_response(url, response):
        if "Not found" == response.text:
            print ("URL Not Found: %s" % url)
        else:
            data.append(response.text)

    for url in urls:
        otto.enqueue(url, handle_url_response, method, data=kwargs, headers={ "Content-type": "application/x-www-form-urlencoded" })

    otto.wait()

    json_data = json.JSONEncoder(indent=None,
                                 separators=(',', ': ')).encode(data)

    return json_data



class Monitor(object):

    def __init__(self, server_list, monitor_config, mqtt_client):

        self.interval = monitor_config['interval']
        self.recipients = monitor_config['recipients']
        self.servers = self.getServers(server_list)
        self.heartbeatFile = monitor_config['heartbeatFile']
        self.heartbeatHours = monitor_config['heartbeatHours']

        self.init_sound = monitor_config['init_sound']
        self.error_sound = monitor_config['error_sound']
        self.success_sound = monitor_config['success_sound']
        self.heartbeat_sound = monitor_config['heartbeat_sound']

        self.notification_user = monitor_config['notification_user']
        self.notification_token = monitor_config['notification_token']
        self.notification_url = monitor_config['notification_url']

        self.app_name = monitor_config['app_name']

        self.hostname = socket.gethostname()
        self.repeat_timer = None

        self.mode = 0

        self.client = mqtt_client

        self.learnIp()
        self.startChecks()



    def startChecks(self):
        """Initalise timer and heartbeat"""

        self.heartbeat()
        self.getTimer()



    def notify(self, mymessage, sound):
        """Sends a pushover notification"""

        mytitle = self.hostname + " > monitor."

        return create_request([self.notification_url], 'POST', {
            "token": self.notification_token,      # Pushover app token
            "user": self.notification_user,        # Pushover user token
            "html": "1",           # 1 for HTML, 0 to disable
            "title": mytitle,      # Title of message
            "message": mymessage,  # Message (HTML if required)
            "sound": sound,     # Sound played on receiving device
            })



    def cancelTimer(self):
        self.repeat_timer.cancel()



    def getTimer(self):
        if self.repeat_timer is None:
            self.repeat_timer = RepeatTimer(self.interval,
                                        self.checkServers,
                                        *args,
                                        **kwargs)



    def get_now(self):
        now = datetime.now()
        dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
        return dt_string



    def learnIp(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("gmail.com",80))
        ip = s.getsockname()[0]
        self.ip = ip
        s.close()
        self.client.publish(self.hostname + " @ " + ip)
        logging.info(self.hostname + " IP " + ip)



    def run(self):
        logging.info("Run: " + self.app_name)
        self.notify(self.app_name + ' Started', self.init_sound)
        self.client.publish(self.app_name + ' Started')
        self.repeat_timer.start()



    def checkServers(self, *args, **kwargs):
        self.heartbeat()

        # self.client.publish("Check URLs")

        for server in self.servers:
            _thread.start_new_thread(server.check_status, ())
            time.sleep(0.1)

        time.sleep(1)
        down_servers = self.getDownServers()

        if len(down_servers) > 0:
            self.notifyDown(down_servers)
        else:
            mes = "UP @ " + self.get_now()
            logging.info(mes)
            self.client.publish(mes)
            self.reset()



    def getDownServers(self):
        down_servers = []
        for server in self.servers:
            if server.status != 'OK' and server.fails >= server.max_fails and server.notified_fail == False:
                down_servers.append(server)
        return down_servers



    def notifyDown(self, down_servers):
        message = ''
        for server in down_servers:
            text = "%s %s %s - %s\n" % (server.name,
                                        server.last_checked,
                                        server.url,
                                        server.status)
            message += text
            server.notified_fail = True

            mes = "Site Down: " + server.name
            logging.info(mes)
            self.client.publish(mes)
            time.sleep(2)

        time.sleep(1)

        self.notify(message, self.error_sound)

        mes = "DOWN @ " + self.get_now()
        logging.info(mes)
        self.client.publish(mes)



    def getServers(self, server_list):
        servers = []
        for server in server_list:
            servers.append(Server(name=server['name'],
                                  url=server['url'],
                                  timeout=server['timeout'],
                                  max_fails=server['max_fails'],
                                  assert_string=server['assert_string']))
        return servers



    def reset(self):
        # logging.info("reset")
        for server in self.servers:
            server.notified_fail = False
            server.fails = 0
            server.status = 'OK'
            server.assert_pass = True



    def heartbeat(self):
        # logging.info("heartbeat")
        filePath = self.heartbeatFile
        a_name = self.app_name

        if(os.path.isfile(filePath)):

            f = open(filePath,"r")
            last = f.readline()
            f.close()

            dt_last = datetime.strptime(last, '%b %d %Y %I:%M%p')
            hours = math.floor(((datetime.now() - dt_last).total_seconds()) / 3600)
            if(hours > self.heartbeatHours):
                self.notify(a_name + ' Heartbeat', self.heartbeat_sound)
                self.client.publish("Heartbeat OK " + self.get_now())
                # for recipient in self.recipients:
                self.writeHeartbeat()
        else:
            self.writeHeartbeat()



    def writeHeartbeat(self):
        logging.info("writeHeartbeat")
        filePath = self.heartbeatFile
        f = open(filePath,"w")
        f.write(datetime.now().strftime('%b %d %Y %I:%M%p'))
        f.close()



    def update(self):
        # logging.info('update')
        self.reset()



    def setMode(self, mode):
        self.mode = mode
        modes = {
            0: "Monitor",
            1: "Backup",
            2: "Configuration",
            3: "Connect",
            4: "Disconnect",
            5: "Reboot",
            6: "Shutdown"
        }
        mode_text = modes.get(mode, "Unknown")



    def getMode(self):
        return self.mode


#
# Run
#
#
#
#
#
if __name__ == "__main__":

    MQTT_BROKER = monitor_config['mqtt_broker']
    MQTT_PORT = monitor_config['mqtt_port']
    MQTT_TOPIC = monitor_config['mqtt_topic']
    CHECK_INTERVAL = monitor_config['interval']
    MQTT_KEEPALIVE_INTERVAL = CHECK_INTERVAL * 2

    p = pub(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE_INTERVAL, MQTT_TOPIC)

    monitor = Monitor(server_list, monitor_config, p)
    monitor.run()

    print("CREATE CLIENT")
    client = mqtt.Client()

    def on_connect(client, userdata, flags, rc):
        logging.debug("Connected with result code: " + str(rc))
        logging.info('Subscribing')
        client.subscribe(MQTT_TOPIC)


    def on_message(client, userdata, msg):
        m = msg.payload.decode('utf-8')
        logging.info(m)
        if "OK" in m:
            bg = pendingBg
        if "REBOOT" in m:
            os.system("sudo systemctl reboot -i")
        if "SHUTDOWN" in m:
            os.system("sudo shutdown -h now")


    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(MQTT_BROKER, MQTT_PORT)
    client.loop_forever()

    #end