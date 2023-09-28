import config as cfg


class UserInterface(cfg.MyThread):
    def __init__(self):
        """Constructor."""
        # Get the queues used for communication
        # global Q_cmd_tUI_to_tLS
        # global Q_cmd_tUI_to_tGK
        # global Q_cmd_tUI_to_tIP
        # global Q_cmd_tUI_to_tMC
        # global Q_hw_tUI_to_tGK

        # PLACEHOLDER: Create and place tkinter GUI elements

        cfg.MyThread.__init__(self)

    def run(self):
        """Execute the main function of the loop."""
        while True:
            pass
            # PLACEHOLDER: Collect communications from in-queues (right now tUI has no in-queues)
            # PLACEHOLDER: Handle commands from other threads
            # PLACEHOLDER: Make local deepcopy of D_parsed_image_data (using a Lock)
            # PLACEHOLDER: Mark up main frame from self.D_parsed_image_data
            # PLACEHOLDER: Send marked-up frame to display

            # PLACEHOLDER: tk.update_idletasks()
            # PLACEHOLDER: tk.update()