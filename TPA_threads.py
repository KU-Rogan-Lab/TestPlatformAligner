from threading import Thread, Lock, Event
from queue import Queue, PriorityQueue
from collections import deque
from imutils.video import VideoStream, FPS, perspective
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
import utils as utl  # A local file containing various utility functions

# TODO:
#  - Standardize what variables are self. vars and what are globals
#  - Figure out if you *really* need queues for this
#  - Update any OkR-commented lines


class UserInterface(Thread):
    def __init__(self):
        Thread.__init__(self)

    def run(self):
        pass


class GateKeeper(Thread):
    def __init__(self):
        Thread.__init__(self)

    def run(self):
        pass


class ImageParser(Thread):
    def __init__(self, camera=0, img_size=(1000, 1000), frame_rate=30, visualize_data=True):
        """Constructor"""
        
        self.camera = camera
        self.img_size = img_size
        self.frame_rate = frame_rate
        self.visualize_data = visualize_data
        
        # The target points for the image transform
        # These represent the "true" dimensions of the anchors in pixels,
        # they MUST be in (TL, TR, BR, BL) order, 
        # and they must keep to the same aspect ratio as self.true_anchor_dimensions
        self.target_points = np.float32([[400, 400], [600, 400], [600, 600], [400, 600]])
        
        # The true dimensions of the anchor points in mm
        self.true_anchor_dimensions = (98.8, 98.8)
        
        # A calculated constant to convert between pixels and mm in the post-transform image
        self.pixel2mm_constant = self.true_anchor_dimensions[0] / (self.target_points[1][0] - self.target_points[0][0])
        
        # The x and y pixel offsets to get from the position of the laser dot to the position of the emitter slit
        # Given as [mm distance] * self.pixel2mm_constant**-1
        self.emitter_x_offset = int(-98 * self.pixel2mm_constant ** -1)
        self.emitter_y_offset = int(-18.5 * self.pixel2mm_constant ** -1)
        
        # The x and y pixel offsets to get from the position of some anchor point (which one is defined below) to
        # the position of the sensor.
        # Given as [mm distance] * self.pixel2mm_constant**-1
        self.sensor_x_offset = int(15 * self.pixel2mm_constant ** -1)
        self.sensor_y_offset = int(25 * self.pixel2mm_constant ** -1)
        
        self.threshold = 245  # The threshold used when thresholding the image to look for the laser dot
        
        # These color boundaries will need to be fine-tuned for the specific anchors and lighting being used
        self.anchor_lower_color = np.array([60, 40, 40])  # Lower bound of the color of the anchor objects (HSV format)
        self.anchor_upper_color = np.array([90, 255, 255])  # Upper bound of the color of the anchor objects (HSV format)

        self.camera_started = True

        self.inqueue = deque(maxlen=1)
        self.outqueue = deque(maxlen=1)
        
        self.ratio = 1
        
        self.transformation_found = False
        self.laser_dot_found = False
        self.tl_anchor_found = False

        self.transform = np.array([[], [], []])
        self.image = np.array([[0, 0, 0]])
        self.qr_codes_found = []

        # # Defining all the queues used to send data out of the thread
        # self.Q_LaserPositionOut = queue.Queue(maxsize=1)
        # self.Q_TLAnchorPositionOut = queue.Queue(maxsize=1)
        # self.Q_QRDataOut = queue.Queue(maxsize=1)
 
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
        E_SBNotObscuring.wait()  # Comment this out to test imageParser on its own
        # PLACEHOLDER: Full Light
        
        # Runs the libcamera-hello command line utility for its built-in autofocus
        # If it's stupid but it works, it's not stupid
        os.system("libcamera-hello -n -t 2000")
        
        vs = VideoStream(src=self.camera, usePiCamera=False, resolution=self.img_size, framerate=30)
        vs.start()
        self.camera_started = True

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
                self.transformation_found = False

            if len(self.inqueue) > 0:
                if 'pause' in self.inqueue:
                    # print(f'waiting... {self.inqueue}')
                    if self.camera_started:
                        vs.stop()
                        del vs
                        self.camera_started = False
                    time.sleep(1)
                    continue
                if 'exit' in self.inqueue:
                    break

            if not self.camera_started:
                vs = VideoStream(src=self.camera, resolution=self.img_size, framerate=self.frame_rate)
                vs.start()
                self.camera_started = True
                while vs.read() is None:
                    print('camera not available... ')
                    time.sleep(1)

            if True:
                # PLACEHOLDER: Check if imageParser has permission to control the lights
                # Lights on to see the screws when finding transform (screws are transform points),
                # lights dim for better laser finding afterwards
                if not self.transformation_found:
                    # PLACEHOLDER: Full Light
                    pass
                    
                elif self.transformation_found:
                    # PLACEHOLDER: Dim Light
                    pass

            self.image = vs.read()
            self.image = cv.rotate(self.image, cv.ROTATE_90_COUNTERCLOCKWISE)
            
            if np.max(self.image) == 0:
                continue
            
            # Consider dropping this resize step if it is having trouble seeing small QR codes
            self.image = cv.resize(self.image, (int(self.img_size[0] * self.ratio), int(self.img_size[1] * self.ratio)),
                                   interpolation=cv.INTER_AREA)

            # Calculate the perspective transformation matrix if you do not have it already
            if not self.transformation_found:
                
                try:
                    # Find colorful screw image coordinates (anchor points)
                    anchorCoords = utl.findAnchorPoints(img=self.image, visualize=True, low=self.anchor_lower_color,
                                                        high=self.anchor_upper_color)
                    # Order the anchor points (TL, TR, BR, BL)
                    untransformedPoints = utl.orderAnchorPoints(np.array([anchorCoords[0], anchorCoords[1],
                                                                          anchorCoords[2], anchorCoords[3]]))
                    # Find the perspective transform matrix from the anchor points
                    self.transform = cv.getPerspectiveTransform(untransformedPoints, self.target_points)
                    self.transformation_found = True
                
                except:  # You should not be using bare excepts! todo fix this
                    print('Could not find the perspective transform')
                
            if self.transformation_found:
                self.image = cv.warpPerspective(self.image, self.transform, (1000, 1000))
                
                # Only look for QR codes after finding transform to avoid wasting time looking for super warped codes
                # Commented out to mute for OkR demo
                # And, only look for the code once to further avoid time loss
