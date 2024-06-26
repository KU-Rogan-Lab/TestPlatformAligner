import config as cfg
import motion
from tkinter import messagebox
import time


class GateKeeper(cfg.MyThread):
    def __init__(self):
        """Constructor."""
        self.motors = motion.motion(port='/dev/ttyACM0', emulate=False)
        self.homeSet = False  # Inherited from old code

        cfg.MyThread.__init__(self)

    def stop(self):
        """Wrap up any remaining business before the thread stops."""
        # TODO Save motor position
        print('Stopping the Gatekeeper thread...')

    def run(self):
        # We are assuming that the sensor head is starting at its home position
        # TODO Load motor position
        self.motors.setHome()
        cfg.E_SB_not_obscuring.set()  # Tell tIP the source box is out of the way

        while True:  # Main loop
            time.sleep(0.01)
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

                    elif comm.content == 'ReadMotorPosition':
                        pos = self.motors.getPosition()
                        comm.reply = pos

                    elif comm.content == 'SetMotorHome':
                        self.motors.setHome()
                        pos = self.motors.getPosition()
                        comm.reply = pos
                        self.homeSet = True

                    elif comm.content == 'MotorsToPosition':
                        if self.homeSet:
                            positionX, positionY = comm.content_2
                            self.motors.moveTo(positionX, positionY)
                        else:
                            messagebox.showerror("Home not Set!", "Set home first!")
                        comm.reply = 'Granted'

                    elif comm.content == 'SetFloodLEDs':
                        if not comm.content_2 == cfg.S_floodLED_level:
                            C_LED_control_mbox = cfg.CommObject(c_type='cmd', priority=0, sender='tGK',
                                                                content='ShowMessageBox',
                                                                content_2={'title': 'Hardware Control',
                                                                           'message': 'DEBUG: Manual LED control '
                                                                                      'needed',
                                                                           'detail': f'Please set the floodlight LEDs '
                                                                                     f'to {comm.content_2}. Only '
                                                                                     f'proceed when done.',
                                                                           'type': 'ok'})
                            cfg.Q_cmd_tGK_to_tUI.put(C_LED_control_mbox)
                            # C_LED_control_mbox.E_reply_set.wait()
                            cfg.S_floodLED_level = comm.content_2
                            comm.reply = 'Granted'

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

            if cfg.E_tGK_stopping.is_set():
                self.stop()
                break
