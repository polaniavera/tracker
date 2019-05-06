#!/usr/bin/env python

import time
import json
import serial
import sqlite3
import requests
import subprocess
import adafruit_gps
import Adafruit_DHT

#initial data
kilometraje = 0
latitud = 0.0
longitud = 0.0
altitud = 0.0
velocidad = 0
tanqueConductor = 0.0
tanquePasajero = 0.0
fecha = ""
hora = ""
enviado = 0
timePost = 60
timeUpdate = 600
outPost = 15
outUpdate = 60
ipTest = "190.143.75.85"
headers = {'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest'}
url = "https://pruebas.extranet.com.co/coreiot/api/public/EYT.Tracker/Registro/Registro/Nuevo"
dataBase = "/home/pi/coreiot/itemdb"
idItem = "e67d85d2-cf20-4027-be3e-c488e2d64a80"
sensor = Adafruit_DHT.DHT11
gpioSensor = 17
countGps = 0

time.sleep(5)
print('-' * 5+'START'+'-' * 5, flush=True)

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def post_request(body, tOut):
    success = False
    try:
        r = requests.post(url, data=json.dumps(body), headers=headers, timeout=tOut)
        r.raise_for_status()
        if(r.json()['Error']):
            print('Error', flush=True)
        else:
            flag = 1
            success = True
    except requests.exceptions.HTTPError as errh:
        print ("Http Error:",errh, flush=True)
    except requests.exceptions.ConnectionError as errc:
        print ("Error Connecting:",errc, flush=True)
    except requests.exceptions.Timeout as errt:
        print ("Timeout Error:",errt, flush=True)
    except requests.exceptions.RequestException as err:
        print ("OOps: Something Else",err, flush=True)
    finally:
        if not success:
            flag = 0
    return flag

def watcher():
    connection = False
    try:
        pingRes = subprocess.check_output("ping 190.143.75.85 -c3 -q | grep received | awk -F ',' '{print $2}' | awk '{print $1}'", shell=True)
        if int(pingRes) > 0:
            connection = True
        else:
            print("Network down", flush=True)
    except:
        print("Network Test Error", flush=True) 
    if connection:
        cursor.execute("SELECT id, Kilometraje, Latitud, Longitud, Altitud, TanqueConductor, TanquePasajero, Velocidad, Fecha, Hora FROM item WHERE Enviado = 0")
        results = cursor.fetchall()
        if len(results) > 0:
            idList = []
            jsondict = {}
            for val in results:
                idList.append(val['id'])
                del val['id']
            jsondict['Registros'] = results
            jsondict['idItem'] = 'e67d85d2-cf20-4027-be3e-c488e2d64a80'
            #Update
            updated = post_request(jsondict, outUpdate)
            if updated==1:
                sql="UPDATE item SET Enviado = 1 WHERE id IN ({seq})".format(seq=','.join(['?']*len(idList)))
                cursor.execute(sql, idList)
                dbconnect.commit()
                print('{} Updated'.format(len(idList)), flush=True)
            else:
                print('Error POST', flush=True)
        else:
            print('Up to date', flush=True)
       
# serial uart access
uart = serial.Serial("/dev/ttyS0", baudrate=9600, timeout=3000)
# Create a GPS module instance.
gps = adafruit_gps.GPS(uart, debug=False)
# Turn on the basic GGA and RMC info
gps.send_command(b'PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0')
# Set update rate to once a second (1hz)
gps.send_command(b'PMTK220,1000')

#database set up
dbconnect = sqlite3.connect(dataBase, check_same_thread=False)
dbconnect.row_factory = dict_factory
cursor = dbconnect.cursor()
 
lastPost = time.monotonic()
lastUpdate = time.monotonic()
while True:
    # Every 60s post, 600s update
    gps.update()
    if not gps.has_fix:
        countGps += 1
        time.sleep(1)
        if countGps == 100:
            raise Exception('Error GPS timeout')    
        continue
    countGps = 0
    current = time.monotonic()
    currentUpdate = time.monotonic()
    if current - lastPost >= timePost:
        lastPost = current
        #Fetch data from sensor
        tanqueConductor, tanquePasajero = Adafruit_DHT.read_retry(sensor, gpioSensor)
        #Fetch data from gps
        latitud = gps.latitude
        longitud = gps.longitude
        if gps.speed_knots is not None:
            velocidad = int(gps.speed_knots * 1.852)
        if gps.altitude_m is not None:
            altitud = gps.altitude_m
        fecha = '{}/{}/{}'.format(
            gps.timestamp_utc.tm_mday,
            gps.timestamp_utc.tm_mon,
            gps.timestamp_utc.tm_year)
        hora = '{:02}:{:02}:{:02}'.format(
            gps.timestamp_utc.tm_hour,
            gps.timestamp_utc.tm_min,
            gps.timestamp_utc.tm_sec)        
        
        payload = {'IdItem':idItem,
         'Registros':[{
             'Kilometraje':kilometraje,
             'Latitud':latitud,
             'Longitud':longitud,
             'Altitud':altitud,
             'TanqueConductor':tanqueConductor,
             'TanquePasajero':tanquePasajero,
             'Velocidad':velocidad,
             'Fecha':fecha,
             'Hora':hora
             }]
         }
        
        #POST
        enviado = post_request(payload, outPost)
        if enviado == 0:
            print('Enviado: {}'.format(enviado), flush=True)
        
        #execute insert statement
        cursor.execute("INSERT INTO item (Kilometraje, Latitud, Longitud, TanqueConductor, TanquePasajero, Velocidad, Altitud, Fecha, Hora, Enviado)VALUES(?,?,?,?,?,?,?,?,?,?)",
                       (kilometraje, latitud, longitud, tanqueConductor, tanquePasajero, velocidad, altitud, fecha, hora, enviado))
        dbconnect.commit()
        
        #print('Id: {}'.format(idItem), flush=True)
        #print('Kilometraje: {}'.format(kilometraje), flush=True)
        #print('Latitud: {0:.6f}'.format(latitud), flush=True)
        #print('Longitud: {0:.6f}'.format(longitud), flush=True)
        #print('Tanque Conductor: {}'.format(tanqueConductor), flush=True)
        #print('Tanque Pasajero: {}'.format(tanquePasajero), flush=True)
        #print('Velocidad: {} km/h'.format(velocidad), flush=True)
        #print('Altitud: {} metros'.format(altitud), flush=True)
        #print('Fecha: {}'.format(fecha), flush=True)
        #print('Hora: {}'.format(hora), flush=True)
        
    if currentUpdate - lastUpdate >= timeUpdate:
        lastUpdate = currentUpdate
        watcher()
    
#close the connection
dbconnect.close()