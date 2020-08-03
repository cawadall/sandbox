# -*- coding: utf-8 -*-

import threading
import time
from datetime import datetime
import cv2
import numpy as np


time_cycle = 80

class MyAlgorithm(threading.Thread):

    def __init__(self, camera, motors):
        self.camera = camera
        self.motors = motors

        self.pan = 0.0
        self.tilt = 0.0
        self.first_time = True
        self.time = 0.0
        self.topright = False
        # MOVE CAMERA TO A KNOWN POSITION
        if (self.motors):
            self.motors.setPTMotorsData(0, 0, 24, 20)

        self.stop_event = threading.Event()
        self.kill_event = threading.Event()
        self.lock = threading.Lock()
        threading.Thread.__init__(self, args=self.stop_event)


    def run (self):

        self.stop_event.clear()

        while (not self.kill_event.is_set()):
           
            start_time = datetime.now()

            if not self.stop_event.is_set():
                self.execute()

            finish_Time = datetime.now()

            dt = finish_Time - start_time
            ms = (dt.days * 24 * 60 * 60 + dt.seconds) * 1000 + dt.microseconds / 1000.0
            #print (ms)
            if (ms < time_cycle):
                time.sleep((time_cycle - ms) / 1000.0)

    def stop (self):
        self.stop_event.set()

    def play (self):
        if self.is_alive():
            self.stop_event.clear()
        else:
            self.start()

    def kill (self):
        self.kill_event.set()


    def execute(self):
        # Add your code here
        # Input image
        input_image = self.camera.getImage()
        if input_image is not None:
            self.camera.setColorImage(input_image)
            '''
            If you want show a thresohld image (black and white image) or a gray 
            or filtered image use:
            self.camera.setThresholdImage(image)
            '''
            face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
            eye_cascade = cv2.CascadeClassifier('haarcascade_eye.xml')
            gray = cv2.cvtColor(input_image, cv2.COLOR_BGR2GRAY)


            input_image_copy = np.copy(input_image)
            gray_copy = np.copy(gray)

            # SEGMENTATION
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30),flags=cv2.CASCADE_SCALE_IMAGE)
            print "Found {0} faces!".format(len(faces))

            center = [0,0]
            for (x,y,w,h) in faces:
                cv2.rectangle(input_image_copy,(x,y),(x+w,y+h),(255,0,0),2)
                roi_gray = gray_copy[y:y+h, x:x+w]
                roi_color = input_image_copy[y:y+h, x:x+w]
                center = [x+(w/2), y+(h/2)]
                eyes = eye_cascade.detectMultiScale(roi_gray)
                print "center: {cen}".format(cen=center)
                for (ex,ey,ew,eh) in eyes:
                    cv2.rectangle(roi_color,(ex,ey),(ex+ew,ey+eh),(0,255,0),2)
            self.camera.setThresholdImage(input_image_copy) #output

            #MOVEMENT OF THE CAMERA TO FOLLOW THE SEGMENTED
            limits = self.motors.getLimits()
            if len(faces)>0:
                self.first_time = True
                width = self.camera.client.getImage().width
                height = self.camera.client.getImage().height
                imgXCenter = width/2
                imgYCenter = height/2
                
                #Find out if the X component of the face is to the left of the middle of the image.
                if(center[0] < (imgXCenter - 60)):
                    self.pan -= 2
                    print str(center[0]) + " > " + str(imgXCenter) + " : Pan Right : " + str(self.pan)
                 #Find out if the X component of the face is to the right of the middle of the image.
                elif(center[0] > (imgXCenter + 60)):
                    self.pan += 2
                    print str(center[0]) + " < " + str(imgXCenter) + " : Pan Left : " + str(self.pan)
                else:
                    print str(center[0]) + " ~ " + str(imgXCenter) + " : " + str(self.pan)

                # Consider min and max Pan value of the camera
                self.pan = min(self.pan, limits.maxPan)
                self.pan = max(self.pan, limits.minPan) 

                #Find out if the Y component of the face is to the left of the middle of the image.
                if(center[1] < (imgYCenter - 60)):
                    self.tilt += 2
                    print str(center[1]) + " > " + str(imgYCenter) + " : Tilt Down : " + str(self.tilt)
                 #Find out if the Y component of the face is to the right of the middle of the image.
                elif(center[1] > (imgYCenter + 60)):
                    self.tilt -= 2
                    print str(center[1]) + " < " + str(imgYCenter) + " : Tilt Up : " + str(self.tilt)
                else:
                    print str(center[1]) + " ~ " + str(imgYCenter) + " : " + str(self.tilt)

                # Consider min and max Tilt value of the camera 
                self.tilt = min(self.tilt, limits.maxTilt)
                self.tilt = max(self.tilt, limits.minTilt) 
                
                # Send orders to the camera
                if (self.motors):
                        self.motors.setPTMotorsData(self.pan, self.tilt, limits.maxPanSpeed, limits.maxTiltSpeed)
            else:
                # If no face is found in the image, 
                #   - It waits 5 seconds
                #   - It starts searching in X axis.

                if self.first_time:
                    self.time = datetime.now()
                    self.first_time = False
                
                diff = datetime.now() - self.time
                time_since_last_detection = (diff.days*24*60*60+diff.seconds)
                print "Time since last detection: " + str(time_since_last_detection) + " seconds"

                if time_since_last_detection >= 5.0:
                    print ">>>>>>>>>>>>>>>>>>>>>>"
                    print "TRYING TO DETECT FACES"
                    print ">>>>>>>>>>>>>>>>>>>>>>"

                    if self.pan >= limits.maxPan:
                        self.topright = True
                        self.pan = limits.maxPan
                    elif self.pan <= limits.minPan:
                        self.topright = False
                        self.pan = limits.minPan

                    if not self.topright:
                        self.pan += 1
                    else:
                        self.pan -= 1

                    self.motors.setPTMotorsData(self.pan, 0, limits.maxPanSpeed, limits.maxTiltSpeed)
                    

