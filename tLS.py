import config as cfg
import serial
import time


class Listener(cfg.MyThread):
    def __init__(self):
        """Constructor."""

        # TODO Put in the correct port here once we know what port we are listening to
        # self.ser = serial.Serial(port='/dev/serial0', timeout=0.1)

        cfg.MyThread.__init__(self)

    def stop(self):
        """Wrap up any remaining business before the thread stops."""
        print('Stopping the Listener thread...')

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

            if cfg.E_tLS_stopping.is_set():
                self.stop()
                break
