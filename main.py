# from threading import Thread, Lock, Event
# from queue import Queue
# from collections import deque
# from imutils.video import VideoStream, FPS
# from tkinter import messagebox
# import argparse
# import cv2 as cv
# import imutils
# import motion
# import numpy as np
# import os
# import queue
# import time
# import tkinter as tk
# import utils as utl  # A local file containing various utility functions

import tGK, tIP, tLS, tMC, tUI

# TODO:
#  - Standardize what variables are self. vars and what are globals
#  - Update any OkR-commented lines
#  - Turn tIP.ratio into the scale factor I want


if __name__ == '__main__':

    # Create all the threads being used
    tGK = tGK.GateKeeper()
    tIP = tIP.ImageParser(camera=('autovideosrc device=/dev/video2 ! appsink'))
    tLS = tLS.Listener()
    tMC = tMC.MotorControl()
    tUI = tUI.UserInterface()

    # Start all the threads
#     tIP.run()
    tGK.start()
    tIP.start()
    tLS.start()
    tMC.start()
    tUI.start()
