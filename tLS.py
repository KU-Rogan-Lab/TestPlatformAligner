import config as cfg


class Listener(cfg.MyThread):
    def __init__(self):
        """Constructor."""

        cfg.MyThread.__init__(self)

    def run(self):
        while True:
            # Collect communications from other threads
            pass
#             self.collect_comms([Q_hw_tIP_to_tGK, Q_hw_tMC_to_tGK, Q_hw_tLS_to_tGK, Q_hw_tUI_to_tGK])
#             for comm in self.comm_list:
#                 if comm.c_type == 'cmd':  # Handle it like a command
#                     pass