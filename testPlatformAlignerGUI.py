from tkinter import *
from tkinter import messagebox
import motion
import numpy as np
import TPA_threads as tPA
from threading import Event


class Window(Frame):

    def __init__(self, master=None, port='/dev/ttyACM0', emulate=False):
        Frame.__init__(self, master)        
        self.master = master

        self.motors = motion.motion(port=port, emulate=emulate)
        self.homeSet = False

        self.stepSize = 1
        self.sensorsPositions = []
        self.measuredPositions = []

        self.stepSizeVar=StringVar() 
        self.stepSizeVar.set(str(self.stepSize))
        stepsLabel = Label(self, text="mm")
        self.stepsEntry = Entry(self, textvariable=self.stepSizeVar, width=6)

        self.moveToXVar=StringVar() 
        self.moveToXVar.set("0")
        self.moveToXEntry = Entry(self, textvariable=self.moveToXVar, width=10)
        self.moveToYVar=StringVar() 
        self.moveToYVar.set("0")
        self.moveToYEntry = Entry(self, textvariable=self.moveToYVar, width=10)

        self.savedPointsVar=StringVar() 
        self.savedPointsVar.set("0")
        self.savedPointsLabel = Label(self, textvariable=self.savedPointsVar, width=10)

        menu = Menu(self.master)
        self.master.config(menu=menu)

        fileMenu = Menu(menu)
        fileMenu.add_command(label="Exit", command=self.exitProgram)
        menu.add_cascade(label="File", menu=fileMenu)

        # widget can take all window
        self.pack(fill=BOTH, expand=1)

        readPositionButton  = Button(self, text="Read Position", width=33, height=2, command=self.readPosition)
        self.homeButton = Button(self, text="Set Home", width=33, height=2, command=self.setHome)  
        self.moveToButton = Button(self, text="Move To", width=33, height=2, command=self.moveToPosition)
        
        self.startAlignerButton = Button(self, text="Start Auto-Aligner", width=14, height=2, command=self.startAutoAligner)
        self.doAutoAlignButton = Button(self, text="Do Auto-Alignment", width=14, height=2, command=self.doAutoAlign)

        upButton = Button(self, text="Up", width=4, height=2, command=lambda: self.moveBtn(0,-1))
        upRightButton = Button(self, text="U-R", width=4, height=2, command=lambda: self.moveBtn(-1,-1))
        upLeftButton = Button(self, text="U-L", width=4, height=2, command=lambda: self.moveBtn(1,-1))
        downButton = Button(self, text="Down", width=4, height=2, command=lambda: self.moveBtn(0,1))
        downRightButton = Button(self, text="D-R", width=4, height=2, command=lambda: self.moveBtn(-1,1))
        downLeftButton = Button(self, text="D-L", width=4, height=2, command=lambda: self.moveBtn(1,1))
        leftButton = Button(self, text="Left", width=4, height=2, command=lambda: self.moveBtn(1,0))
        rightButton = Button(self, text="Right", width=4, height=2, command=lambda: self.moveBtn(-1,0))

        upFastButton = Button(self, text="10x U", width=4, height=2, command=lambda: self.moveBtn(0,-10))
        upRightFastButton = Button(self, text="10x U-R", width=4, height=2, command=lambda: self.moveBtn(-10,-10))
        upLeftFastButton = Button(self, text="10x U-L", width=4, height=2, command=lambda: self.moveBtn(10,-10))
        downFastButton = Button(self, text="10x D", width=4, height=2, command=lambda: self.moveBtn(0,10))
        downRightFastButton = Button(self, text="10x D-R", width=4, height=2, command=lambda: self.moveBtn(-10,10))
        downLeftFastButton = Button(self, text="10x D-L", width=4, height=2, command=lambda: self.moveBtn(10,10))
        leftFastButton = Button(self, text="10x L", width=4, height=2, command=lambda: self.moveBtn(10,0))
        rightFastButton = Button(self, text="10x R", width=4, height=2, command=lambda: self.moveBtn(-10,0))

        # place buttons
        stepsLabel.place(x=150,y=110)
        self.stepsEntry.place(x=150,y=130)
        self.homeButton.place(x=20,y=450)

        self.moveToXEntry.place(x=85 ,y=350)
        self.moveToYEntry.place(x=185 ,y=350)
        self.moveToButton.place(x=20,y=300)
        readPositionButton.place(x=20,y=400)
        
        self.startAlignerButton.place(x=20,y=500)
        self.doAutoAlignButton.place(x=190,y=500)

        upButton.place(x=150, y=60)
        upRightButton.place(x=215, y=60)
        upLeftButton.place(x=85, y=60)
        downButton.place(x=150, y=160)
        downRightButton.place(x=215, y=160)
        downLeftButton.place(x=85, y=160)
        leftButton.place(x=85, y=110)
        rightButton.place(x=215, y=110)
        
        upFastButton.place(x=150, y=10)
        upRightFastButton.place(x=280, y=10)
        upLeftFastButton.place(x=20, y=10)
        downFastButton.place(x=150, y=210)
        downRightFastButton.place(x=280, y=210)
        downLeftFastButton.place(x=20, y=210)
        leftFastButton.place(x=20, y=110)
        rightFastButton.place(x=280, y=110)
        
        #self.homeButton['state'] = ACTIVE

    def exitProgram(self):
        exit()

    def moveToPosition(self):
        if self.homeSet:
            positionX = float(self.moveToXEntry.get())
            positionY = float(self.moveToYEntry.get())
            self.motors.moveTo(positionX, positionY)
        else:
            messagebox.showerror("Home not Set!", "Set home first!")

    def setHome(self):
        self.motors.setHome()
        self.readPosition()
        self.homeSet = True

    def readPosition(self):
        pos = self.motors.getPosition()
        self.moveToXVar.set(str(pos[0]))
        self.moveToYVar.set(str(pos[1]))

    def moveBtn(self, x, y):
        steps = float(self.stepsEntry.get())
        self.motors.moveFor(x*steps,y*steps,0)
        print(f'{x*steps}, {y*steps}')
        
    def startAutoAligner(self):
        tPA.tIP = tPA.ImageParser(camera=('autovideosrc device=/dev/video2 ! appsink'))
        tPA.tMC = tPA.MotorControl()
        tPA.tGK = tPA.GateKeeper()
    
        # Create all the events/conditions/locks used to communicate between threads
        tPA.E_SB_not_obscuring = Event() # Event used to tell tIP the source box has been moved out of the way
        tPA.E_tIP_data_flowing = Event() # Event used to tell tMC that tIP is now producing data
        tPA.E_StartAutoAlign = Event() # OkR Demo Event, used to prompt the auto align confirmation window
        
        tPA.tIP.start()
        tPA.tMC.start()
        
    def doAutoAlign(self):
        tPA.E_StartAutoAlign.set()
        

root = Tk()
app = Window(root)
root.wm_title("Spectrometer Platform")
root.geometry("370x600")
root.mainloop()
