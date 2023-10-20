import config as cfg
import cv2 as cv
import tkinter as tk
from tkinter import scrolledtext
import copy

import tGK, tIP, tLS, tMC


class UserInterface(cfg.MyThread):
    def __init__(self):
        """Constructor."""

        # THREAD VARIABLES GO HERE
        self.D_parsed_image_data = None  # The local copy of the parsed image data
        self.homeSet = False  # Inherited from old code
        self.sensorsPositions = []  # Inherited from old code
        self.measuredPositions = []  # Inherited from old code

        # GUI ELEMENTS GO BELOW HERE

        self.root = tk.Tk()

    # Set up the positions of the basic frames that make up the GUI
        self.F_video_feed = tk.Frame(self.root, bd=2, relief=tk.GROOVE)
        self.F_video_feed.grid(row=0, column=0, rowspan=4, columnspan=1, padx=5, pady=5, ipadx=1, ipady=1,
                               sticky=tk.W + tk.E)

        self.F_info_readout = tk.Frame(self.root, bd=2, relief=tk.GROOVE)
        self.F_info_readout.grid(row=4, column=0, rowspan=1, columnspan=1, padx=5, pady=5, ipadx=1, ipady=1,
                                 sticky=tk.W + tk.E)

        self.F_title_box = tk.Frame(self.root)
        self.F_title_box.grid(row=0, column=1, rowspan=1, columnspan=1, padx=5, pady=5, ipadx=1, ipady=1,
                              sticky=tk.W + tk.E)

        self.F_stop = tk.Frame(self.root, bd=2, relief=tk.GROOVE)
        self.F_stop.grid(row=1, column=1, rowspan=1, columnspan=1, padx=5, pady=5, ipadx=1, ipady=1,
                         sticky=tk.W + tk.E)

        self.F_GUI_terminal = tk.Frame(self.root)
        self.F_GUI_terminal.grid(row=2, column=1, rowspan=1, columnspan=1, padx=5, pady=5, ipadx=1, ipady=1,
                                 sticky=tk.W + tk.E)

        self.F_motor_controls = tk.Frame(self.root, bd=2, bg='#bbbbbb', relief=tk.GROOVE)
        self.F_motor_controls.grid(row=3, column=1, rowspan=1, columnspan=1, padx=5, pady=5, ipadx=1, ipady=1,
                                   sticky=tk.W + tk.E)

        self.F_controls_3 = tk.Frame(self.root, bd=2, relief=tk.GROOVE)
        self.F_controls_3.grid(row=4, column=1, rowspan=1, columnspan=1, padx=5, pady=5, ipadx=1, ipady=1,
                               sticky=tk.W + tk.E)

    # Create and place the widgets in the F_video_feed frame
        self.v_feed_placeholder = tk.Label(self.F_video_feed, text='VIDEO FEED', bg='#bbbbbb', padx=400, pady=400)
        self.v_feed_placeholder.pack()

    # Create and place the widgets in the F_info_readout frame
        self.info_readout_placeholder = tk.Label(self.F_info_readout, text='INFO READOUTS', bg='#bbbbbb', padx=400, pady=50)
        self.info_readout_placeholder.pack()

    # Create and place the widgets in the F_title_box frame
        self.title_label = tk.Label(self.F_title_box, font=("TkDefaultFont", 20),
                                    text=f'Test Platform Control GUI | Version {cfg.K_version_number}')
        self.title_label.pack()

    # Create and place the widgets in the F_stop frame
        # TODO Make these buttons do something

        self.emergency_stop_button = tk.Button(self.F_stop, height=2, width=30, bg='red', fg='white',
                                               font=("TkDefaultFont", 15), text='EMERGENCY STOP')
        self.emergency_stop_button.grid(row=0, column=0, padx=5, pady=5, ipadx=1, ipady=1)

    # Create and place the widgets in the F_GUI_terminal frame
        self.GUI_terminal = tk.scrolledtext.ScrolledText(self.F_GUI_terminal, bg='#bbbbbb')
        self.GUI_terminal.insert(tk.END, f'TEST PLATFORM CONTROL GUI | Version {cfg.K_version_number}\n'
                                         f'\n'
                                         f'This is a program designed to speed up work on the test platform.\n'
                                         f'Features include:\n'
                                         f'* Manual motor control\n'
                                         f'* Computer vision-based auto-alignment\n'
                                         f'* Data readouts\n'
                                         f'* Sensor safety features\n'
                                         f'\n'
                                         f'Please see README.txt for full instructions.\n'
                                         f'\n'
                                         f'Program written by Aidan Novo, based on code by Dr. Rogan and Dr. '
                                         f'Minafra.\n')
        for i in range(0, 1000):
            self.GUI_terminal.insert(tk.END, f'LINE {i}\n')
        self.GUI_terminal.pack()

    # Create and place the widgets in the F_motor_controls frame (mostly copied from old code)
        # Create and place the entry field that controls step size
        self.stepSizeVar = tk.StringVar(value='1')
        self.stepsEntry = tk.Entry(self.F_motor_controls, textvariable=self.stepSizeVar, width=5)
        self.stepsEntry.grid(row=2, column=2, padx=2, pady=2, sticky=tk.S)

        self.stepsLabel = tk.Label(self.F_motor_controls, text='mm')
        self.stepsLabel.grid(row=2, column=2, padx=2, pady=2, sticky=tk.N)

        # Create and place the entry fields that allow users to move to a specific position
        self.moveToXVar = tk.StringVar(value='0')
        self.moveToXEntry = tk.Entry(self.F_motor_controls, textvariable=self.moveToXVar, width=10)
        self.moveToXEntry.grid(row=3, column=5, padx=15, pady=2, sticky=tk.NE)

        self.moveToYVar = tk.StringVar(value='0')
        self.moveToYEntry = tk.Entry(self.F_motor_controls, textvariable=self.moveToYVar, width=10)
        self.moveToYEntry.grid(row=3, column=6, padx=15, pady=2, sticky=tk.NW)

        # Create and place some miscellaneous buttons
        self.readPositionButton = tk.Button(self.F_motor_controls, text="Read Position", width=25, height=2, command=self.readPosition)
        self.readPositionButton.grid(row=4, column=5, columnspan=2, padx=30, pady=2)

        self.homeButton = tk.Button(self.F_motor_controls, text="Set Home", width=25, height=2, command=self.setHome)
        self.homeButton.grid(row=1, column=5, columnspan=2, padx=30, pady=2)

        self.moveToButton = tk.Button(self.F_motor_controls, text="Move To", width=25, height=2, command=self.moveToPosition)
        self.moveToButton.grid(row=2, column=5, columnspan=2, padx=30, pady=2)

        self.doAutoAlignButton = tk.Button(self.F_motor_controls, text="Do Auto-Alignment", width=25, height=2, command=self.doAutoAlign)
        self.doAutoAlignButton.grid(row=0, column=5, columnspan=2, padx=30, pady=2)

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

    # Create and place the widgets in the F_controls_3 frame
        self.misc_control_placeholder = tk.Label(self.F_controls_3, text='MISC CONTROLS', bg='#bbbbbb', padx=200, pady=50)
        self.misc_control_placeholder.pack()

        cfg.MyThread.__init__(self)

    def moveBtn(self, x, y):
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
                self.GUI_terminal.insert(tk.END, f'Move accepted | X: {x * steps} mm, Y: {y * steps} mm\n')
            else:
                self.GUI_terminal.insert(tk.END, 'Motor move denied by Gatekeeper, please try again\n')

            cfg.L_move_button_command.release()

    def readPosition(self):
        # TODO Implement this
        pass

    def setHome(self):
        # TODO Implement this
        pass

    def moveToPosition(self):
        # TODO Implement this
        pass

    def startAutoAligner(self):
        # TODO Implement this
        pass

    def doAutoAlign(self):
        # TODO Implement this
        pass

    def my_main_loop(self):
        """Perform the main function of the thread."""
        # PLACEHOLDER: Collect communications from in-queues (right now tUI has no in-queues)
        # PLACEHOLDER: Handle commands from other threads
        # PLACEHOLDER: Mark up main frame from self.D_parsed_image_data
        # PLACEHOLDER: Send marked-up frame to display

        with cfg.L_D_parsed_image_data:
            self.D_parsed_image_data = copy.deepcopy(cfg.D_parsed_image_data)

        try:
            self.D_parsed_image_data.image = cv.resize(self.D_parsed_image_data.image, (900, 900),
                                                       interpolation=cv.INTER_AREA)
            cv.imshow('Camera Feed', self.D_parsed_image_data.image)
        except:
            pass

        self.root.update_idletasks()
        self.root.update()

    def run(self):
        """Repeatedly run self.my_main_loop()."""
        # We give the main loop function its own function so that we can run the main loop even while waiting for
        # communication replies.
        while True:
            self.my_main_loop()


if __name__ == '__main__':

    # Create all the threads being used
    tGK = tGK.GateKeeper()
    tIP = tIP.ImageParser(camera=('autovideosrc device=/dev/video2 ! appsink'))
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
