# This is a modified version of the pivideostream.py module in the imutils package, written by Aidan Novo specifically
# for the KU Rogan Lab Test Platform Aligner Project.
#
# Specifically, it has been modified to better work with the ArduCam IMX519 Autofocus Camera which is being used on the
# test platform.

import picamera2
from picamera2 import Picamera2
from threading import Thread
import cv2


class PiVideoStream:
    def __init__(self, resolution=(320, 240), framerate=30, autofocus=True):
        # initialize the camera
        self.picam2 = Picamera2()

        # set camera parameters
        camera_config = self.picam2.create_video_configuration(main={'size': resolution, 'format': 'RGB888'},
                                                               controls={'FrameDurationLimits': (int(1000000/framerate),
                                                                                                 int(1000000/framerate))})
        self.picam2.configure(camera_config)
        self.picam2.start()

        if autofocus:
            self.picam2.set_controls({'AfTrigger': 0})
            self.picam2.set_controls({'AfMode': 1})

        # initialize the capture and the variable used to indicate
        # if the thread should be stopped
        self.capture = None
        self.stopped = False

    def start(self):
        # start the thread to read frames from the video stream
        t = Thread(target=self.update, args=())
        t.daemon = True
        t.start()
        return self

    def update(self):
        # keep looping infinitely until the thread is stopped
        while True:
            self.capture = self.picam2.capture_array('main')

            # if the thread indicator variable is set, stop the thread
            # and resource camera resources
            if self.stopped:
                self.picam2.stop()
                return

    def read(self):
        # return the frame most recently read
        return self.capture

    def stop(self):
        # indicate that the thread should be stopped
        self.stopped = True
