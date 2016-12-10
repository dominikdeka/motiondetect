import sys
import RPi.GPIO as GPIO
from time import sleep  
import Adafruit_DHT
import urllib2
import paho.mqtt.publish as publish
from dhtmonitor_conf import *


def getSensorData(pin):
    RH, T = Adafruit_DHT.read_retry(Adafruit_DHT.DHT22, pin)
    # return dict
    return (str(round(RH,1)), str(round(T,1)))
    
# main() function
def main():
    print 'starting...'

    while True:
        try:
            RH, T = getSensorData(2)
            RH2, T2 = getSensorData(3)
            RH3, T3 = getSensorData(4)
            RH4, T4 = getSensorData(17)
            try:
                f = urllib2.urlopen(thingspeak_baseURL + 
                                "&field1=%s&field2=%s&field3=%s&field4=%s&field5=%s&field6=%s&field7=%s&field8=%s" % (T, RH, T2, RH2, T3, RH3, T4, RH4))
                f.close()
		msgs = [("/temperature/garden", T, 0, True),
			("/temperature/taras", T2, 0, True),
			("/hummidity/taras", RH2, 0, True),
			("/temperature/loundry", T3, 0, True),
			("/hummidity/loundry", RH3, 0, True),
			("/temperature/front", T4, 0, True)
			]
		publish.multiple(msgs,hostname=mqtt_server,port=mqtt_port,client_id="",keepalive=60,will=None,auth={'username':mqtt_uname, 'password':mqtt_pw})
            except urllib2.HTTPError, e:
                checksLogger.error('HTTPError = ' + str(e.code))
            except urllib2.URLError, e:
                checksLogger.error('URLError = ' + str(e.reason))
            except httplib.HTTPException, e:
                checksLogger.error('HTTPException')
            except Exception:
                import traceback
                checksLogger.error('generic exception: ' + traceback.format_exc())	    
            sleep(600)
        except:
            print 'error: ', sys.exc_info()[0]

# call main
if __name__ == '__main__':
    main()
