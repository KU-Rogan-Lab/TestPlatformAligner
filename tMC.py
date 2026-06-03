import config as cfg
import motion
import cv2 as cv
import copy
import time

from tkinter import messagebox


class MotorControl(cfg.MyThread):
    def __init__(self):
        """Constructor."""

        self.avg_laser_pos = (-1, -1)
        self.avg_tl_anchor_pos = (-1, -1)

        self.D_parsed_image_data = None  # The local copy of the parsed image data package

        cfg.MyThread.__init__(self)

    def stop(self):
        """Wrap up any remaining business before the thread stops."""
        print('Stopping the Motor Control thread...')

    def run(self):
        """Do the main behavior of the thread."""
        # Wait for all the required parsed image data to be ready
        cfg.E_PID_image_ready.wait()
        cfg.E_PID_pixel2mm_ready.wait()
        cfg.E_PID_transform_ready.wait()
        cfg.E_PID_tl_anchor_coord_ready.wait()
        cfg.E_PID_laser_coords_ready.wait()
        cfg.E_PID_emitter_coords_ready.wait()
        cfg.E_PID_pixel2mm_ready.wait()

        while True:
            time.sleep(0.01)  # Keeps it from hogging resources TOO badly. Something of a band-aid
            # Collect communications from other threads
            self.collect_comms([cfg.Q_cmd_tUI_to_tMC])

            # Handle all communications
            for comm in self.comm_list:
                if comm.c_type == 'cmd':  # Handle it like a command
                    if comm.content == 'DoAutoAlign':
                        # Calculate the motor move needed to align the box w/ the sensor, then return it in comm.reply
                        # TODO Make this more robustly calculate a 'safe' arm move
                        #  i.e. Stays within motion bounds, doesn't sweep the laser over the sensor, etc.
                        with cfg.L_D_parsed_image_data:
                            self.D_parsed_image_data = copy.deepcopy(cfg.D_parsed_image_data)

                        self.avg_laser_pos = self.D_parsed_image_data.laser_coords
                        self.avg_tl_anchor_pos = self.D_parsed_image_data.tl_anchor_coord

                        # Multiply by -1 for armMoveX because camera and motors have opposite x-axis directions
                        armMoveX = (self.avg_tl_anchor_pos[0] + cfg.K_sensor_x_offset - self.avg_laser_pos[0]) * -1
                        armMoveY = (self.avg_tl_anchor_pos[1] + cfg.K_sensor_y_offset - self.avg_laser_pos[1])

                        # The 1 in index zero is the step size, for compatibility with MotorControl command structure
                        armMove = (1, cfg.K_pixel2mm_constant * armMoveX, cfg.K_pixel2mm_constant * armMoveY)

                        C_autoalign_move = cfg.CommObject(c_type='hw', priority=3, sender='tMC',
                                                          content='MotorControl', content_2=armMove)
                        print(C_autoalign_move)
                        cfg.Q_hw_tMC_to_tGK.put(C_autoalign_move)

                        comm.reply = 'Granted'  # Send the calculated arm move back to the requesting thread

                    else:
                        comm.reply = 'DEBUG:CommunicationSeen'

                    comm.E_reply_set.set()

            # with cfg.L_D_parsed_image_data:
            #     self.avg_laser_pos = cfg.D_PID.laser_coords
            #     self.avg_tl_anchor_pos = cfg.D_PID.tl_anchor_coord
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

            if cfg.E_tMC_stopping.is_set():
                self.stop()
                break
