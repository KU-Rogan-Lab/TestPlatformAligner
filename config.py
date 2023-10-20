# This is a file that holds all variables and resources that need to be shared between threads.
# This is mainly the queues and the "notice board" - events, locks, flags, etc.
# But, this file also contains the shared classes, which is maybe less organized, but it doesn't really matter

# (All this stuff cannot go in main.py, because doing so causes an import loop)

from threading import Thread, Lock, Event
from queue import Queue
import numpy as np


class CommObject:
    # The communication object that is getting passed between threads.
    def __init__(self, c_type, priority, sender, content, content_2=None, reply=None):
        """Constructor."""
        self.c_type = c_type
        self.priority = priority
        self.sender = sender  # A string with the name of the thread that sent this communication
        self.content = content  # The basic content of the request
        self.content_2 = content_2  # Contains more detailed or specific info, for complex requests
        self.reply = reply  # Contains the reply from the thread executing or responding to the communication
        self.E_reply_set = Event()  # An event to let the source thread know the reply has been set

    def __repr__(self):
        return (f'CommObject(c_type={self.c_type}, priority={self.priority}, content={self.content},'
                f'content_2={self.content_2}, reply={self.reply})')


class ParsedImageData:
    # A class containing the parsed data produced by tIP
    def __init__(self, image=None, transform=None, parsed_qr=None, tl_anchor_coord=None, pixel2mm_constant=None,
                 laser_coords=None, emitter_coords=None):
        self.image = image  # The image
        self.transform = transform  # The matrix to perspective transform the raw camera input
        self.parsed_qr = parsed_qr  # The contents of the qr codes parsed
        self.tl_anchor_coord = tl_anchor_coord  # The coordinates of the top-left anchor point
        self.pixel2mm_constant = pixel2mm_constant  # The constant to switch between pixels and mm
        self.laser_coords = laser_coords  # The coordinates of the laser dot
        self.emitter_coords = emitter_coords  # The calculated coordinates of the emitter slit

    def __str__(self):
        return f'Parsed Image Data:\n' \
               f'image = self.image (large array)\n' \
               f'transform = {self.transform}\n' \
               f'parsed_qr = {self.parsed_qr}\n' \
               f'tl_anchor_coord = {self.tl_anchor_coord}\n' \
               f'pixel2mm_constant = {self.pixel2mm_constant}\n' \
               f'laser_coords = {self.laser_coords}\n' \
               f'emitter_coords = {self.emitter_coords}'


class MyThread(Thread):
    # Using class inheritance to keep code dry.
    # Any methods or __init__() stuff common to all threads goes here.

    def __init__(self):
        """Constructor."""
        # comm_list is the internal list that CommObjects get moved into each loop
        # It is a list so that we can play with it in more ways than a raw queue would allow
        self.comm_list = []

        Thread.__init__(self)

    def collect_comms(self, in_queue_list):
        """Collect communications from a list of input queues and write them into self.comm_list.
        Then, sort comm_list by priority."""

        # Wipe the old comm_list before putting new comms into it
        self.comm_list = []

        # This keeps pulling from queues as long as there is something in the queue to pull.
        # This could cause memory/lag issues with extremely large or continuously-filled queues
        for q in in_queue_list:
            if not q.empty():
                self.comm_list.append(q.get())
                print(self.comm_list)

        self.comm_list.sort(key=lambda element: element.priority)


# These are the command ("cmd") queues, used for threads asking other threads to do things
Q_cmd_tUI_to_tGK = Queue()
Q_cmd_tUI_to_tIP = Queue()
Q_cmd_tUI_to_tMC = Queue()
Q_cmd_tUI_to_tLS = Queue()

# These are the hardware control ("hw") queues, used specifically for threads sending hardware commands to tGK
Q_hw_tUI_to_tGK = Queue()
Q_hw_tIP_to_tGK = Queue()
Q_hw_tMC_to_tGK = Queue()
Q_hw_tLS_to_tGK = Queue()

E_SB_not_obscuring = Event()  # Event used to tell tIP the source box has been moved out of the way

# These events indicate whether or not the current D_parsed_image_data package includes the corresponding data
E_PID_image_ready = Event()
E_PID_pixel2mm_ready = Event()
E_PID_transform_ready = Event()
E_PID_tl_anchor_coord_ready = Event()
E_PID_laser_coords_ready = Event()
E_PID_emitter_coords_ready = Event()
E_PID_parsed_qr_ready = Event()

D_parsed_image_data = ParsedImageData()  # The shared data object with the results from tIP's math

S_floodLED_level = ''  # Can be 'Bright', 'Dim', or 'Off'
S_laser_on = False  # False = laser is off, True = laser is on
S_microscopeLED_on = False  # False = microscope LEDs are off, True = microscope LEDs are on

# Locks used to protect shared resources, uses nomenclature "L_[name of thing protected]"
L_floodLED_brightness = Lock()  # Lock used to lock lights to a certain brightness when tIP is taking a picture
L_move_button_command = Lock()  # Lock used to prevent new move button commands from starting until the current is done
L_D_parsed_image_data = Lock()  # Lock used to protect D_parsed_image_data

# ----------------------------------- CONSTANTS GO BELOW HERE -----------------------------------
K_version_number = '0.1.0'

# The target points for the image transform, which represent the "true" dimensions of the anchors in pixels.
# They MUST be in (TL, TR, BR, BL) order and they MUST keep to the same aspect ratio as K_true_anchor_dimensions
K_target_points = np.float32([[400, 400], [600, 400], [600, 600], [400, 600]])

K_true_anchor_dimensions = (98.8, 98.8)  # The true dimensions of the anchor points in mm

# A calculated constant to convert between pixels and mm in the post-transform image
K_pixel2mm_constant = K_true_anchor_dimensions[0] / (K_target_points[1][0] - K_target_points[0][0])

# The x and y pixel offsets to get from the position of the laser dot to the position of the emitter slit
# Given as [mm distance] * K_pixel2mm_constant**-1
K_emitter_x_offset = int(-98 * K_pixel2mm_constant ** -1)
K_emitter_y_offset = int(-18.5 * K_pixel2mm_constant ** -1)

# The x and y pixel offsets to get from the position of some anchor point (which one is defined below) to
# the position of the sensor.
# Given as [mm distance] * K_pixel2mm_constant ** -1
K_sensor_x_offset = int(15 * K_pixel2mm_constant ** -1)
K_sensor_y_offset = int(25 * K_pixel2mm_constant ** -1)

K_threshold = 245  # The threshold used when thresholding the image to look for the laser dot

# These color boundaries will need to be fine-tuned for the specific anchors and lighting being used
K_anchor_lower_color = np.array([60, 40, 40])  # Lower bound of the color of the anchors (HSV format)
K_anchor_upper_color = np.array([90, 255, 255])  # Upper bound of the color of the anchors (HSV format)

K_ratio = 1  # Honestly I am not totally sure what this one does. I inherited this variable from past code

