import config as cfg
import motion
from tkinter import messagebox


class GateKeeper(cfg.MyThread):
    def __init__(self):
        """Constructor."""
        self.motors = motion.motion(port='/dev/ttyACM1', emulate=False)

        cfg.MyThread.__init__(self)

    def run(self):
        while True:
            self.collect_comms([cfg.Q_hw_tIP_to_tGK, cfg.Q_hw_tMC_to_tGK, cfg.Q_hw_tLS_to_tGK, cfg.Q_hw_tUI_to_tGK])
            for comm in self.comm_list:
                # TODO Make tGK more than a rubber stamp machine
                # TODO Make tGK ask tUI to do all of this, because tkinter says all the GUI needs to be in one thread
                if comm.c_type == 'cmd':  # Handle it like a command
                    comm.reply = 'DEBUG:CommunicationSeen'
                    # PLACEHOLDER: Handle commands here
                    comm.E_reply_set.set()

                elif comm.c_type == 'hw':  # Handle it like a hardware request
                    if comm.content == 'MotorControl':
                        steps, x, y = comm.content_2
                        self.motors.moveFor(x * steps, y * steps, 0)
                        comm.reply = 'Granted'

                    elif comm.content == 'SetFloodLEDs':
                        if comm.content_2 == 'Bright':
                            if not cfg.S_floodLED_level == 'Bright':
                                # messagebox.showinfo(title='Hardware Control',
                                #                     message='Please turn the floodlight LEDs on.\n'
                                #                             'Only close this window when the LEDs have been turned on!')
                                cfg.S_floodLED_level = 'Bright'
                            comm.reply = 'Granted'

                        elif comm.content_2 == 'Dim':
                            if not cfg.S_floodLED_level == 'Dim':
                                # messagebox.showinfo(title='Hardware Control',
                                #                     message='Please turn the floodlight LEDs to dim (partially on).\n'
                                #                             'Only close this window when the LEDs have been set to dim!\n'
                                #                             '(For now, you can just set them to on)')
                                cfg.S_floodLED_level = 'Dim'
                            comm.reply = 'Granted'

                        elif comm.content_2 == 'Off':
                            if not cfg.S_floodLED_level == 'Off':
                                # messagebox.showinfo(title='Hardware Control',
                                #                     message='Please turn the floodlight LEDs off.\n'
                                #                             'Only close this window when the LEDs have been turned off!')
                                cfg.S_floodLED_level = 'Off'
                            comm.reply = 'Granted'
                            pass

                    # TODO Implement laser control of some kind
                    elif comm.content == 'TurnLaserOn':
                        # PLACEHOLDER: Turn the laser on
                        cfg.S_laser_on = True
                        comm.reply = 'Granted'
                        pass

                    elif comm.content == 'TurnLaserOff':
                        # PLACEHOLDER: Turn the laser off
                        cfg.S_laser_on = False
                        comm.reply = 'Granted'
                        pass

                    comm.E_reply_set.set()

                # elif comm.c_type == 'data':  # Handle it like data
                #     pass
