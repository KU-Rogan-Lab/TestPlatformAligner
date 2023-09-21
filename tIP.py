import main as m
import config as cfg
import numpy as np
import cv2 as cv
from imutils.video import VideoStream
import time
import os
import utils as utl  # A file with various utility functions


class ImageParser(cfg.MyThread):
    def __init__(self, camera=0, img_size=(1000, 1000), frame_rate=30, visualize_data=True):
        """Constructor."""

        self.camera = camera
        self.img_size = img_size
        self.frame_rate = frame_rate
        self.visualize_data = visualize_data

        # The target points for the image transform
        # These represent the "true" dimensions of the anchors in pixels.
        # They MUST be in (TL, TR, BR, BL) order,
        # and they MUST keep to the same aspect ratio as self.true_anchor_dimensions
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
        # Given as [mm distance] * self.pixel2mm_constant ** -1
        self.sensor_x_offset = int(15 * self.pixel2mm_constant ** -1)
        self.sensor_y_offset = int(25 * self.pixel2mm_constant ** -1)

        self.threshold = 245  # The threshold used when thresholding the image to look for the laser dot

        # These color boundaries will need to be fine-tuned for the specific anchors and lighting being used
        self.anchor_lower_color = np.array([60, 40, 40])  # Lower bound of the color of the anchors (HSV format)
        self.anchor_upper_color = np.array([90, 255, 255])  # Upper bound of the color of the anchors (HSV format)

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

        cfg.MyThread.__init__(self)

    def __del__(self):
        cv.destroyAllWindows()

    def stop(self):
        """Wrap up the thread's business and stop."""
        cv.destroyAllWindows()

    def run(self):
        """Run the main behavior of the thread."""

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
            C_startup_lights_on = cfg.CommObject(c_type='hw', priority=1, sender='tIP', content='SetFloodLEDsBright')
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

        print("Press 'q' to close\nPress 't' to correct perspective")  # todo Remove from final version

        while True:  # Main loop
            # Collect communications from other threads
            self.collect_comms([cfg.Q_cmd_tUI_to_tIP])
            self.comm_list.sort(key=lambda a: a.priority)  # Sort the internal request list by priority

            # Handle all communications
            for comm in self.comm_list:
                if comm.c_type == 'cmd':  # Handle it like a command
                    # PLACEHOLDER: Handle 'recalculate transform' command
                    # PLACEHOLDER: Handle 'recalculate anchors' command
                    # PLACEHOLDER: Handle 're-parse QR' command
                    # PLACEHOLDER: Handle other commands
                    comm.reply = 'DEBUG:CommunicationSeen'
                    comm.E_reply_set.set()

            # TODO: Remove these old-style commands once they are no longer needed
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

            # Control the floodlight LED brightness
            with cfg.L_floodLED_brightness:  # Using the lock to keep brightness the same while we take a picture
                if not self.transformation_found:  # Floodlight LEDs bright to better find screws (transform points)
                    C_lights_on_for_screws = cfg.CommObject(c_type='hw', priority=1, sender='tIP',
                                                          content='SetFloodLEDsBright')
                    cfg.Q_hw_tIP_to_tGK.put(C_lights_on_for_screws)
                    pass

                elif self.transformation_found:  # Floodlight LEDs dim for better laser finding
                    C_lights_on_for_screws = cfg.CommObject(c_type='hw', priority=1, sender='tIP',
                                                          content='SetFloodLEDsBright')
                    cfg.Q_hw_tIP_to_tGK.put(C_lights_on_for_screws)
                    pass

                self.image = vs.read()

            # Rotate image to be right-side up
            self.image = cv.rotate(self.image, cv.ROTATE_90_COUNTERCLOCKWISE)

            # Try again if the image is all black
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
                if self.qr_codes_found == []:
                    self.qr_codes_found = utl.decode(self.image)

                # Find the pixel coordinates of the top-left anchor in the image
                if not self.Q_TLAnchorPositionOut.full():  # OkR Sort of a slapped-together framerate fix
                    try:
                        anchor_coords = utl.findAnchorPoints(img=self.image, visualize=True,
                                                             low=self.anchor_lower_color,
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
            if laserCoords == (-1, -1):  # utl.findLaserPoint returning (-1,-1) indicates that it found nothing
                self.laser_dot_found = False
                # PLACEHOLDER: Try wiggling the motor
            elif laserCoords != (-1, -1):
                self.laser_dot_found = True

            # Set emitter_coords based off of laserCoords and a predefined offset
            if self.laser_dot_found:
                if not self.Q_LaserPositionOut.full():
                    self.Q_LaserPositionOut.put(laserCoords)

                emitter_coords = (laserCoords[0] + self.emitter_x_offset, laserCoords[1] + self.emitter_y_offset)

            # Update D_parsed_image_data with the most recent results
            with cfg.L_D_parsed_image_data:
                cfg.D_parsed_image_data.image = self.image
                cfg.D_parsed_image_data.pixel2mm_constant = self.pixel2mm_constant

                if self.transformation_found:
                    cfg.D_parsed_image_data.transform = self.transform

                if self.tl_anchor_found:
                    cfg.D_parsed_image_data.tl_anchor_coord = tlAnchorPos  # todo make this a self. variable

                if self.qr_codes_found != []:  # This is kind of the odd one out
                    cfg.D_parsed_image_data.parsed_qr = self.qr_codes_found

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

            # TODO: This above bit works, but because the anchor points never get updated, it will always just
            # output [350,650,1] for a. And really, the code is not written to ever update the anchor points.
            # Talk to Jack/maybe other people at the lab meeting to figure out if we can just assume the anchor
            # points will not be moving

            print('-----')
            cv.imshow('Camera Feed', self.image)