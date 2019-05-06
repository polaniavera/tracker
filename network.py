#!/usr/bin/env python

import os
import sys
import time
import requests
import xmltodict
import subprocess

attempt = 0
finish = False

class HuaweiE3372(object):
    BASE_URL = 'http://{host}'
    COOKIE_URL = '/html/index.html'
    XML_APIS = [
        '/api/device/information',
        '/api/device/signal'
        ]
    session = None
    connected = False

    def __init__(self,host='192.168.8.1'):
        self.host = host
        self.base_url = self.BASE_URL.format(host=host)
        self.session = requests.Session()
        # get a session cookie by requesting the COOKIE_URL
        try:
            r = self.session.get(self.base_url + self.COOKIE_URL, timeout=10)
            r.raise_for_status()
            self.connected = True
        except requests.exceptions.HTTPError as errh:
            print ("Http Error:",errh)
        except requests.exceptions.ConnectionError as errc:
            print ("Error Connecting:",errc)
        except requests.exceptions.Timeout as errt:
            print ("Timeout Error:",errt)
        except requests.exceptions.RequestException as err:
            print ("OOps: Something Else",err)
        
    def get(self,path):
        return xmltodict.parse(self.session.get(self.base_url + path, timeout=10).text).get('response',None)

def main():
    global finish
    while not finish:
        e3372 = HuaweiE3372()
        if e3372.connected:
            for path in e3372.XML_APIS:
                for key,value in e3372.get(path).items():
                    if key=='rssi':
                        signal = value
                    if key=='workmode':
                        mode = value
            monitor(mode, signal)                 
        else:                
            print('Device is not connected')
            finish = True
    print('Finish')        
    
def monitor(m, s):
    global finish
    if m == 'LTE':
        if int(s[:3]) < -85:
            print('Nivel bajo {} {}'.format(m, s))
            finish = True
        else:
            print('Nivel OK {} {}'.format(m, s))
            checkInternet()
    elif m == 'WCDMA':
        if int(s[:3]) < -100:
            print('Nivel bajo {} {}'.format(m, s))
            finish = True
        else:
            print('Nivel OK {} {}'.format(m, s))
            checkInternet()
    else:
        print('{} {}'.format(m, s))
        finish = True
            
def checkInternet():
    global finish
    global attempt
    print('checking...')
    connection = False
    try:
        pingRes = subprocess.check_output("ping 190.143.75.85 -c3 -q | grep received | awk -F ',' '{print $2}' | awk '{print $1}'", shell=True)
        if int(pingRes) > 0:
            connection = True
            finish = True
            attempt = 0
            print("Up and running")
        else:
            print("Network down")
    except:
        print("Network Test Error")
    if not connection:
        if attempt == 3:
            print ('Rebooting device')
            os.system('sudo reboot')
        print('Restarting interface')
        os.system('sudo ip link set eth1 down')
        time.sleep(60)
        os.system('sudo ip link set eth1 up')
        time.sleep(60)
        attempt += 1
        print ('Attempt {}'.format(attempt))
        
if __name__ == "__main__":
    print('*'*25)
    print(time.strftime("%c"))
    interface = os.system('sudo ip link set eth1 up')
    if interface == 0:
        time.sleep(60)
        main()
    else:
        print('No eth interface')