#                 if self.qr_codes_found == []:
#                     self.qr_codes_found = utl.decode(self.image)
                
                # Find the pixel coordinates of the top-left anchor in the image
                if not self.Q_TLAnchorPositionOut.full():  # OkR Sort of a slapped-together framerate fix
                    try:
                        anchorCoords = utl.findAnchorPoints(img=self.image, visualize=True, low=self.anchor_lower_color,
                                                            high=self.anchor_upper_color)
                        orderedAnchors = utl.orderAnchorPoints(np.array([anchorCoords[0], anchorCoords[1],
                                                                         anchorCoords[2], anchorCoords[3]]))
                        tlAnchorPos = orderedAnchors[0]
                        self.tl_anchor_found = True
                        
                    except:
                        pass  # OkR This is bad, fix this
                
                # Append the position of the top-left anchor to its out-queue
                if self.tl_anchor_found and not self.Q_TLAnchorPositionOut.full():
                    self.Q_TLAnchorPositionOut.put(tlAnchorPos)
            
            # Try to find the coords of the laser dot in the image
            laserCoords = utl.findLaserPoint(img=self.image, visualize=True, threshold=self.threshold)
            
            # Set self.laser_dot_found to True or False based on if we could find it
            if laserCoords == (-1,-1):  # utl.findLaserPoint returning (-1,-1) indicates that it found nothing
                self.laser_dot_found = False
                # PLACEHOLDER: Try wiggling the motor
            elif laserCoords != (-1, -1):
                self.laser_dot_found = True
            
            # Set emitterCoords based off of laserCoords and a predefined offset
            if self.laser_dot_found:
                if not self.Q_LaserPositionOut.full():
                    self.Q_LaserPositionOut.put(laserCoords)
                    
                emitterCoords = (laserCoords[0] + self.emitter_x_offset, laserCoords[1] + self.emitter_y_offset)
            
            # If all data is ready for tMC, tell tMC
            if self.transformation_found and self.laser_dot_found and self.tl_anchor_found:
                E_iPDataFlowing.set()

            if self.visualize_data:
                if self.laser_dot_found:
                    cv.putText(self.image, f'. Laser Dot ({laserCoords[0]},{laserCoords[1]})', laserCoords,
                               cv.FONT_HERSHEY_SIMPLEX, 0.5, (255, 200, 50), 2)
                    cv.putText(self.image, f'. Emitter Slit ({emitterCoords[0]},{emitterCoords[1]})', emitterCoords,
                               cv.FONT_HERSHEY_SIMPLEX, 0.5, (255, 200, 50), 2)
                
                scaleSquareCoord = int(10 + 10 * (self.pixel2mm_constant ** -1))
                cv.rectangle(self.image, (10,10), (scaleSquareCoord, scaleSquareCoord), (255, 200, 50), 2)
                cv.putText(self.image, '10 mm', (scaleSquareCoord + 5, scaleSquareCoord), cv.FONT_HERSHEY_SIMPLEX, 0.5,
                           (255, 200, 50), 2)
                
