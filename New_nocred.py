import serial
import pynmea2
import time
import pyrebase
import Adafruit_SSD1306
from PIL import Image, ImageDraw, ImageFont
import RPi.GPIO as GPIO
import threading
import requests
from shapely.geometry import MultiPoint,LineString,Point
import json
from math import *
import smtplib


class RouteDetection:
    lat = 0
    lng = 0
    fine = 0
    index = 0
    un = 'email'
    password = 'pass'
    vehicle_id = ''
    origin_lat = 0
    origin_lng = 0
    destination_lat = 0
    destination_lng = 0
    isCorrect = 1
    via_lat = 0
    via_lng = 0
    isRoute = 0
    last_known_lat = 0
    last_known_lng = 0
    is_fine_limit_cross = 0
    distance_traveled = 0
    geometry = {}
    speed = 0
    isdestination = 0
    road_snap = {}
    map_api = ''
    isDirection = 1
    email = ''
    config = {
        "apiKey":"",
        "authDomain":"",
        "databaseURL":"",
        "storageBucket":"",
        "serviceAccount":"./.json"
        

        }
    
    
    def __init__(self,lat,lng,vehicle_id,email):
        
        firebase = pyrebase.initialize_app(self.config)
        self.db = firebase.database()
        self.lat = lat
        self.lng = lng
        self.serialPort = serial.Serial("/dev/serial0", 9600, timeout=0.5)
        self.email = email
        self.vehicle_id = vehicle_id
        self.mail = smtplib.SMTP('smtp.gmail.com',587)
        self.mail.starttls()
        self.mail.login(self.un,self.password)
        self.last_known_lat =self.db.child("users").child(vehicle_id).child("lat").get()
        self.last_known_lng = self.db.child("users").child(vehicle_id).child("lng").get()
        try:
            if(self.getFine()!=None):
                self.fine = self.getFine()
        except:
            print("New vehicle registered.")
        #self.fine = self.getFine()
        print(self.fine)
        self.sendMail(self.email,'Vehicle Tracking System Initiated\nYour Pending Fine:'+str(self.fine))
    def setSpeed(self,speed):
        self.speed = speed
    def setRoad_snap(self,snap):
        self.road_snap = snap
        
    def getCoordinates(self):
        if(not self.isOverFine()):
            while True:
                str = self.serialPort.readline()
             
                
               # print(str)
                #parseGPS(str,self)
                if str.find('CGA') > 0:
                        print("true")
                        msg = pynmea2.parse(str)
                        if(self.lng>msg.lon):
                            self.isCorrect = 1
                        else:
                            self.isCorrect = 0
                        self.lat = msg.lat
                        self.lng = msg.lon
                time.sleep(11)





    def getSpeed(self):
        if(not self.isOverFine()):
            while True:
                str = self.serialPort.readline()
                data = str.lstrip("b'")[:-3]
                if data.find('$GPVTG')!=-1:
                    cur_speed = data.split(",")[7]
                    self.speed = cur_speed
                time.sleep(11)

    def getGeometry(self):
        lat = []
        lng = []
        for x in self.road_snap['snappedPoints']:
            lat.append(x['location']['latitude'])
            lng.append(x['location']['longitude'])
        coords = list(zip(lat,lng))
        #self.geometry = LineString(coords)
        self.geometry = MultiPoint(coords).convex_hull
        
    def getRoadSnapShot(self,origin_lat,origin_lng,via_lat,via_lng,dest_lat,dest_lng):
        #url = 'https://roads.googleapis.com/v1/snapToRoads?path='+str(origin_lat)+','+str(origin_lng)+'|'+str(via_lat)+','+str(via_lng)+'|'+str(dest_lat)+','+str(dest_lng)+'&key=AIzaSyDzmsvrf1kfh8sxSXMdcB6H8h6hmAcSyic'
        url = 'https://roads.googleapis.com/v1/snapToRoads?path='+str(origin_lat)+','+str(origin_lng)+'|'+str(via_lat)+','+str(via_lng)+'|'+str(dest_lat)+','+str(dest_lng)+'&key='            
        try:
            myResponse = requests.get(url)
            print(myResponse)
            if(myResponse.ok):
                jData = json.loads(myResponse.content)
                self.road_snap = jData
                print(self.road_snap)
                self.getGeometry()
                update_db_thread = threading.Thread(target = vehicle_tracking.updateFirebase)
                display_thread = threading.Thread(target = vehicle_tracking.display)
                coordinate_thread = threading.Thread(target = vehicle_tracking.getCoordinates)
                speed_thread = threading.Thread(target = vehicle_tracking.getSpeed)
                coordinate_thread.start()
                speed_thread.start()
                update_db_thread.start()
                display_thread.start()
                return
        except Exception:
            print('Something went Wrong')
            print(Exception)
            return -1
        
    def isOnTrack(self):
        point = Point(self.lat,self.lng)

        return point.within(self.geometry)

    def addFine(self,amount):
        self.fine=self.fine+amount

    def isOverSpeed(self):
        if(self.speed>10):
            return 2
        elif(self.speed<10 and self.speed>0):
            return 1
        else:
            return 0
        
    def resetFine(self):
        self.fine = self.db.child("users").child(self.vehicle_id).child("fine").set(0)

        
    def accelerate(self):
        while True:
            acceleration = input('Enter acceleration:')
            self.speed = self.speed+acceleration
            time.sleep(11)

        
        
    def display(self):
        while True:
            display = Adafruit_SSD1306.SSD1306_128_32(rst=None)
            display.begin() # initialize graphics library for selected display module
            display.clear() # clear display buffer
            display.display() # write display buffer to physical display
            displayWidth = display.width # get width of display
            displayHeight = display.height # get height of display
            image = Image.new('1', (displayWidth, displayHeight)) # create graphics library image buffer
            draw = ImageDraw.Draw(image) # create drawing object
            font = ImageFont.load_default()# load and set default font

            #if:
            # Draw text
            
    #and self.isDirection==1
            
    #draw.text((10,0), "Powered By STEWPEED!!!", font=font, fill=120) # print text to image buffer
            #if(self.isOnTrack() and self.isOverSpeed()<2 and self.isDirection==1 and not self.isOverFine()):
            if(self.isOnTrack() and self.isOverSpeed()<2 and not self.isOverFine() and self.isCorrect ==1):
                draw.text((1,0), "Lattitude:"+str(self.lat), font=font, fill=120) # print text to image buffer
                draw.text((1,8), "Longitude:"+str(self.lng), font=font, fill=120) # print text to image buffer
                draw.text((1,16), "Fine:"+str(self.fine), font=font, fill=120) # print text to image buffer
                draw.text((1,23), "Speed:"+str(self.speed), font=font, fill=120)
            elif(self.isdestination ==1):
                draw.text((1,0), "Lattitude:"+str(self.lat), font=font, fill=120) # print text to image buffer
                draw.text((1,8), "Longitude:"+str(self.lng), font=font, fill=120) # print text to image buffer
                draw.text((1,16), "Fine:"+str(self.fine), font=font, fill=120) # print text to image buffer
                draw.text((1,23), "Speed:"+str(self.speed), font=font, fill=120)
            elif(self.isOverSpeed()==2 and not self.isOverFine()):
                self.addFine(50)
                draw.text((1,0), "!!Over Speed!!", font=font, fill=120) # print text to image buffer
                self.sendMail(self.email,'OverSpeed\n'+'\nTotal Fine:'+str(self.fine))
            elif(not self.isOnTrack() and not self.isOverFine()):
                self.addFine(1000)
                draw.text((1,0), "!!Out of Track!!", font=font, fill=120) # print text to image buffer
                #self.sendMail(self.email,'Wrong Routen'+'\nTotal Fine:'+str(self.fine))
            elif(self.isOverSpeed()==0):
                draw.text((1,0), "!!Stop!!", font=font, fill=120) # print text to image buffer
            elif(self.isOverFine()):
                draw.text((1,0), "!!Halt.Pay Fine!!", font=font, fill=120) # print text to image buffer
            elif(self.isCorrect == 0 and not self.isOverFine()):
                self.addFine(1000)
                draw.text((1,0), "!!Wrong Route!!", font=font, fill=120) # print text to image buffer
                self.sendMail(self.email,'Wrong Routen'+'\nTotal Fine:'+str(self.fine))
                
            else:
                draw.text((1,0), "!!!Check Log!!!", font=font, fill=120) # print text to image buffer
                
            


            # Display to screen
            display.image(image) # set display buffer with image buffer
            display.display() # write display buffer to physical display
            time.sleep(11)  
            # Cleanup
            #GPIO.cleanup() # release all GPIOIO resources



    def getFine(self):
        try:
            det = self.db.child("users").child(self.vehicle_id).get()
            for data in det.each():
                if(data.key()=='Fine'):
                    self.fine = data.val()
            return self.fine
        except:
            print("New vehicle Registered.")
    


    def lastKnownlocation(self): 
        det = self.db.child("users").child(self.vehicle_id).get()
        for data in det.each():
            if(data.key()=='Latitude'):
                self.lat = data.val()
            if(data.key()=='Longitude'):
                self.lng =data.val()
            if(data.key()=='Fine'):
                self.fine = data.val()

        print('Last Known Location:\nLatitude:'+str(self.lat)+'\nLongitude:'+str(self.lng))
        msg = 'Last Known Location:\nLatitude:'+str(self.lat)+'\nLongitude:'+str(self.lng)
        self.sendMail(self.email,msg)
        
    
        
        
    def getBearing(lat1,lon1,lat2,lon2):
        dLon = lon2 - lon1
        y=sin(dLon) * cos(lat2)
        x = cos(lat1) * sin(lat2) \
          -sin(lat1) * cos(lat2) * cos(dLon)
        return atan2(y,x)

    def isOnRoute(self,lat1,lon1,lat2,lon2):
        if(self.getBearing(lat,lon,lat2,lon2)>-25 and self.getBearing(lat,lon,lat2,lon2)<25):
            return True
        else:
            return False

    def isOverFine(self):
        if(self.fine>5000):
            return True
        else:
            return False
        
    def updateCoordinates(self):
        if(not self.isOverFine()):
            while True:
                if(self.lng>self.road_snap['snappedPoints'][self.index]['location']['longitude']):
                    self.isCorrect = 1
                else:
                    self.isCorrect = 0
                self.lat = self.road_snap['snappedPoints'][self.index]['location']['latitude']
                self.lng = self.road_snap['snappedPoints'][self.index]['location']['longitude']
                print(self.lat)
                if(self.index<len(self.road_snap['snappedPoints'])-1 and self.speed!=0):
                    self.index = self.index+1
                elif(self.index==len(self.road_snap['snappedPoints'])-1):
                    self.isdestination = 1
                
                time.sleep(11)

    def sendMail(self,to,message):
        self.mail.sendmail(self.un,to,message)
        return

    def updateFirebase(self):
        if(not self.isOverFine()):
            while True:
                data = {"vehicle_id":self.vehicle_id,"Latitude":self.lat,"Longitude":self.lng,"Fine":self.fine,'Email':self.email}
                self.db.child("users").child(self.vehicle_id).set(data)
                time.sleep(11)
                                 



