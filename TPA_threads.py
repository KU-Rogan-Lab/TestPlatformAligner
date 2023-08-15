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
#  - Turn tIP.ratio into the scale factor I want


class CommObject:
    # The communication object that is getting passed between threads.
    # Right now this is kind of just a bastardized dict, but I made it a class so I can add methods if needed
    def __init__(self, c_type, priority, content, id_num):
        """Constructor."""
        self.c_type = c_type
        self.priority = priority
        self.content = content
        self.id_num = id_num


class UserInterface(Thread):
    def __init__(self):
        """Constructor."""
        # Get the queues used for communication
        global Q_cmd_tUI_to_tLS
        global Q_cmd_tUI_to_tGK
        global Q_cmd_tUI_to_tIP
        global Q_cmd_tUI_to_tMC
        global Q_hw_tUI_to_tGK

        Thread.__init__(self)

    def run(self):
        pass


class GateKeeper(Thread):
    def __init__(self):
        """Constructor."""
        # Get the queues used for communication
        global Q_hw_tUI_to_tGK
        global Q_hw_tLS_to_tGK
        global Q_hw_tIP_to_tGK
        global Q_hw_tMC_to_tGK

        Thread.__init__(self)

    def run(self):
        pass


class ImageParser(Thread):
    def __init__(self, camera=0, img_size=(1000, 1000), frame_rate=30, visualize_data=True):
        """Constructor"""

        # Get the queues used for communication
        global Q_hw_tIP_to_tGK
        global Q_cmd_tUI_to_tIP
        
        self.camera = camera
        self.img_size = img_size
        self.frame_rate = frame_rate
        self.visualize_data = visualize_data

        # todo Set up queues here

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
        """Wrap up the thread's business and stop."""
        cv.destroyAllWindows()

    def run(self):
        """Run the main behavior of the thread."""
        E_SB_not_obscuring.wait()  # Comment this out to test imageParser on its own
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
            
        print("Press 'q' to close\nPress 't' to correct perspective")

        tpr = time.time()

        while True:
            if cv.waitKey(1) & 0xFF == ord('q'):
                self.stop()
                exit()
                
            if cv.waitKey(30) & 0xFF == ord('t'):  # Tells it to re-calculate the perspective transform
                self.transformation_found = False

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

            # Read the image and rotate it to be right-side-up
            self.image = vs.read()
            self.image = cv.rotate(self.image, cv.ROTATE_90_COUNTERCLOCKWISE)

            # Keep reading images until we get an image that is not just black
            if np.max(self.image) == 0:
                continue
            
            # Consider dropping this resize step if it is having trouble seeing small QR codes
            self.image = cv.resize(self.image, (int(self.img_size[0] * self.ratio), int(self.img_size[1] * self.ratio)),
                                   interpolation=cv.INTER_AREA)

            # Calculate the perspective transformation matrix if you do not have it already
            if not self.transformation_found:
                
                try:
                    # Find colorful screw image coordinates (anchor points)
                    anchor_coords = utl.findAnchorPoints(img=self.image, visualize=True, low=self.anchor_lower_color,
                                                         high=self.anchor_upper_color)
                    # Order the anchor points (TL, TR, BR, BL)
                    untransformed_points = utl.orderAnchorPoints(np.array([anchor_coords[0], anchor_coords[1],
                                                                          anchor_coords[2], anchor_coords[3]]))
                    # Find the perspective transform matrix from the anchor points
                    self.transform = cv.getPerspectiveTransform(untransformed_points, self.target_points)
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
                        anchor_coords = utl.findAnchorPoints(img=self.image, visualize=True, low=self.anchor_lower_color,
                                                            high=self.anchor_upper_color)
                        orderedAnchors = utl.orderAnchorPoints(np.array([anchor_coords[0], anchor_coords[1],
                                                                         anchor_coords[2], anchor_coords[3]]))
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
            
            # Set emitter_coords based off of laserCoords and a predefined offset
            if self.laser_dot_found:
                if not self.Q_LaserPositionOut.full():
                    self.Q_LaserPositionOut.put(laserCoords)
                    
                emitter_coords = (laserCoords[0] + self.emitter_x_offset, laserCoords[1] + self.emitter_y_offset)
            
            # If all data is ready for tMC, tell tMC
            if self.transformation_found and self.laser_dot_found and self.tl_anchor_found:
                E_tIP_data_flowing.set()

            # if self.visualize_data:
            #     if self.laser_dot_found:
            #         cv.putText(self.image, f'. Laser Dot ({laserCoords[0]},{laserCoords[1]})', laserCoords,
            #                    cv.FONT_HERSHEY_SIMPLEX, 0.5, (255, 200, 50), 2)
            #         cv.putText(self.image, f'. Emitter Slit ({emitter_coords[0]},{emitter_coords[1]})', emitter_coords,
            #                    cv.FONT_HERSHEY_SIMPLEX, 0.5, (255, 200, 50), 2)
            #
            #     scaleSquareCoord = int(10 + 10 * (self.pixel2mm_constant ** -1))
            #     cv.rectangle(self.image, (10,10), (scaleSquareCoord, scaleSquareCoord), (255, 200, 50), 2)
            #     cv.putText(self.image, '10 mm', (scaleSquareCoord + 5, scaleSquareCoord), cv.FONT_HERSHEY_SIMPLEX, 0.5,
            #                (255, 200, 50), 2)
                