#                 a = self.transform.dot((anchorCoords[0][0], anchorCoords[0][1], 1))
#                 a /= a[2]
#                 cv.putText(self.image, f'{a}', (10,100), cv.FONT_HERSHEY_SIMPLEX, 0.5, (255,200,50), 2)
                
                #TODO: This above bit works, but because the anchor points never get updated, it will always just
                # output [350,650,1] for a. And really, the code is not written to ever update the anchor points.
                # Talk to Jack/maybe other people at the lab meeting to figure out if we can just assume the anchor
                # points will not be moving

            print('-----')
            cv.imshow('Camera Feed', self.image)
            
        # Stop the timer and display FPS information
        fps.stop()
        try:
            vs.stop()
        except:
            pass


class MotorControl(Thread):
    def __init__(self):
        self.motors = motion.motion(port='/dev/ttyACM0', emulate=False)
        
        self.avgLaserPos = (-1, -1)
        self.avgTLAnchorPos = (-1, -1)
        
        Thread.__init__(self)
        
    def stop(self):
        cv.destroyAllWindows()
        self.motors.moveTo(0, 0)
    
    def run(self):
        # We are assuming that the sensor head is already at its home position, which is off in the +x +y corner
        self.motors.setHome()
        E_SBNotObscuring.set()  # Tell tIP the source box is out of the way
        
        E_iPDataFlowing.wait()  # Wait until tIP is producing its data
        
        # Main loop, all very OkR
        while True:
                
            self.avgLaserPos = tIP.Q_LaserPositionOut.get()
            self.avgTLAnchorPos = tIP.Q_TLAnchorPositionOut.get()
            
            E_StartAutoAlign.wait()
            
            goodPositions = messagebox.askyesno('Confirm Positions & Arm Move',
                                                f'Are the following positions correct?\n'
                                                f'Laser Dot: {self.avgLaserPos}\n'
                                                f'TL Anchor Position: {self.avgTLAnchorPos}')
            
            if not goodPositions:
                E_StartAutoAlign.clear()
                continue
            
            elif goodPositions:
                E_StartAutoAlign.clear()
                # Multiply by -1 for armMoveX because camera and motors have opposite x-axis directions
                armMoveX = (self.avgTLAnchorPos[0] + 102 - self.avgLaserPos[0]) * -1
                armMoveY = (self.avgTLAnchorPos[1] + 102 - self.avgLaserPos[1])
                
                armMove = (tIP.pixel2mm_constant * armMoveX, tIP.pixel2mm_constant * armMoveY)
                
                self.motors.moveFor(armMove[0], armMove[1], 0)
        

class Listener(Thread):
    def __init__(self):
        Thread.__init__(self)

    def run(self):
        pass


if __name__ == '__main__':

    # Create all the queues being used
    Q_tUI_to_tIP = Queue()

    # Create all the threads being used
    tUI = UserInterface()
    tGK = GateKeeper()
    tIP = ImageParser(camera=('autovideosrc device=/dev/video2 ! appsink'))
    tMC = MotorControl()
    tLS = Listener()

    # Create all the events/conditions/locks used to communicate between threads
    E_SBNotObscuring = Event()  # Event used to tell tIP the source box has been moved out of the way
    E_iPDataFlowing = Event()  # Event used to tell tMC that tIP is now producing data
    
    # Start all the threads
#     tIP.run()
    tUI.start()
    tGK.start()
    tIP.start()
    tMC.start()
    tLS.start()
    


