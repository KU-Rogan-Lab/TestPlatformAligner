from threading import Thread, Lock, Event
from queue import Queue


class CommObject:
    # The communication object that is getting passed between threads.
    def __init__(self, c_type, priority, sender, content, reply=None):
        """Constructor."""
        self.c_type = c_type
        self.priority = priority
        self.sender = sender  # A string with the name of the thread that sent this communication
        self.content = content
        self.reply = reply  # Contains the reply from the thread executing or responding to the communication
        self.E_reply_set = Event()  # An event to let the source thread know the reply has been set

    def __repr__(self):
        return f'CommObject(c_type={self.c_type}, priority={self.priority}, content={self.content}, reply={self.reply})'


class ParsedImageData:
    # A class containing the parsed data produced by tIP
    def __init__(self, image=None, transform=None, parsed_qr=None, tl_anchor_coord=None, pixel2mm_constant=None):
        self.image = image
        self.transform = transform
        self.parsed_qr = parsed_qr
        self.tl_anchor_coord = tl_anchor_coord
        self.pixel2mm_constant = pixel2mm_constant


class MyThread(Thread):
    # Using class inheritance to keep code dry.
    # Any methods or __init__() stuff common to all threads goes here.

    def __init__(self):
        """Constructor."""
        # comm_list is the internal list that CommObjects get moved into each loop
        # It is a list so that we can play with it in more ways than a raw queue would allow
        self.comm_list = []

        Thread.__init__(self)

    def collect_comms(self, in_queue_list):
        """Collect communications from a list of input queues and write them into self.comm_list.
        Then, sort comm_list by priority."""

        # This keeps pulling from queues as long as there is something in the queue to pull.
        # This could cause memory/lag issues with extremely large or continuously-filled queues
        for q in in_queue_list:
            if not q.empty():
                self.comm_list.append(q.get())

        self.comm_list.sort(key=lambda element: element.priority)


# These are the command ("cmd") queues, used for threads asking other threads to do things
Q_cmd_tUI_to_tGK = Queue()
Q_cmd_tUI_to_tIP = Queue()
Q_cmd_tUI_to_tMC = Queue()
Q_cmd_tUI_to_tLS = Queue()

# These are the hardware control ("hw") queues, used specifically for threads sending hardware commands to tGK
Q_hw_tUI_to_tGK = Queue()
Q_hw_tIP_to_tGK = Queue()
Q_hw_tMC_to_tGK = Queue()
Q_hw_tLS_to_tGK = Queue()

E_SB_not_obscuring = Event()  # Event used to tell tIP the source box has been moved out of the way
L_floodLED_brightness = Lock()  # Lock used to lock lights to a certain brightness when tIP is taking a picture
L_D_parsed_image_data = Lock()  # Lock used to protect D_parsed_image_data

D_parsed_image_data = ParsedImageData()