#                 a = self.transform.dot((anchor_coords[0][0], anchor_coords[0][1], 1))
#                 a /= a[2]
#                 cv.putText(self.image, f'{a}', (10,100), cv.FONT_HERSHEY_SIMPLEX, 0.5, (255,200,50), 2)
                
                #TODO: This above bit works, but because the anchor points never get updated, it will always just
                # output [350,650,1] for a. And really, the code is not written to ever update the anchor points.
                # Talk to Jack/maybe other people at the lab meeting to figure out if we can just assume the anchor
                # points will not be moving

            print('-----')
            cv.imshow('Camera Feed', self.image)


class MotorControl(Thread):
    def __init__(self):
        """Constructor."""

        # Get the queues used for communication
        global Q_hw_tMC_to_tGK
        global Q_cmd_tUI_to_tMC

        self.motors = motion.motion(port='/dev/ttyACM0', emulate=False)
        
        self.avg_laser_pos = (-1, -1)
        self.avg_tl_anchor_pos = (-1, -1)
        
        Thread.__init__(self)
        
    def stop(self):
        cv.destroyAllWindows()
        self.motors.moveTo(0, 0)
    
    def run(self):
        # We are assuming that the sensor head is already at its home position, which is off in the +x +y corner
        self.motors.setHome()
        E_SB_not_obscuring.set()  # Tell tIP the source box is out of the way
        
        E_tIP_data_flowing.wait()  # Wait until tIP is producing its data
        
        # Main loop, all very OkR
        while True:
                
            self.avg_laser_pos = tIP.Q_LaserPositionOut.get()
            self.avg_tl_anchor_pos = tIP.Q_TLAnchorPositionOut.get()
            
            E_StartAutoAlign.wait()
            
            goodPositions = messagebox.askyesno('Confirm Positions & Arm Move',
                                                f'Are the following positions correct?\n'
                                                f'Laser Dot: {self.avg_laser_pos}\n'
                                                f'TL Anchor Position: {self.avg_tl_anchor_pos}')
            
            if not goodPositions:
                E_StartAutoAlign.clear()
                continue
            
            elif goodPositions:
                E_StartAutoAlign.clear()
                # Multiply by -1 for armMoveX because camera and motors have opposite x-axis directions
                armMoveX = (self.avg_tl_anchor_pos[0] + 102 - self.avg_laser_pos[0]) * -1
                armMoveY = (self.avg_tl_anchor_pos[1] + 102 - self.avg_laser_pos[1])
                
                armMove = (tIP.pixel2mm_constant * armMoveX, tIP.pixel2mm_constant * armMoveY)
                
                self.motors.moveFor(armMove[0], armMove[1], 0)
        

class Listener(Thread):
    def __init__(self):
        """Constructor."""

        # Get the queues used to communicate
        global Q_cmd_tUI_to_tLS
        global Q_hw_tLS_to_tGK
        Thread.__init__(self)

    def run(self):
        pass


if __name__ == '__main__':

    # Create all the queues being used
    # Nomenclature is Q_[communication type]_[sending thread]_to_[receiving thread]
    # When referencing them inside a thread, name them Q_[communication type]_[other thread]_[in/out]
    # These are the command ("cmd") queues, used for threads asking other threads to do things
    Q_cmd_tUI_to_tGK = Queue()
    Q_cmd_tUI_to_tIP = Queue()
    Q_cmd_tUI_to_tMC = Queue()
    Q_cmd_tUI_to_tLS = Queue()
    # These are the hardware control ("hw") queues, used specifially for threads sending hardware commands to tGK
    Q_hw_tUI_to_tGK = Queue()
    Q_hw_tIP_to_tGK = Queue()
    Q_hw_tMC_to_tGK = Queue()
    Q_hw_tLS_to_tGK = Queue()

    # Create all the threads being used
    tUI = UserInterface()
    tGK = GateKeeper()
    tIP = ImageParser(camera=('autovideosrc device=/dev/video2 ! appsink'))
    tMC = MotorControl()
    tLS = Listener()

    # Create all the events/conditions/locks used to communicate between threads
    E_SB_not_obscuring = Event()  # Event used to tell tIP the source box has been moved out of the way
    E_tIP_data_flowing = Event()  # Event used to tell tMC that tIP is now producing data
    
    # Start all the threads
#     tIP.run()
    tUI.start()
    tGK.start()
    tIP.start()
    tMC.start()
    tLS.start()