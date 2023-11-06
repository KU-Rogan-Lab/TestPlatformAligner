import config as cfg
import numpy as np
import cv2 as cv
import utils as utl  # A file with various utility functions

from my_pivideostream import PiVideoStream
import time
import os


class ImageParser(cfg.MyThread):
    def __init__(self, img_size=(800, 800), frame_rate=30, autofocus=True, visualize_data=True):
        # img_size = (500,500) is a debugging thing. Should be 1000,1000
        """Constructor."""

        self.img_size = img_size
        self.frame_rate = frame_rate
        self.visualize_data = visualize_data  # todo This should belong to tUI once it is tUI marking up frames

        self.camera_started = True

        self.laser_coords = (-1, -1)
        self.emitter_coords = (-1, -1)

        self.transformation_found = False
        self.laser_dot_found = False
        self.tl_anchor_found = False

        self.transform = np.array([[], [], []])
        self.image = np.array([[0, 0, 0]])
        self.qr_codes_found = []

        self.tft_list = []  # TODO Debug
        self.tt_list = []  # TODO Debug
        self.lt_list = []  # TODO Debug

        # # Defining all the queues used to send data out of the thread
        # self.Q_LaserPositionOut = queue.Queue(maxsize=1)
        # self.Q_TLAnchorPositionOut = queue.Queue(maxsize=1)
        # self.Q_QRDataOut = queue.Queue(maxsize=1)

        self.t_start = 0  # TODO Debug
        self.loop_time = 0  # TODO Debug

        cfg.MyThread.__init__(self)

    def __del__(self):
        cv.destroyAllWindows()

    def stop(self):
        """Wrap up any remaining business before the thread stops."""
        print('Stopping the Image Parser thread...')
        cv.destroyAllWindows()

    def run(self):
        """Run the main behavior of the thread."""

        # This namedWindow stuff needs to be here instead of in init because the cv.namedWindow call must be in the same
        # thread as the cv.imshow call(s)
        cv.namedWindow('Mask', cv.WINDOW_AUTOSIZE + cv.WINDOW_GUI_NORMAL)
        cv.namedWindow('Threshold', cv.WINDOW_AUTOSIZE + cv.WINDOW_GUI_NORMAL)
        cv.namedWindow('Camera Feed', cv.WINDOW_AUTOSIZE + cv.WINDOW_GUI_NORMAL)
        cv.moveWindow('Camera Feed', 3, 40)
        cv.waitKey(1)

        # todo Let the user click "cancel" to terminate the program
        # todo Make tIP ask tUI to show this warning, because tkinter needs all the GUI still to be in one thread
        # Ask the user if it is safe to turn the lights and laser on
        # messagebox.showwarning('Sensor Safety Warning',
        #                        'When you click "OK", the program will turn on the laser and LED floodlights.\n\n'
        #                        'Exposure to this light may damage voltage-biased sensors. Please only proceed once it '
        #                        'is safe to turn the laser and LEDs on.')

        # Ask tGK to turn on the lights and laser
        while True:  # This is in a while True block so that we can try again if our first requests are denied
            # Ask tGK to turn on the lights
            C_startup_lights_on = cfg.CommObject(c_type='hw', priority=1, sender='tIP',
                                                 content='SetFloodLEDs', content_2='Bright')
            cfg.Q_hw_tIP_to_tGK.put(C_startup_lights_on)

            # Ask tGK to turn on the laser
            C_startup_laser_on = cfg.CommObject(c_type='hw', priority=1, sender='tIP', content='TurnLaserOn')
            cfg.Q_hw_tIP_to_tGK.put(C_startup_laser_on)

            # Wait (non-busywaiting, yay!) until tGK has made a reply to both requests
            C_startup_lights_on.E_reply_set.wait()
            C_startup_laser_on.E_reply_set.wait()

            # Only continue once our request to turn on the lights and laser is granted
            if C_startup_lights_on.reply == 'Granted' and \
                    C_startup_lights_on.reply == 'Granted':
                break

        # Wait for tMC to say that the source box is out of the way before we turn on the camera
        cfg.E_SB_not_obscuring.wait()

        vs = PiVideoStream(output_size=self.img_size, framerate=30)
        vs.start()
        self.camera_started = True

        while vs.read() is None:
            print('camera not available... ')
            print(vs.read())
            time.sleep(1)

        print("Press 'q' to close\nPress 't' to correct perspective")  # TODO Remove from final version

        while True:  # Main loop
            self.t_start = time.time()  # TODO This is debug code, remove when done

            # Collect communications from other threads
            self.collect_comms([cfg.Q_cmd_tUI_to_tIP])

            # Handle all communications
            for comm in self.comm_list:
                if comm.c_type == 'cmd':  # Handle it like a command
                    # PLACEHOLDER: Handle 'recalculate transform' command
                    # PLACEHOLDER: Handle 'recalculate anchors' command
                    # PLACEHOLDER: Handle 're-parse QR' command
                    # PLACEHOLDER: Handle other commands
                    comm.reply = 'DEBUG:CommunicationSeen'
                    comm.E_reply_set.set()

            # TODO Remove these old-style commands once they are no longer needed
            # if cv.waitKey(1) & 0xFF == ord('q'):
            #     self.stop()
            #     exit()
            #
            # if cv.waitKey(30) & 0xFF == ord('t'):  # Tells it to re-calculate the perspective transform
            #     self.transformation_found = False

            if not self.camera_started:
                vs = PiVideoStream(output_size=self.img_size, framerate=30)
                vs.start()
                self.camera_started = True
                while vs.read() is None:
                    print('camera not available... ')
                    time.sleep(1)

            # Control the floodlight LED brightness
            with cfg.L_floodLED_brightness:  # Using the lock to keep brightness the same while we take a picture
                if not self.transformation_found:  # Floodlight LEDs bright to better find screws (transform points)
                    C_lights_on_for_screws = cfg.CommObject(c_type='hw', priority=1, sender='tIP',
                                                            content='SetFloodLEDs', content_2='Bright')
                    cfg.Q_hw_tIP_to_tGK.put(C_lights_on_for_screws)
                    pass

                elif self.transformation_found:  # Floodlight LEDs dim for better laser finding
                    C_lights_on_for_screws = cfg.CommObject(c_type='hw', priority=1, sender='tIP',
                                                            content='SetFloodLEDs', content_2='Dim')
                    cfg.Q_hw_tIP_to_tGK.put(C_lights_on_for_screws)
                    pass

                self.image = vs.read()

            # Rotate image to be right-side up
            t1 = time.time()
            # self.image = cv.rotate(self.image, cv.ROTATE_90_COUNTERCLOCKWISE)
            rotate_time = time.time() - t1

            # Try again if the image is all black
            if np.max(self.image) == 0:
                continue

            # Resizing the image to be smaller *may* result in speed increases
            if cfg.K_ratio != 1:
                self.image = cv.resize(self.image, (int(self.img_size[0] * cfg.K_ratio), int(self.img_size[1] * cfg.K_ratio)),
                                       interpolation=cv.INTER_AREA)

            # Calculate the perspective transformation matrix if you do not have it already
            if not self.transformation_found:

                try:
                    # Find colorful screw image coordinates (anchor points)
                    anchor_coords = utl.findAnchorPoints(img=self.image, visualize=cfg.K_visualize_mask,
                                                         low=cfg.K_anchor_lower_color,
                                                         high=cfg.K_anchor_upper_color)
                    # Order the anchor points (TL, TR, BR, BL)
                    untransformed_points = utl.orderAnchorPoints(np.array([anchor_coords[0], anchor_coords[1],
                                                                           anchor_coords[2], anchor_coords[3]]))
                    # Find the perspective transform matrix from the anchor points
                    self.transform = cv.getPerspectiveTransform(untransformed_points, cfg.K_target_points)
                    self.transformation_found = True

                except Exception as error:
                    print('Failed to find the perspective transform')
                    print('Exception:', error)

            if self.transformation_found:  # This needs to stay as an if, not an elif
                t1 = time.time()  # TODO Debug code
                self.image = cv.warpPerspective(self.image, self.transform, self.img_size)
                transform_time = time.time() - t1   # TODO Debug code
                # Only look for QR codes after finding transform to avoid wasting time looking for super warped codes
                # And, only look for the code once to further avoid time loss
                if self.qr_codes_found == []:
                    pass
                    # TODO Let the user control whether the code looks for qrs via checkbox
                    self.qr_codes_found = utl.decode(self.image)

                # Find the pixel coordinates of the top-left anchor in the image
                if not self.tl_anchor_found:  # Only look for the anchor if we haven't found it yet
                    try:
                        anchor_coords = utl.findAnchorPoints(img=self.image, visualize=cfg.K_visualize_mask,
                                                             low=cfg.K_anchor_lower_color,
                                                             high=cfg.K_anchor_upper_color)
                        ordered_anchors = utl.orderAnchorPoints(np.array([anchor_coords[0], anchor_coords[1],
                                                                         anchor_coords[2], anchor_coords[3]]))
                        tl_anchor_pos = ordered_anchors[0]
                        self.tl_anchor_found = True

                    except Exception as error:  # TODO Bare except clauses are bad, fix this
                        print('Failed to find top-left anchor point position')
                        print(error)

            # Try to find the coords of the laser dot in the image
            t1 = time.time()
            self.laser_coords = utl.findLaserPoint(img=self.image, visualize=cfg.K_visualize_thresh,
                                                   threshold=cfg.K_threshold)
            laser_time = time.time() - t1

            # Set self.laser_dot_found to True or False based on if we could find it
            if self.laser_coords == (-1, -1):  # utl.findLaserPoint returning (-1,-1) indicates that it found nothing
                self.laser_dot_found = False
                # PLACEHOLDER: Try wiggling the motor
            elif self.laser_coords != (-1, -1):
                self.laser_dot_found = True

            # Set self.emitter_coords based off of self.laser_coords and a predefined offset
            if self.laser_dot_found:
                self.emitter_coords = (self.laser_coords[0] + cfg.K_emitter_x_offset,
                                       self.laser_coords[1] + cfg.K_emitter_y_offset)

            # Update D_PID with the most recent results, and set events to indicate what data is available
            with cfg.L_D_parsed_image_data:
                cfg.D_parsed_image_data.image = self.image
                cfg.D_parsed_image_data.pixel2mm_constant = cfg.K_pixel2mm_constant
                cfg.E_PID_image_ready.set()
                cfg.E_PID_pixel2mm_ready.set()

                if self.transformation_found:
                    cfg.D_parsed_image_data.transform = self.transform
                    cfg.E_PID_transform_ready.set()
                else:
                    cfg.E_PID_transform_ready.clear()

                if self.tl_anchor_found:
                    cfg.D_parsed_image_data.tl_anchor_coord = tl_anchor_pos  # TODO Make this a self. variable
                    cfg.E_PID_tl_anchor_coord_ready.set()
                else:
                    cfg.E_PID_tl_anchor_coord_ready.clear()

                if self.laser_dot_found:
                    cfg.D_parsed_image_data.laser_coords = self.laser_coords
                    cfg.D_parsed_image_data.emitter_coords = self.emitter_coords
                    cfg.E_PID_laser_coords_ready.set()
                    cfg.E_PID_emitter_coords_ready.set()
                else:
                    cfg.E_PID_laser_coords_ready.clear()
                    cfg.E_PID_emitter_coords_ready.clear()

                if self.qr_codes_found != []:
                    cfg.D_parsed_image_data.parsed_qr = self.qr_codes_found
                    cfg.E_PID_parsed_qr_ready.set()
                else:
                    cfg.E_PID_parsed_qr_ready.clear()

            if self.visualize_data:
                utl.mark_up_image(self.image, self.laser_coords, self.emitter_coords)
            cv.imshow('Camera Feed', self.image)

            # Move the other feeds so they are aligned with the main feed for easy comparison
            feed_x = cv.getWindowImageRect('Camera Feed')[0] - 2  # These are magic numbers
            feed_y = cv.getWindowImageRect('Camera Feed')[1] - 30  # These are magic numbers
            cv.moveWindow('Mask', feed_x, feed_y)
            cv.moveWindow('Threshold', feed_x, feed_y)

            cv.waitKey(1)

            # Logging some basic info about how much time each step takes
            # self.loop_time = time.time() - self.t_start
            # utl.calc_processing_time('tIP tot', self.loop_time, self.tt_list, 100)

            # try:
            #     utl.calc_processing_time('tIP trs', transform_time, self.tft_list, 100)
            # except:
            #     pass
            # print(f' las {round(laser_time, 5)}\t{round(laser_time / self.loop_time, 2)}')
            # print(f' rot {round(rotate_time, 5)}\t{round(rotate_time / self.loop_time, 2)}')

            if cfg.E_tIP_stopping.is_set():
                self.stop()
                break
