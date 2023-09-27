import main as m
import config as cfg
from tkinter import messagebox


class GateKeeper(cfg.MyThread):
    def __init__(self):
        """Constructor."""
        cfg.MyThread.__init__(self)

    def run(self):
        while True:
            self.collect_comms([cfg.Q_hw_tIP_to_tGK, cfg.Q_hw_tMC_to_tGK, cfg.Q_hw_tLS_to_tGK, cfg.Q_hw_tUI_to_tGK])

            for comm in self.comm_list:
                # todo: Make tGK more than a rubber stamp machine
                # todo: Make tGK ask tUI to do all of this, because tkinter says all the GUI needs to be in one thread
                if comm.c_type == 'cmd':  # Handle it like a command
                    comm.reply = 'DEBUG:CommunicationSeen'
                    # PLACEHOLDER: Handle commands here
                    comm.E_reply_set.set()

                elif comm.c_type == 'hw':  # Handle it like a hardware request
                    if comm.content == 'SetFloodLEDsBright':
                        messagebox.showinfo(title='Hardware Control',
                                            message='Please turn the floodlight LEDs on.\n'
                                                    'Only dismiss this window when the LEDs have been turned on!')
                        cfg.S_floodLED_level = 'Bright'
                        comm.reply = 'Granted'
                        pass

                    elif comm.content == 'SetFloodLEDsDim':
                        messagebox.showinfo(title='Hardware Control',
                                            message='Please turn the floodlight LEDs to dim (partially on).\n'
                                                    'Only dismiss this window when the LEDs have been turned to dim!\n'
                                                    '(For now, you can just set them to on)')
                        cfg.S_floodLED_level = 'Dim'
                        comm.reply = 'Granted'
                        pass

                    elif comm.content == 'SetFloodLEDsOff':
                        messagebox.showinfo(title='Hardware Control',
                                            message='Please turn the floodlight LEDs off.\n'
                                                    'Only dismiss this window when the LEDs have been turned off!')
                        cfg.S_floodLED_level = 'Off'
                        comm.reply = 'Granted'
                        pass

                    # todo: Implement laser control of some kind
                    elif comm.content == 'TurnLaserOn':
                        cfg.S_laser_on = True
                        comm.reply = 'Granted'
                        pass

                    elif comm.content == 'TurnLaserOff':
                        cfg.S_laser_on = False
                        comm.reply = 'Granted'
                        pass

                    comm.E_reply_set.set()

                # elif comm.c_type == 'data':  # Handle it like data
                #     pass
