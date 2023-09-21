import main as m
from tkinter import messagebox


class GateKeeper(m.MyThread):
    def __init__(self):
        """Constructor."""
        m.MyThread.__init__(self)

    def run(self):
        while True:
            self.collect_comms([m.Q_hw_tIP_to_tGK, m.Q_hw_tMC_to_tGK, m.Q_hw_tLS_to_tGK, m.Q_hw_tUI_to_tGK])

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
                        comm.reply = 'Granted'
                        pass

                    elif comm.content == 'SetFloodLEDsDim':
                        messagebox.showinfo(title='Hardware Control',
                                            message='Please turn the floodlight LEDs to dim (partially on).\n'
                                                    'Only dismiss this window when the LEDs have been turned to dim!\n'
                                                    '(For now, you can just set them to on)')
                        comm.reply = 'Granted'
                        pass

                    elif comm.content == 'SetFloodLEDsOff':
                        messagebox.showinfo(title='Hardware Control',
                                            message='Please turn the floodlight LEDs off.\n'
                                                    'Only dismiss this window when the LEDs have been turned off!')
                        comm.reply = 'Granted'
                        pass

                    # todo: Implement laser control of some kind
                    elif comm.content == 'TurnLaserOn':
                        comm.reply = 'Granted'
                        pass

                    elif comm.content == 'TurnLaserOff':
                        comm.reply = 'Granted'
                        pass

                    comm.E_reply_set.set()

                # elif comm.c_type == 'data':  # Handle it like data
                #     pass
