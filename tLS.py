import main as m
import config as cfg


class Listener(cfg.MyThread):
    def __init__(self):
        """Constructor."""

        # Get the queues used to communicate
        global Q_cmd_tUI_to_tLS
        global Q_hw_tLS_to_tGK

        cfg.MyThread.__init__(self)

    def run(self):
        while True:
            # Collect communications from other threads
            pass
#             self.collect_comms([Q_hw_tIP_to_tGK, Q_hw_tMC_to_tGK, Q_hw_tLS_to_tGK, Q_hw_tUI_to_tGK])  # todo FIX THIS
#             self.comm_list.sort(key=lambda a: a.priority)  # Sort the internal request list by priority
#
#             for comm in self.comm_list:
#                 if comm.c_type == 'cmd':  # Handle it like a command
#                     pass