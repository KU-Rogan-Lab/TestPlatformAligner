from __future__ import print_function 
import serial
from time import sleep
import numpy as np

class motion:
    """
        Class to control the motion of the chuck at KU
        authors:    nicola.minafra@cern.ch
                    crogan@ku.edu
    """
    def __init__(self, port='COM11', timeout=0.1, emulate=False):
        self.commandIndex = 0
        self.softHome = [0,0,0]
        self.emulate = emulate
        if not self.emulate:
            self.ser = serial.Serial(port=port, baudrate=115200, timeout=timeout)
            self.ser.readline()
        self.motors = ['X', 'Y']
        self.scale = {'X': 1, 'Y' : 1, 'Z': 1}
        self.timeout = timeout

        self.maxLimit = {'X': None, 'Y' : None, 'Z': None}
        self.minLimit = {'X': None, 'Y' : None, 'Z': None}

    def sendCommand(self, command, returnImmediately=True):
        self.commandIndex = (self.commandIndex+1)%10
        command = f'{self.commandIndex}{command}\r\n'
        if not self.emulate:
            self.ser.reset_input_buffer()
            self.ser.write(command.encode())
        if returnImmediately:
            return None
        if self.emulate:
            return "Emulation mode ON"

        while (True):
            self.ser.write(command.encode())
            readStr = self.ser.readline().decode()
            if len(readStr)>1 and int(readStr[0]) == self.commandIndex:
                print(f'Reply: {readStr[3:-2]}')
                return readStr[3:-2]
            else:
                print(f'Waiting for index {self.commandIndex}, received: {readStr}')
            sleep(2*self.timeout)


    def moveTo(self, x=0, y=0, z=0, returnImmediately=True):
        """
			Sends to chick to the wanted position
			Returns the final position
        """
        self.commandIndex = (self.commandIndex+1)%10;
        command = f'g {x + self.softHome[0]} {y + self.softHome[1]}'
        self.sendCommand(command)
        if returnImmediately:   
            return None
        else:
            return self.getPosition()

    def moveFor(self, x=0, y=0, z=0, returnImmediately=True):
        """
                Moves the chuck for the wanted distance (positive or negative)
                Returns the distance traveled
        """
        positionBefore = self.getPosition()
        print(f'positionBefore: {positionBefore}')
        command = f'r {x} {y}'
        print(f'Command: {command}')
        self.sendCommand(command)
        if returnImmediately:
            return None
        else:
            positionNow = self.getPosition()
            print(f'positionNow: {positionNow}')
            return [positionNow[i] - positionBefore[i] for i in range(len(positionBefore))]

    def goHome(self, returnImmediately=True):
        """
                Sends to chuck to home position
        """
        self.moveTo(0,0,0,returnImmediately=returnImmediately)
        if returnImmediately:
            return None
        else:
            return self.getPosition()
    
    def setHome(self):
        """
                Sets current position as coordinate origin (home)
        """
        self.softHome = self.getPosition(absolute=True)
        return
        
    def getPosition(self, absolute=False):
        """
                Returns current position of the chuck for a given motor (if specified) or for all
        """
        self.commandIndex = (self.commandIndex+1)%10
        command = f'{self.commandIndex}p'
        if not self.emulate:
            self.ser.reset_input_buffer()
            self.ser.write(command.encode())
        else:
            print("Emulation mode ON")
            return [-1,-1,-1]

        repetitionCounter = 0
        while (True):
            repetitionCounter += 1
            if repetitionCounter > 5:
                self.ser.reset_input_buffer()
                self.ser.write(command.encode())
                repetitionCounter = 0
            readStr = self.ser.readline().decode()
            try:
                if len(readStr)>1 and int(readStr[0]) == self.commandIndex:
                    xposStr = readStr[readStr.find("X")+2:]
                    xposStr = xposStr[:xposStr.find(" ")]
                    xpos = float(xposStr)
                    yposStr = readStr[readStr.find("Y")+2:]
                    yposStr = yposStr[:yposStr.find(" ")]
                    ypos = float(yposStr)
                    print(f'Abs Position: {xpos} {ypos}\t Relative position: {xpos - self.softHome[0]} {ypos - self.softHome[1]}')
                    if not absolute:
                        xpos -= self.softHome[0]
                        ypos -= self.softHome[1]
                    return [xpos,ypos,0.0]
                else:
                    print(f'Waiting for index {self.commandIndex}, received: {readStr}')
            except:
                print(f'Waiting for index, exception received: {readStr}')
            sleep(2*self.timeout)

     
        
    # def setSafetyLimit(self, motor, min=None, max=None):
    #     motor = motor.upper()
    #     if motor not in self.motors:
    #         self.logger.error(f'Unknown motor: {motor}')
    #         return
    #     if min is not None:
    #         self.minLimit[motor] = min
    #         print(f'min set to {min} for {motor}')
    #     if max is not None:
    #         self.maxLimit[motor] = max
    #         print(f'max set to {max} for {motor}')

if __name__ == '__main__':
    m = motion()
    print(m.getPosition())
    
       
    
        





