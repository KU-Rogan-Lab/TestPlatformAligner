import main as m
import config as cfg
import motion
import cv2 as cv
from tkinter import messagebox


class MotorControl(cfg.MyThread):
    def __init__(self):
        """Constructor."""

        self.motors = motion.motion(port='/dev/ttyACM0', emulate=False)

        self.avg_laser_pos = (-1, -1)
        self.avg_tl_anchor_pos = (-1, -1)

        cfg.MyThread.__init__(self)

    def stop(self):
        self.motors.moveTo(0, 0)
        # todo Instead of this, make it save the motor position on shutdown
        cv.destroyAllWindows()

    def run(self):
        # We are assuming that the sensor head is already at its home position, which is off in the +x +y corner
        self.motors.setHome()
        cfg.E_SB_not_obscuring.set()  # Tell tIP the source box is out of the way

        #         E_tIP_data_flowing.wait()  # Wait until tIP is producing its data
        #         # todo this event no longer exists, fix this

        # Main loop, all very OkR
        while True:
            # Collect communications from other threads
            pass
            #             self.collect_comms([Q_hw_tIP_to_tGK, Q_hw_tMC_to_tGK, Q_hw_tLS_to_tGK, Q_hw_tUI_to_tGK])  # todo FIX THIS
            #
            #             for comm in self.comm_list:
            #                 if comm.c_type == 'cmd':  # Handle it like a command
            #                     pass

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