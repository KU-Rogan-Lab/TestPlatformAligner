from threading import Thread
from threading import Lock
from threading import Event
from collections import deque
from imutils.video import VideoStream
from imutils.video import FPS
from imutils import perspective
from tkinter import messagebox
import argparse
import cv2 as cv
import imutils
import motion
import numpy as np
import os
import queue
import time
import tkinter as tk
import utils as utl # A local file containing various utility functions

# TODO:
# - Standardize what variables are self. vars and what are globals
# - Figure out if you *really* need queues for this
# - Update any OkR-commented lines

class imageParser(Thread):
    def __init__(self, camera=0, imgSize=(1000,1000), frameRate=30, visualizeData=True):
        # Constructor
        
        self.camera = camera
        self.cameraImgSize = imgSize
        self.frameRate = frameRate
        self.visualizeData = visualizeData
        
        # The target points for the image transform
        # These represent the "true" dimensions of the anchors in pixels,
        # they MUST be in (TL, TR, BR, BL) order, 
        # and they must keep to the same aspect ratio as self.trueAnchorDimensions
        self.targetPoints = np.float32([[400, 400], [600, 400], [600, 600], [400, 600]])
        
        # The true dimensions of the anchor points in mm
        self.trueAnchorDimensions = (98.8, 98.8)
        
        # A calculated constant to convert between pixels and mm in the post-transform image
        self.pixel2mmConstant = self.trueAnchorDimensions[0] / (self.targetPoints[1][0] - self.targetPoints[0][0])
        
        # The x and y pixel offsets to get from the position of the laser dot to the position of the emitter slit
        # Given as [mm distance] * self.pixel2mmConstant**-1
        self.emitterXOffset = int(-98 * self.pixel2mmConstant**-1)
        self.emitterYOffset = int(-18.5 * self.pixel2mmConstant**-1)
        
        # The x and y pixel offsets to get from the position of some anchor point (which one is defined below) to
        # the position of the sensor.
        # Given as [mm distance] * self.pixel2mmConstant**-1
        self.sensorXOffset = int(15 * self.pixel2mmConstant**-1)
        self.sensorYOffset = int(25 * self.pixel2mmConstant**-1)
        
        self.threshold = 245 # The threshold used when thresholding the image to look for the laser dot
        
        # These color boundaries will need to be fine-tuned for the specific anchors and lighting being used
        self.anchorLowerColor = np.array([60, 40, 40]) # The 1lower bound of the color of the anchor objects (HSV format)
        self.anchorUpperColor = np.array([90, 255, 255]) # The upper bound of the color of the anchor objects (HSV format)

        self.cameraStarted = True

        self.inqueue = deque(maxlen=1)
        self.outqueue = deque(maxlen=1)
        
        self.ratio = 1
        
        self.transformationFound = False
        self.laserDotFound = False
        self.tlAnchorFound = False


        self.transform = np.array([[], [], []])
        self.image = np.array([[0,0,0]])
        self.qrCodesFound = []
        
        
        # Defining all the queues used to send data out of the thread
        self.Q_LaserPositionOut = queue.Queue(maxsize=1)
        self.Q_TLAnchorPositionOut = queue.Queue(maxsize=1)
        self.Q_QRDataOut = queue.Queue(maxsize=1)
 
        Thread.__init__(self) 

    def __del__(self):
        cv.destroyAllWindows()

    def stop(self):
        self.outqueue.clear()
        cv.destroyAllWindows()

    def getOutQueue(self):
        return self.outqueue

    def getInQueue(self):
        return self.inqueue

    def run(self):
        E_SBNotObscuring.wait() # Comment this out to test imageParser on its own
        # PLACEHOLDER: Full Light
        
        # Runs the libcamera-hello command line utility for its built-in autofocus
        # If it's stupid but it works it's not stupid        
        os.system("libcamera-hello -n -t 2000")
        
        vs = VideoStream(src=self.camera, usePiCamera=False, resolution=self.cameraImgSize, framerate=30)
        vs.start()
        self.cameraStarted = True    

        while vs.read() is None:
            print('camera not available... ')
            print(vs.read())    

            time.sleep(1)
            
        print("Press 'q' to close \nPress 't' to correct perspective")
        
        fps = FPS().start()
        tpr = time.time()

        while True:
            if cv.waitKey(1) & 0xFF == ord('q'):
                self.stop()
                exit()
                
            if cv.waitKey(30) & 0xFF == ord('t'):  # Tells it to re-calculate the perspective transform
                self.transformationFound = False
                