if __name__=='__main__':
    print("Vehicle Tracking System Initiated\n")
    vehicle_id = input("Enter Vehicle id:")
    email = input("Enter email address:")
    vehicle_tracking = RouteDetection(1,2,vehicle_id,email)
    print("0-Demo mode")
    print("1-Live Mode.")
    print("2-Get Last Known Location.")
    print("3-Reset Fine.")
    
    mode = input("Enter your Choice:")
    if(mode ==0):
        road_snap = {
  "snappedPoints": [
    {
      "location": {
        "latitude": 11.941623654431327,
        "longitude": 76.566839076273823
      },
      "originalIndex": 0,
      "placeId": "ChIJXQ9RaIsVrjsRGjdSV3hGrvE"
    },
    {
      "location": {
        "latitude": 12.941938519593689,
        "longitude": 77.5653454943392
      },
      "originalIndex": 1,
      "placeId": "ChIJO2QJG4sVrjsR6yn7hyQKAdE"
    },
     {
      "location": {
        "latitude": 12.41623654431327,
        "longitude": 77.5653454943393
      },
      "originalIndex": 1,
      "placeId": "ChIJO2QJG4sVrjsR6yn7hyQKAdE"
    },
     {
      "location": {
        "latitude": 12.41623654431326,
        "longitude": 77.56683907627382
      },
      "originalIndex": 1,
      "placeId": "ChIJO2QJG4sVrjsR6yn7hyQKAdE"
    },
    {
      "location": {
        "latitude": 13.940450707375122,
        "longitude": 78.565058036418662
      },
      "originalIndex": 2,
      "placeId": "ChIJO2QJG4sVrjsR6yn7hyQKAdE"
    }
  ]
}
        speed = input('Enter Speed:')
        vehicle_tracking.setSpeed(speed)
        vehicle_tracking.setRoad_snap(road_snap)
        vehicle_tracking.getGeometry()
        get_acc_thread = threading.Thread(target = vehicle_tracking.accelerate)
        update_db_thread = threading.Thread(target = vehicle_tracking.updateFirebase)
        display_thread = threading.Thread(target = vehicle_tracking.display)
        update_coordinates_thread = threading.Thread(target = vehicle_tracking.updateCoordinates)

        update_coordinates_thread.start()                     
        get_acc_thread.start()
        update_db_thread.start()
        display_thread.start()
        

        


    if(mode == 1):
        origin_lat = input("Enter origin latitude:")
        origin_lon = input("Enter origin Longitude:")
        via_lat = input("Enter Via Latitude:")
        via_lon = input("Enter via Longitude:")
        destination_lat = input("Enter destinaion latitude:")
        destination_lon = input("Enter destination longitude:")

        vehicle_tracking.getRoadSnapShot(origin_lat,origin_lon,via_lat,via_lon,destination_lat,destination_lon)
        
        print("")

        

    elif(mode == 2):
        vehicle_tracking.lastKnownlocation();
        print("")

        
        

    elif(mode == 3):
        vehicle_tracking.resetFine()
        print("")



        


        
    

   
    
        
        
        
        

