#!/usr/bin/env python

import time
import sys
import RPi.GPIO as GPIO
import urllib2
from mprofi_api_client import MprofiAPIConnector
from paho.mqtt import client as mqttc
from motiondetect_conf import *


GPIO.setmode(GPIO.BCM)
GPIO.setup(gpio_pin, GPIO.IN)

def on_connect(client, userdata, rc):
        print('Connected with result code '+str(rc))
        client.subscribe(mqtt_topic)
def on_message(client, userdata, msg):
        print 'Topic: ', msg.topic+'\nMessage: '+str(msg.payload)
	hour = time.strftime("%H")
        if msg.payload == "1" or ((int(hour) >= 24 or int(hour) <6) and msg.payload <> "3"):
            connector = MprofiAPIConnector(api_token=mprofi_key)
            connector.add_message(mprofi_recipient, mprofi_message)
            connector.send(mprofi_ref)
        client.disconnect()

client = mqttc.Client()
client.on_connect = on_connect
client.on_message = on_message
client.username_pw_set(mqtt_uname, mqtt_pw)

for num in range(1,120):
    if (GPIO.input(gpio_pin)==1):
	f = urllib2.urlopen(thingspeak_baseURL +
                                "&%s=%s" % (thingspeak_field,1))

	client.connect(mqtt_server, mqtt_port, 60)
	client.loop_forever() 
	print "motion detected"
	sys.exit(0)

    time.sleep(1)
