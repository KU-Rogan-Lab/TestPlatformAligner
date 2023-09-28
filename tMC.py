import config as cfg
import motion
import cv2 as cv
import copy

from tkinter import messagebox


class MotorControl(cfg.MyThread):
    def __init__(self):
        """Constructor."""

        # todo tMC should not get motor control, move this to tGK
        self.motors = motion.motion(port='/dev/ttyACM0', emulate=False)

        self.avg_laser_pos = (-1, -1)
        self.avg_tl_anchor_pos = (-1, -1)

        self.D_parsed_image_data = None  # The local copy of the parsed image data package

        cfg.MyThread.__init__(self)

    def stop(self):
        """Handle stopping the thread and wrapping up its business."""

        # todo tGK gets motor control, not tMC
        self.motors.moveTo(0, 0)
        # todo Instead of this, make it save the motor position on shutdown
        cv.destroyAllWindows()

    def run(self):
        """Do the main behavior of the thread."""

        # todo Once tGK has full motor control, it should be doing all of this home-setting stuff
        # We are assuming that the sensor head is starting at its home position
        self.motors.setHome()
        cfg.E_SB_not_obscuring.set()  # Tell tIP the source box is out of the way

        # Wait for all the required parsed image data to be ready
        cfg.E_PID_image_ready.wait()
        cfg.E_PID_pixel2mm_ready.wait()
        cfg.E_PID_transform_ready.wait()
        cfg.E_PID_tl_anchor_coord_ready.wait()
        cfg.E_PID_laser_coords_ready.wait()
        cfg.E_PID_emitter_coords_ready.wait()
        cfg.E_PID_pixel2mm_ready.wait()

        while True:
            # Collect communications from other threads
            self.collect_comms([cfg.Q_cmd_tUI_to_tMC])

            # Handle all communications
            for comm in self.comm_list:
                if comm.c_type == 'cmd':  # Handle it like a command

                    if comm.content == 'CalculateAlignMove':
                        # Calculate the motor move needed to align the box w/ the sensor, then return it in comm.reply
                        # todo Make this more robustly calculate a 'safe' arm move
                        #  i.e. Stays within motion bounds, doesn't sweep the laser over the sensor, etc.
                        with cfg.L_D_parsed_image_data:
                            self.D_parsed_image_data = copy.deepcopy(cfg.D_parsed_image_data)

                        self.avg_laser_pos = self.D_parsed_image_data.laser_coords
                        self.avg_tl_anchor_pos = self.D_parsed_image_data.tl_anchor_coord

                        # Multiply by -1 for armMoveX because camera and motors have opposite x-axis directions
                        armMoveX = (self.avg_tl_anchor_pos[0] + 102 - self.avg_laser_pos[0]) * -1
                        armMoveY = (self.avg_tl_anchor_pos[1] + 102 - self.avg_laser_pos[1])

                        armMove = (cfg.K_pixel2mm_constant * armMoveX, cfg.K_pixel2mm_constant * armMoveY)

                        comm.reply = armMove  # Send the calculated arm move back to the requesting thread

                    else:
                        comm.reply = 'DEBUG:CommunicationSeen'

                    comm.E_reply_set.set()

            # with cfg.L_D_parsed_image_data:
            #     self.avg_laser_pos = cfg.D_parsed_image_data.laser_coords
            #     self.avg_tl_anchor_pos = cfg.D_parsed_image_data.tl_anchor_coord
            #
            # E_StartAutoAlign.wait()
            #
            # goodPositions = messagebox.askyesno('Confirm Positions & Arm Move',
            #                                     f'Are the following positions correct?\n'
            #                                     f'Laser Dot: {self.avg_laser_pos}\n'
            #                                     f'TL Anchor Position: {self.avg_tl_anchor_pos}')
            #
            # if not goodPositions:
            #     E_StartAutoAlign.clear()
            #     continue
            #
            # elif goodPositions:
            #     E_StartAutoAlign.clear()
            #     # Multiply by -1 for armMoveX because camera and motors have opposite x-axis directions
            #     armMoveX = (self.avg_tl_anchor_pos[0] + 102 - self.avg_laser_pos[0]) * -1
            #     armMoveY = (self.avg_tl_anchor_pos[1] + 102 - self.avg_laser_pos[1])
            #
            #     armMove = (tIP.pixel2mm_constant * armMoveX, tIP.pixel2mm_constant * armMoveY)
            #
            #     self.motors.moveFor(armMove[0], armMove[1], 0)