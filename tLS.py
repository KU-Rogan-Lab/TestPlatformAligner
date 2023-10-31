import config as cfg
import serial
import time


class Listener(cfg.MyThread):
    def __init__(self):
        """Constructor."""

        # TODO Put in the correct port here once we know what port we are listening to
        # self.ser = serial.Serial(port='PLACEHOLDER', timeout=0.1)

        cfg.MyThread.__init__(self)

    def run(self):
        while True:
            time.sleep(0.01)
            # Collect communications from other threads
            self.collect_comms([cfg.Q_cmd_tUI_to_tLS])
            for comm in self.comm_list:
                if comm.c_type == 'cmd':  # Handle it like a command
                    # TODO Implement commands
                    comm.reply = 'DEBUG:CommunicationSeen'

                comm.E_reply_set.set()

            # TODO Consider adjusting the ratio of communications handled per cycle to serial reads per cycle

            # DEBUG
            # print(self.ser.readline())