#             if cv.waitKey(1) & 0xFF == ord('a'):  # Tells it to retry the autofocus
#                 print('Retrying autofocus')
#                 os.system("libcamera-hello -n -t 2000")  # Currently not working, this fights with the VideoStream for control of the camera
                
            if len(self.inqueue)>0:
                if 'pause' in self.inqueue:
                    # print(f'waiting... {self.inqueue}')
                    if self.cameraStarted:
                        vs.stop()
                        del vs
                        self.cameraStarted = False
                    time.sleep(1)
                    continue
                if 'exit' in self.inqueue:
                    break

            if not self.cameraStarted:
                vs = VideoStream(src=self.camera, resolution=self.cameraImgSize, framerate=self.frameRate)
                vs.start()
                self.cameraStarted = True
                while vs.read() is None:
                    print('camera not available... ')
                    time.sleep(1)

            if True:
                # PLACEHOLDER: Check if imageParser has permission to control the lights
                # Lights on to see the screws when finding transform (screws are transform points), lights dim for better laser finding afterwards
                if not self.transformationFound:
                    # PLACEHOLDER: Full Light
                    pass
                    
                elif self.transformationFound:
                    # PLACEHOLDER: Dim Light
                    pass

            self.image = vs.read()
            self.image = cv.rotate(self.image, cv.ROTATE_90_COUNTERCLOCKWISE)
            
            if np.max(self.image) == 0:
                continue
            
            # Consider dropping this resize step if it is having trouble seeing small QR codes
            self.image = cv.resize(self.image, (int(self.cameraImgSize[0]*self.ratio),int(self.cameraImgSize[1]*self.ratio)), interpolation=cv.INTER_AREA)                

            # Calculate the perspective transformation matrix if you do not have it already
            if not self.transformationFound:
                
                try:
                    # Find colorful screw image coordinates (anchor points)
                    anchorCoords = utl.findAnchorPoints(img=self.image, visualize=True, low=self.anchorLowerColor, high=self.anchorUpperColor)
                    # Order the anchor points (TL, TR, BR, BL)
                    untransformedPoints = utl.orderAnchorPoints(np.array([anchorCoords[0], anchorCoords[1], anchorCoords[2], anchorCoords[3]]))
                    # Find the perspective transform matrix from the anchor points
                    self.transform = cv.getPerspectiveTransform(untransformedPoints, self.targetPoints)
                    self.transformationFound = True
                
                except:
                    print('Could not find the perspective transform')
                
            if self.transformationFound:
                self.image = cv.warpPerspective(self.image, self.transform, (1000, 1000))
                
                # Only look for QR codes after finding transform to avoid wasting time looking for super warped codes
                # Commented out to mute for OkR demo
                # And, only look for the code once to further avoid time loss
#                 if self.qrCodesFound == []:
#                     self.qrCodesFound = utl.decode(self.image)
                
                # Find the pixel coordinates of the top-left anchor in the image
                if not self.Q_TLAnchorPositionOut.full(): # OkR Sort of a slapped-together framerate fix
                    try:
                        anchorCoords = utl.findAnchorPoints(img=self.image, visualize=True, low=self.anchorLowerColor, high=self.anchorUpperColor)
                        orderedAnchors = utl.orderAnchorPoints(np.array([anchorCoords[0], anchorCoords[1], anchorCoords[2], anchorCoords[3]]))
                        tlAnchorPos = orderedAnchors[0]
                        self.tlAnchorFound = True
                        
                    except:
                        pass # OkR This is bad, fix this
                
                # Append the position of the top-left anchor to its out-queue
                if self.tlAnchorFound and not self.Q_TLAnchorPositionOut.full():
                    self.Q_TLAnchorPositionOut.put(tlAnchorPos)
            
            # Try to find the coords of the laser dot in the image
            laserCoords = utl.findLaserPoint(img=self.image, visualize=True, threshold=self.threshold)
            
            # Set self.laserDotFound to True or False based on if we could find it
            if laserCoords == (-1,-1): # utl.findLaserPoint returning (-1,-1) indicates that it found nothing
                self.laserDotFound = False 
                # PLACEHOLDER: Try wiggling the motor
            elif laserCoords != (-1, -1):
                self.laserDotFound = True
            
            # Set emitterCoords based off of laserCoords and a predefined offset
            if self.laserDotFound:
                if not self.Q_LaserPositionOut.full():
                    self.Q_LaserPositionOut.put(laserCoords)
                    
                emitterCoords = (laserCoords[0] + self.emitterXOffset, laserCoords[1] + self.emitterYOffset)
            
            # If all data is ready for mCR, tell mCR
            if self.transformationFound and self.laserDotFound and self.tlAnchorFound:
                E_iPDataFlowing.set()

            
            if self.visualizeData:
                if self.laserDotFound:
                    cv.putText(self.image, f'. Laser Dot ({laserCoords[0]},{laserCoords[1]})', laserCoords, cv.FONT_HERSHEY_SIMPLEX, 0.5, (255,200,50), 2)
                    cv.putText(self.image, f'. Emitter Slit ({emitterCoords[0]},{emitterCoords[1]})', emitterCoords, cv.FONT_HERSHEY_SIMPLEX, 0.5, (255,200,50), 2)
                
                scaleSquareCoord = int(10 + 10*(self.pixel2mmConstant ** -1))
                cv.rectangle(self.image, (10,10), (scaleSquareCoord, scaleSquareCoord), (255,200,50), 2)
                cv.putText(self.image, '10 mm', (scaleSquareCoord + 5, scaleSquareCoord), cv.FONT_HERSHEY_SIMPLEX, 0.5, (255,200,50), 2)
                
