import threading
import cv2 as cv
import tkinter as tk
import copy
import time
import os

import config as cfg
import utils as utl
import tGK, tIP, tLS, tMC

from tkinter import scrolledtext
from PIL import Image, ImageTk


class UserInterface(cfg.MyThread):

    # BASIC GUI LAYOUT:
    #
    #                        [_________GUI_WINDOW________]
    # [____CAMERA_FEED____]  | TITLE          |‾‾‾‾‾‾‾‾‾||
    # |                   |  ||‾‾‾‾‾‾‾‾‾‾‾‾‾‾||  INFO   ||
    # |     (imshow)      |  || MOTOR CTRLS  || DISPLAY ||
    # |                   |  ||______________||         ||
    # |                   |  ||‾‾‾‾‾‾‾‾‾‾‾‾‾‾||         ||
    # |                   |  ||  MISC CTRLS  ||         ||
    # |                   |  ||______________||_________||
    # |                   |   ‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾
    # |                   |  [_________TERMINAL__________]
    # |___________________|  |                           |
    #                        |                           |
    #                        |___________________________|
    # f'TEST PLATFORM CONTROL GUI | Version {cfg.K_version_number}\n'
    # f'\n'
    # f'This is a program designed to speed up work on the test platform.\n'
    # f'Features include:\n'
    # f'* Manual motor control\n'
    # f'* Computer vision-based auto-alignment\n'
    # f'* Data readouts\n'
    # f'* Sensor safety features\n'
    # f'\n'
    # f'Please see README.txt for full instructions.\n'
    # f'\n'
    # f'Program written by Aidan Novo, based on code by Dr. Rogan and Dr. '
    # f'Minafra.\n'
    # f'-------------------------------------------------------------------------\n'

    def __init__(self):
        """Constructor."""

    # THREAD VARIABLES GO HERE
        self.terminal_WID = int(os.popen('xdotool getactivewindow').readline().strip('\n'))  # Terminal's xdotool WID
        self.D_PID = None  # The local copy of the parsed image data
        self.homeSet = False  # Inherited from old code
        self.sensorsPositions = []  # Inherited from old code
        self.measuredPositions = []  # Inherited from old code

        self.t_tot_list = []  # List of last 100 loop times (Debug code)
        self.t_update_list = []  # List of last 100 update times (Debug code)

    # GUI ELEMENTS GO BELOW HERE

        self.root = tk.Tk()
        self.root.geometry('+850+40')
        self.root.protocol('WM_DELETE_WINDOW', self.set_stop_events)

    # Set up the positions of the basic frames that make up the GUI
        self.F_title_box = tk.Frame(self.root)
        self.F_title_box.grid(row=0, column=0, padx=5, pady=5, ipadx=1, ipady=1, sticky=tk.W + tk.E)

        self.F_motor_controls = tk.Frame(self.root, bd=2, bg='#bbbbbb', relief=tk.GROOVE)
        self.F_motor_controls.grid(row=1, column=0, padx=5, pady=5, ipadx=1, ipady=1, sticky=tk.W + tk.E)

        self.F_misc_controls = tk.Frame(self.root, bd=2, bg='#bbbbbb', relief=tk.GROOVE)
        self.F_misc_controls.grid(row=2, column=0, padx=5, pady=5, ipadx=1, ipady=1, sticky=tk.W + tk.E)

        self.F_info_readout = tk.Frame(self.root, bd=2, relief=tk.GROOVE)
        self.F_info_readout.grid(row=0, column=1, rowspan=3, padx=5, pady=5, ipadx=1, ipady=1,
                                 sticky=tk.N + tk.S + tk.W + tk.E)

    # Create and place the widgets in the F_info_readout frame
        self.info_readout_placeholder = tk.Label(self.F_info_readout, text='INFO READOUTS', bg='#bbbbbb', padx=20, pady=20)
        self.info_readout_placeholder.grid(row=0, column=0)

        # TODO This label is solely for debug purposes, delete when done
        self.thread_list_label = tk.Label(self.F_info_readout, text='THREAD LIST', bg='#bbbbbb', padx=20, pady=20)
        self.thread_list_label.grid(row=0, column=1)

    # Create and place the widgets in the F_title_box frame
        self.title_label = tk.Label(self.F_title_box, font=("TkDefaultFont", 18),
                                    text=f'Test Platform Control GUI | Version {cfg.K_version_number}')
        self.title_label.pack()

    # Create and place the widgets in the F_misc_controls frame
        self.vis_mask_bool = tk.BooleanVar()
        self.vis_mask_check = tk.Checkbutton(self.F_misc_controls, text='Visualize Mask',
                                             variable=self.vis_mask_bool, onvalue=True, offvalue=False,
                                             command=self.update_checkbutton_vars)
        self.vis_mask_check.grid(row=0, column=0, padx=2, pady=2, sticky=tk.W)

        self.vis_thresh_bool = tk.BooleanVar()
        self.vis_thresh_check = tk.Checkbutton(self.F_misc_controls, text='Visualize Threshold',
                                               variable=self.vis_thresh_bool, onvalue=True, offvalue=False,
                                               command=self.update_checkbutton_vars)
        self.vis_thresh_check.grid(row=1, column=0, padx=2, pady=2, sticky=tk.W)

    # Create and place the widgets in the F_motor_controls frame (mostly copied from old code)
        # Create and place the entry field that controls step size
        self.stepSizeVar = tk.StringVar(value='1')
        self.stepsEntry = tk.Entry(self.F_motor_controls, textvariable=self.stepSizeVar, width=5)
        self.stepsEntry.grid(row=2, column=2, padx=2, pady=2, sticky=tk.S)

        self.stepsLabel = tk.Label(self.F_motor_controls, text='mm')
        self.stepsLabel.grid(row=2, column=2, padx=2, pady=2, sticky=tk.N)

        # Create and place an invisible spacer label to put space between the direction and misc. buttons
        # This is a little bit of a bandaid, but it is quick and works fine
        self.motor_spacer_label = tk.Label(self.F_motor_controls, text='', bg='#bbbbbb')
        self.motor_spacer_label.grid(row=0, column=5, padx=15)

        # Create and place the entry fields that allow users to move to a specific position
        self.moveToXVar = tk.StringVar(value='0')
        self.moveToXEntry = tk.Entry(self.F_motor_controls, textvariable=self.moveToXVar, width=5)
        self.moveToXEntry.grid(row=3, column=6, padx=15, pady=2, sticky=tk.NE)

        self.moveToYVar = tk.StringVar(value='0')
        self.moveToYEntry = tk.Entry(self.F_motor_controls, textvariable=self.moveToYVar, width=5)
        self.moveToYEntry.grid(row=3, column=7, padx=15, pady=2, sticky=tk.NW)

        # Create and place some miscellaneous buttons
        self.readPositionButton = tk.Button(self.F_motor_controls, text="Read Position", width=15, height=2, command=self.readPosition)
        self.readPositionButton.grid(row=4, column=6, columnspan=2, padx=2, pady=2)

        self.homeButton = tk.Button(self.F_motor_controls, text="Set Home", width=15, height=2, command=self.setHome)
        self.homeButton.grid(row=1, column=6, columnspan=2, padx=2, pady=2)

        self.moveToButton = tk.Button(self.F_motor_controls, text="Move To", width=15, height=2, command=self.moveToPosition)
        self.moveToButton.grid(row=2, column=6, columnspan=2, padx=2, pady=2)

        self.doAutoAlignButton = tk.Button(self.F_motor_controls, text="Do Auto-Alignment", width=15, height=2, command=self.doAutoAlign)
        self.doAutoAlignButton.grid(row=0, column=6, columnspan=2, padx=2, pady=2)

        # Create and place the primary manual motor control buttons
        self.upButton = tk.Button(self.F_motor_controls, text="Up", width=3, height=2, command=lambda: self.moveBtn(0, -1))
        self.upButton.grid(row=1, column=2, padx=2, pady=2)
        self.downButton = tk.Button(self.F_motor_controls, text="Down", width=3, height=2, command=lambda: self.moveBtn(0, 1))
        self.downButton.grid(row=3, column=2, padx=2, pady=2)
        self.leftButton = tk.Button(self.F_motor_controls, text="Left", width=3, height=2, command=lambda: self.moveBtn(1, 0))
        self.leftButton.grid(row=2, column=1, padx=2, pady=2)
        self.rightButton = tk.Button(self.F_motor_controls, text="Right", width=3, height=2, command=lambda: self.moveBtn(-1, 0))
        self.rightButton.grid(row=2, column=3, padx=2, pady=2)

        self.upRightButton = tk.Button(self.F_motor_controls, text="U-R", width=3, height=2, command=lambda: self.moveBtn(-1, -1))
        self.upRightButton.grid(row=1, column=3, padx=2, pady=2)
        self.upLeftButton = tk.Button(self.F_motor_controls, text="U-L", width=3, height=2, command=lambda: self.moveBtn(1, -1))
        self.upLeftButton.grid(row=1, column=1, padx=2, pady=2)
        self.downRightButton = tk.Button(self.F_motor_controls, text="D-R", width=3, height=2, command=lambda: self.moveBtn(-1, 1))
        self.downRightButton.grid(row=3, column=3, padx=2, pady=2)
        self.downLeftButton = tk.Button(self.F_motor_controls, text="D-L", width=3, height=2, command=lambda: self.moveBtn(1, 1))
        self.downLeftButton.grid(row=3, column=1, padx=2, pady=2)

        self.upFastButton = tk.Button(self.F_motor_controls, text="10x U", width=3, height=2, command=lambda: self.moveBtn(0, -10))
        self.upFastButton.grid(row=0, column=2, padx=2, pady=2)
        self.downFastButton = tk.Button(self.F_motor_controls, text="10x D", width=3, height=2, command=lambda: self.moveBtn(0, 10))
        self.downFastButton.grid(row=4, column=2, padx=2, pady=2)
        self.leftFastButton = tk.Button(self.F_motor_controls, text="10x L", width=3, height=2, command=lambda: self.moveBtn(10, 0))
        self.leftFastButton.grid(row=2, column=0, padx=2, pady=2)
        self.rightFastButton = tk.Button(self.F_motor_controls, text="10x R", width=3, height=2, command=lambda: self.moveBtn(-10, 0))
        self.rightFastButton.grid(row=2, column=4, padx=2, pady=2)

        self.upRightFastButton = tk.Button(self.F_motor_controls, text="10x\nU-R", width=3, height=2, command=lambda: self.moveBtn(-10, -10))
        self.upRightFastButton.grid(row=0, column=4, padx=2, pady=2)
        self.upLeftFastButton = tk.Button(self.F_motor_controls, text="10x\nU-L", width=3, height=2, command=lambda: self.moveBtn(10, -10))
        self.upLeftFastButton.grid(row=0, column=0, padx=2, pady=2)
        self.downRightFastButton = tk.Button(self.F_motor_controls, text="10x\nD-R", width=3, height=2, command=lambda: self.moveBtn(-10, 10))
        self.downRightFastButton.grid(row=4, column=4, padx=2, pady=2)
        self.downLeftFastButton = tk.Button(self.F_motor_controls, text="10x\nD-L", width=3, height=2, command=lambda: self.moveBtn(10, 10))
        self.downLeftFastButton.grid(row=4, column=0, padx=2, pady=2)

        cfg.MyThread.__init__(self)

    def moveBtn(self, x, y):
        """When a button is pressed, send the corresponding motor control request to tGK."""
        if cfg.L_move_button_command.acquire(timeout=0.1):
            steps = float(self.stepsEntry.get())
            C_move_button_input = cfg.CommObject(c_type='hw', priority=3, sender='tUI',
                                                 content='MotorControl', content_2=(steps, x, y))
            cfg.Q_hw_tUI_to_tGK.put(C_move_button_input)

            while True:
                self.my_main_loop()
                if C_move_button_input.E_reply_set.is_set():
                    break

            if C_move_button_input.reply == 'Granted':
                print(f'Motor move accepted | X: {x * steps} mm, Y: {y * steps} mm')
            else:
                print('Motor move not granted by Gatekeeper, please try again')

            cfg.L_move_button_command.release()

    def readPosition(self):
        """Ask tGK for the current motor position."""
        C_readpos_button_input = cfg.CommObject(c_type='hw', priority=3, sender='tUI', content='ReadMotorPosition')
        cfg.Q_hw_tUI_to_tGK.put(C_readpos_button_input)

        while True:
            self.my_main_loop()
            if C_readpos_button_input.E_reply_set.is_set():
                break

        self.moveToXVar.set(str(C_readpos_button_input.reply[0]))
        self.moveToYVar.set(str(C_readpos_button_input.reply[1]))

    def setHome(self):
        """Ask tGK to set the current motor position as home."""
        C_sethome_button_input = cfg.CommObject(c_type='hw', priority=3, sender='tUI', content='SetMotorHome')
        cfg.Q_hw_tUI_to_tGK.put(C_sethome_button_input)

        while True:
            self.my_main_loop()
            if C_sethome_button_input.E_reply_set.is_set():
                break

        self.moveToXVar.set(str(C_sethome_button_input.reply[0]))
        self.moveToYVar.set(str(C_sethome_button_input.reply[1]))

    def moveToPosition(self):
        """Ask tGK to move the motors to the position in the 'move to' fields"""
        positionX = float(self.moveToXEntry.get())
        positionY = float(self.moveToYEntry.get())
        C_moveto_button_input = cfg.CommObject(c_type='hw', priority=3, sender='tUI',
                                               content='MotorsToPosition', content_2=(positionX, positionY))
        cfg.Q_hw_tUI_to_tGK.put(C_moveto_button_input)

        while True:
            self.my_main_loop()
            if C_moveto_button_input.E_reply_set.is_set():
                break

        if C_moveto_button_input.reply == 'Granted':
            print('Motor move accepted')
        else:
            print('Motor move not granted by Gatekeeper, please try again')
        # TODO Implement this

        pass

    def doAutoAlign(self):
        # TODO Implement this
        pass

    def set_stop_events(self):
        """Set events telling all threads to wrap up their business and stop running."""
        cfg.E_tGK_stopping.set()
        cfg.E_tIP_stopping.set()
        cfg.E_tLS_stopping.set()
        cfg.E_tMC_stopping.set()
        cfg.E_tUI_stopping.set()

    def stop(self):
        """Wrap up any remaining business before the thread stops."""
        print('Stopping the User Interface thread...')
        self.root.destroy()


    def update_checkbutton_vars(self):
        """Update the constants in config.py controlled by checkbuttons on the GUI."""
        cfg.K_visualize_mask = self.vis_mask_bool.get()
        cfg.K_visualize_thresh = self.vis_thresh_bool.get()

    def my_main_loop(self):
        t1 = time.time()
        """Perform the main function of the thread."""
        # PLACEHOLDER: Collect communications from in-queues (right now tUI has no in-queues)
        # PLACEHOLDER: Handle commands from other threads

        # PLACEHOLDER: Check that VNC connection is still good, kill program if connection goes down

        with cfg.L_D_parsed_image_data:
            self.D_PID = copy.deepcopy(cfg.D_parsed_image_data)


        # TODO This is debug code, delete it when you are done
        self.info_readout_placeholder.configure(text=f'tUI {threading.get_native_id()}\n'
                                                     f'tGK {tGK.native_id}\n'
                                                     f'tIP {tIP.native_id}\n'
                                                     f'tLS {tLS.native_id}\n'
                                                     f'tMC {tMC.native_id}\n'
                                                     f'last {threading.enumerate()[-1].native_id}')
        thread_list_text = ''
        for i in range(0, threading.active_count()):
            thread_list_text = thread_list_text + str(threading.enumerate()[i]) + '\n'
        thread_list_text = thread_list_text.strip('\n')
        self.thread_list_label.configure(text=thread_list_text)

        # utl.calc_processing_time('tUI tot', time.time() - t1, self.t_tot_list, 100)
        self.root.update_idletasks()
        self.root.update()

    def run(self):
        """Repeatedly run self.my_main_loop()."""
        # We give the main loop function its own function so that we can run the main loop even while waiting for
        # communication replies.
        while True:
            self.my_main_loop()

            if cfg.E_tUI_stopping.is_set():
                self.stop()
                break


if __name__ == '__main__':

    # Create all the threads being used
    tGK = tGK.GateKeeper()
    tIP = tIP.ImageParser(img_size=cfg.K_image_size)
    tLS = tLS.Listener()
    tMC = tMC.MotorControl()
    tUI = UserInterface()

    # Start all the threads
    # tUI.run()
    # tIP.run()
    tGK.start()
    tIP.start()
    tLS.start()
    tMC.start()
    tUI.run()