#                 a = self.transform.dot((anchorCoords[0][0], anchorCoords[0][1], 1))
#                 a /= a[2]
#                 cv.putText(self.image, f'{a}', (10,100), cv.FONT_HERSHEY_SIMPLEX, 0.5, (255,200,50), 2)
                
                #TODO: This above bit works, but because the anchor points never get updated, it will always just
                # output [350,650,1] for a. And really, the code is not written to ever update the anchor points.
                # Talk to Jack/maybe other people at the lab meeting to figure out if we can just assume the anchor points will
                # not be moving
            
            print('-----')
            cv.imshow('Camera Feed', self.image)

            
        # stop the timer and display FPS information
        fps.stop()
        try:
            vs.stop()
        except:
            pass

class motorControlRough(Thread):
    def __init__(self):
        self.motors = motion.motion(port='/dev/ttyACM0', emulate=False)
        
        self.avgLaserPos = (-1,-1)
        self.avgTLAnchorPos = (-1,-1)
        
        Thread.__init__(self)
        
    def stop(self):
        cv.destroyAllWindows()
        self.motors.moveTo(0,0)
    
    def run(self):
        # We are assuming that the sensor head is already at its home position, which is off in the +x +y corner
        self.motors.setHome()
        E_SBNotObscuring.set() # Tell iP the source box is out of the way
        
        E_iPDataFlowing.wait() # Wait until iP is producing its data
        
        # Main loop, all very OkR
        while True:
                
            self.avgLaserPos = iP.Q_LaserPositionOut.get()
            self.avgTLAnchorPos = iP.Q_TLAnchorPositionOut.get()
            
            E_StartAutoAlign.wait()
            
            goodPositions = messagebox.askyesno('Confirm Positions & Arm Move', \
                                                f'''Are the following positions correct?
Laser Dot: {self.avgLaserPos}
TL Anchor Position: {self.avgTLAnchorPos}''')
            
            if not goodPositions:
                E_StartAutoAlign.clear()
                continue
            
            elif goodPositions:
                E_StartAutoAlign.clear()
                armMoveX = (self.avgTLAnchorPos[0] + 102 - self.avgLaserPos[0]) * -1 # Multiply by -1 because camera and motors have opposite x-axis directions
                armMoveY = (self.avgTLAnchorPos[1] + 102 - self.avgLaserPos[1])
                
                armMove = (iP.pixel2mmConstant * armMoveX, iP.pixel2mmConstant * armMoveY)
                
                self.motors.moveFor(armMove[0], armMove[1], 0)
                
        

# Development on the gateKeeper thread is paused until after the Oak Ridge visit
class gateKeeper(Thread):
    def __init__(self):
        Thread.__init__(self)

    def run(self):
        pass
        


if __name__ == '__main__':
    
    # Create all the threads being used
    iP = imageParser(camera=('autovideosrc device=/dev/video2 ! appsink'))
    mCR = motorControlRough()
    gK = gateKeeper()
    
    # Create all the events/conditions/locks used to communicate between threads
    E_SBNotObscuring = Event() # Event used to tell iP the source box has been moved out of the way
    E_iPDataFlowing = Event() # Event used to tell mCR that iP is now producing data
    
    # Start all the threads
#     iP.run()
    iP.start()
    mCR.start()
    


