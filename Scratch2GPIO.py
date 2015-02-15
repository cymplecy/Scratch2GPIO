# Copyright Simon Walters 2015 from original code by Alan Yorinks (s2a_fm project)
# All code is provided under GPL2 and any copies must also be distributed under GPL2 or a later version
#
# Version is 0.0.1 alpha
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import urlparse
from string import split
import socket
import time as time
import threading

scratch_socket = None
scratch_socket2 = None
conn = None
addr = None

class MyHandler(BaseHTTPRequestHandler):


    def do_GET(self):
        # skip over the / in the command
        cmd = self.path[1:]
        # create a list containing the command and all of its parameters
        cmd_list = split(cmd, '/')

        # get the command handler method for the command and call the handler
        # cmd_list[0] contains the command. look up the command method

        s = self.command_handler(cmd_list)
        s = "fred"

        # if pin was not enabled for reporter block, a "NoneType" can be returned by the command_handler
        if (s is None) or (len(s) == 0):

            err_statement = ("do_GET: Do you have all active pins enabled? " + str(cmd_list))
            #logging.info(err_statement)
            print err_statement
            return
        else:
            self.send_resp(s)

    # we can't use the standard send_response since we don't conform to its
    # standards, so we craft our own response handler here
    def send_resp(self, response):
        """
        This method sends Scratch an HTTP response to an HTTP GET command.
        """

        crlf = "\r\n"
        # http_response = str(response + crlf)
        http_response = "HTTP/1.1 200 OK" + crlf
        http_response += "Content-Type: text/html; charset=ISO-8859-1" + crlf
        http_response += "Content-Length" + str(len(response)) + crlf
        http_response += "Access-Control-Allow-Origin: *" + crlf
        http_response += crlf
        #add the response to the nonsense above
        if response != 'okay':
            http_response += str(response + crlf)
        # send it out the door to Scratch
        self.wfile.write(http_response)

        return

    def log_request(self, code=None, size=None):
        print('Request')

    def log_message(self, format, *args):
        print('Message')

    def command_handler(self,cmd_list):
        if cmd_list != ['poll']:
            print "cmd_list", cmd_list
            if cmd_list[0] == "scratch_gpio":
                self.send(cmd_list[2])
            elif cmd_list[0] == "set_pin":
                self.send("pin"+cmd_list[2]+cmd_list[3])


    def send(self,senddata):
        if scratch_socket is not None:
            #print [match.start() for match in re.finditer(re.escape('send'), self.dataraw)]
            totalcmd =''
            cmd = 'broadcast "' + senddata + '"'
                    #print "sneding:",cmd
            n = len(cmd)
            b = (chr((n >> 24) & 0xFF)) + (chr((n >> 16) & 0xFF)) + (chr((n >>  8) & 0xFF)) + (chr(n & 0xFF))
            totalcmd = b + cmd
            print "Sending to Alt:",totalcmd
            conn.send(totalcmd)

class ScratchListener(threading.Thread):
    def __init__(self, socket):
        threading.Thread.__init__(self)
        self.scratch_socket = socket
        self.scratch_socket2 = None
        self._stop = threading.Event()
        self.dataraw = ''
        self.value = None
        self.valueNumeric = None
        self.valueIsNumeric = None
        self.OnOrOff = None
        self.searchPos = 0
        self.encoderDiff = 0
        self.turnSpeed = 40
        self.turnSpeedAdj = 0

        self.matrixX = 0
        self.matrixY = 0
        self.matrixUse = 64
        self.matrixColour = 'FFFFFF'
        self.matrixRed = 255
        self.matrixGreen = 255
        self.matrixBlue = 255
        self.matrixMult = 1
        self.matrixLimit = 1
        self.matrixRangemax = 8
        self.arm = None
        self.carryOn = True


    def meArmGotoPoint(self, meHorizontal, meDistance, meVertical):
        self.arm.gotoPoint(int(max(-50, min(50, meHorizontal))), int(max(70, min(150, meDistance))),
                           int(max(0, min(60, meVertical))))
        print "moved"


        # def send_scratch_command(self, cmd):
        # n = len(cmd)
        # b = (chr((n >> 24) & 0xFF)) + (chr((n >> 16) & 0xFF)) + (chr((n >>  8) & 0xFF)) + (chr(n & 0xFF))
        # self.scratch_socket.send(b + cmd)

    def getValue(self, searchString):
        outputall_pos = self.dataraw.find((searchString + ' '))
        sensor_value = self.dataraw[(outputall_pos + 1 + len(searchString)):].split()
        try:
            return sensor_value[0]
        except IndexError:
            return ""

    # Find pos of searchStr - must be preceded by a deself.matrixLimiting  space to be found
    def bFind(self, searchStr):
        #print "looking in" ,self.dataraw , "for" , searchStr
        self.searchPos = self.dataraw.find(' ' + searchStr) + 1
        #time.sleep(0.1)
        #if (' '+searchStr in self.dataraw):
        #print "Found"
        return (' ' + searchStr in self.dataraw)

    def bFindOn(self, searchStr):
        return (self.bFind(searchStr + 'on ') or self.bFind(searchStr + 'high ') or self.bFind(searchStr + '1 '))

    def bFindOff(self, searchStr):
        return (self.bFind(searchStr + 'off ') or self.bFind(searchStr + 'low ') or self.bFind(searchStr + '0 '))

    def bFindOnOff(self, searchStr):
        #print "searching for" ,searchStr
        self.OnOrOff = None
        if (self.bFind(searchStr + 'on ') or self.bFind(searchStr + 'high ') or self.bFind(
                    searchStr + '1 ') or self.bFind(searchStr + 'true ')):
            self.OnOrOff = 1
            return True
        elif (self.bFind(searchStr + 'off ') or self.bFind(searchStr + 'low ') or self.bFind(
                    searchStr + '0 ') or self.bFind(searchStr + 'false ')):
            self.OnOrOff = 0
            return True
        else:
            return False


    def bCheckAll(self, default=True, pinList=None):
        if self.bFindOnOff('all'):
            if default:
                pinList = sghGC.validPins
            for pin in pinList:
                #print pin
                if sghGC.pinUse[pin] in [sghGC.POUTPUT, sghGC.PPWM, sghGC.PPWMMOTOR]:
                    #print pin
                    sghGC.pinUpdate(pin, self.OnOrOff)

    def bPinCheck(self, pinList):
        for pin in pinList:
            logging.debug("bPinCheck:%s", pin)
            if self.bFindOnOff('pin' + str(pin)):
                sghGC.pinUpdate(pin, self.OnOrOff)
            if self.bFindOnOff('gpio' + str(sghGC.gpioLookup[pin])):
                sghGC.pinUpdate(pin, self.OnOrOff)
            if self.bFindValue('power' + str(pin)):
                print pin, self.value
                if self.valueIsNumeric:
                    sghGC.pinUpdate(pin, self.valueNumeric, type="pwm")
                else:
                    sghGC.pinUpdate(pin, 0, type="pwm")


    def bLEDCheck(self, ledList):
        for led in range(1, (1 + len(ledList))):  # loop thru led numbers
            if self.bFindOnOff('led' + str(led)):
                sghGC.pinUpdate(ledList[led - 1], self.OnOrOff)

    def bListCheck(self, pinList, nameList):
        for loop in range(0, len(pinList)):  # loop thru list
            #print str(nameList[loop]) , pinList[loop]
            if self.bFindOnOff(str(nameList[loop])):
                #print str(nameList[loop]) , "found"
                sghGC.pinUpdate(pinList[loop], self.OnOrOff)

            if self.bFindValue('power' + str(nameList[loop]) + ","):
                if self.valueIsNumeric:
                    sghGC.pinUpdate(pinList[loop], self.valueNumeric, type="pwm")
                else:
                    sghGC.pinUpdate(pinList[loop], 0, type="pwm")

    def bListCheckPowerOnly(self, pinList, nameList):
        for loop in range(0, len(pinList)):  # loop thru list
            if self.bFindValue('power' + str(nameList[loop]) + ","):
                if self.valueIsNumeric:
                    sghGC.pinUpdate(pinList[loop], self.valueNumeric, type="pwm")
                else:
                    sghGC.pinUpdate(pinList[loop], 0, type="pwm")

    def bFindValue(self, searchStr, searchSuffix=''):
        #logging.debug("Searching for:%s",searchStr )
        #return the value of the charachters following the searchstr as float if possible
        #If not then try to return string
        #If not then return ""
        self.value = None
        self.valueNumeric = None
        self.valueIsNumeric = False

        if self.bFind(searchStr):
            if searchSuffix == '':
                #print "$$$" + self.dataraw + "$$$"
                #print "search" , searchStr
                #print "pos", self.searchPos
                #print "svalue",(self.dataraw[(self.searchPos + len(searchStr)):] + "   ")
                #print "bfind",(self.dataraw[(self.searchPos + len(searchStr)):] + "    ").split()
                self.value = (self.dataraw[(self.searchPos + len(searchStr)):] + "   ").strip()
                if len(self.value) > 0:
                    self.value = self.value.split()[0]
                #print "1 s value",self.value
                #print self.value
                if isNumeric(self.value):
                    self.valueNumeric = float(self.value)
                    self.valueIsNumeric = True
                    #print "numeric" , self.valueNumeric
                return True
            else:
                self.value = (self.dataraw[(self.searchPos + len(searchStr)):] + "   ").strip()
                if len(self.value) > 0:
                    self.value = self.value.split()[0]
                if self.value.endswith(searchSuffix):
                    self.value = (self.value[:-len(searchSuffix)]).strip()
                    #print "2 s value",self.value
                    #print self.value
                    if isNumeric(self.value):
                        self.valueNumeric = float(self.value)
                        self.valueIsNumeric = True
                        #print "numeric" , self.valueNumeric
                    return True
                else:
                    return False
        else:
            return False

            # if self.bFind(searchStr):
            # if searchSuffix == '':
            # sensor_value = self.dataraw[(self.searchPos + len(searchStr)):].split()
            # #print "1 s value",sensor_value
            # try:
            # self.value = sensor_value[0]
            # except IndexError:
            # self.value = ""
            # pass
            # #print self.value
            # if isNumeric(self.value):
            # self.valueNumeric = float(self.value)
            # self.valueIsNumeric = True
            # #print "numeric" , self.valueNumeric
            # return True
            # else:
            # sensor_value = self.dataraw[(self.searchPos + len(searchStr)):].split()[0]
            # if sensor_value.endswith(searchSuffix):
            # sensor_value=sensor_value[:-len(searchSuffix)]
            # print "2 s value",sensor_value
            # try:
            # self.value = sensor_value[0]
            # except IndexError:
            # self.value = ""
            # pass
            # #print self.value
            # if isNumeric(self.value):
            # self.valueNumeric = float(self.value)
            # self.valueIsNumeric = True
            # #print "numeric" , self.valueNumeric
            # return True
            # else:
            # return False
            # else:
            # return False

    def bLEDPowerCheck(self, ledList):
        for led in range(1, (1 + len(ledList))):  # loop thru led numbers
            #print "power" +str(led) + ","
            if self.bFindValue('power' + str(led) + ","):
                if self.valueIsNumeric:
                    sghGC.pinUpdate(ledList[led - 1], self.valueNumeric, type="pwm")
                else:
                    sghGC.pinUpdate(ledList[led - 1], 0, type="pwm")

    def vFind(self, searchStr):
        return ((' ' + searchStr + ' ') in self.dataraw)

    def vFindOn(self, searchStr):
        return (self.vFind(searchStr + 'on') or self.vFind(searchStr + 'high') or self.vFind(searchStr + '1'))

    def vFindOff(self, searchStr):
        return (self.vFind(searchStr + 'off') or self.vFind(searchStr + 'low') or self.vFind(searchStr + '0'))

    def vFindOnOff(self, searchStr):
        self.value = None
        self.valueNumeric = None
        self.valueIsNumeric = False
        self.OnOrOff = None
        if self.vFind(searchStr):

            self.value = self.getValue(searchStr)
            if str(self.value) in ["high", "on", "1"]:
                self.valueNumeric = 1
                self.OnOrOff = 1
            else:
                self.valueNumeric = 0
                self.OnOrOff = 0
            return True
        else:
            return False

    def vFindValue(self, searchStr):
        #print "searching for ", searchStr
        self.value = None
        self.valueNumeric = None
        self.valueIsNumeric = False
        if self.vFind(searchStr):
            #print "found"
            self.value = self.getValue(searchStr)
            #print self.value
            if isNumeric(self.value):
                self.valueNumeric = float(self.value)
                self.valueIsNumeric = True
                #print "numeric" , self.valueNumeric
            return True
        else:
            return False

    def vAllCheck(self, searchStr):
        if self.vFindOnOff(searchStr):
            for pin in sghGC.validPins:
                if sghGC.pinUse[pin] in [sghGC.POUTPUT, sghGC.PPWM, sghGC.PPWMMOTOR]:
                    sghGC.pinUpdate(pin, self.valueNumeric)

    def vPinCheck(self):
        for pin in sghGC.validPins:
            #print "checking pin" ,pin
            if self.vFindValue('pin' + str(pin)):
                if self.valueIsNumeric:
                    sghGC.pinUpdate(pin, self.valueNumeric)
                else:
                    sghGC.pinUpdate(pin, 0)

            if self.vFindValue('power' + str(pin)):
                #print pin , "found"
                if self.valueIsNumeric:
                    sghGC.pinUpdate(pin, self.valueNumeric, type="pwm")
                else:
                    sghGC.pinUpdate(pin, 0, type="pwm")

            if self.vFindValue('motor' + str(pin)):
                if self.valueIsNumeric:
                    sghGC.pinUpdate(pin, self.valueNumeric, type="pwmmotor")
                else:
                    sghGC.pinUpdate(pin, 0, type="pwmmotor")

            if self.vFindValue('gpio' + str(sghGC.gpioLookup[pin])):
                logging.debug("gpio lookup %s", str(sghGC.gpioLookup[pin]))
                if self.valueIsNumeric:
                    sghGC.pinUpdate(pin, self.valueNumeric)
                else:
                    sghGC.pinUpdate(pin, 0)
                    #time.sleep(1)

            if self.vFindValue('powergpio' + str(sghGC.gpioLookup[pin])):
                logging.debug("pin %s", pin)
                logging.debug("gpiopower lookup %s", str(sghGC.gpioLookup[pin]))
                if self.valueIsNumeric:
                    sghGC.pinUpdate(pin, self.valueNumeric, type="pwm")
                else:
                    sghGC.pinUpdate(pin, 0, type="pwm")

    def vLEDCheck(self, ledList):
        for led in range(1, (1 + len(ledList))):  # loop thru led numbers
            if self.vFindOnOff('led' + str(led)):
                sghGC.pinUpdate(ledList[led - 1], self.OnOrOff)
                #logging.debug("pin %s %s",ledList[led - 1],self.OnOrOff )

            if self.vFindValue('power' + str(led)):
                if self.valueIsNumeric:
                    sghGC.pinUpdate(ledList[led - 1], self.valueNumeric, type="pwm")
                else:
                    sghGC.pinUpdate(ledList[led - 1], 0, type="pwm")


    def vListCheck(self, pinList, nameList):
        for loop in range(0, len(pinList)):  # loop thru pinlist numbers
            if self.vFindOnOff(str(nameList[loop])):
                sghGC.pinUpdate(pinList[loop], self.OnOrOff)

            if self.vFindValue('power' + str(nameList[loop])):
                if self.valueIsNumeric:
                    sghGC.pinUpdate(pinList[loop], self.valueNumeric, type="pwm")
                else:
                    sghGC.pinUpdate(pinList[loop], 0, type="pwm")
            if self.vFindValue('motor' + str(nameList[loop])):
                if self.valueIsNumeric:
                    sghGC.pinUpdate(pinList[loop], self.valueNumeric, type="pwmmotor")
                else:
                    sghGC.pinUpdate(pinList[loop], 0, type="pwmmotor")

    def vListCheckPowerOnly(self, pinList, nameList):
        for loop in range(0, len(pinList)):  # loop thru pinlist numbers
            if self.vFindValue('power' + str(nameList[loop])):
                if self.valueIsNumeric:
                    sghGC.pinUpdate(pinList[loop], self.valueNumeric, type="pwm")
                else:
                    sghGC.pinUpdate(pinList[loop], 0, type="pwm")

    def vListCheckMotorOnly(self, pinList, nameList):
        for loop in range(0, len(pinList)):  # loop thru pinlist numbers
            if self.vFindValue('motor' + str(nameList[loop])):
                if self.valueIsNumeric:
                    sghGC.pinUpdate(pinList[loop], self.valueNumeric, type="pwmmotor")
                else:
                    sghGC.pinUpdate(pinList[loop], 0, type="pwmmotor")

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()

    def stepperUpdate(self, pins, value, steps=2123456789, stepDelay=0.003):
        #print "pin" , pins , "value" , value
        #print "Stepper type", sgh_Stepper.sghStepper, "this one", type(sghGC.pinRef[pins[0]])
        try:
            sghGC.pinRef[pins[0]].changeSpeed(max(-100, min(100, value)), steps)  # just update Stepper value
            #print "stepper updated"
            # print ("pin",pins, "set to", value)
        except:
            try:
                print ("Stopping PWM")
                sghGC.pinRef[pins[0]].stop()

            except:
                pass
            sghGC.pinRef[pins[0]] = None
            #time.sleep(5)
            #print ("New Stepper instance started", pins)
            sghGC.pinRef[pins[0]] = sgh_Stepper.sghStepper(sghGC, pins, stepDelay)  # create new Stepper instance
            sghGC.pinRef[pins[0]].changeSpeed(max(-100, min(100, value)), steps)  # update Stepper value
            sghGC.pinRef[pins[0]].start()  # update Stepper value
            # print 'pin' , pins , ' changed to Stepper'
            #print ("pins",pins, "set to", value)
        sghGC.pinUse[pins[0]] = sghGC.POUTPUT


    def encoderCount(self, pin):
        lastL = sghGC.pinRead(pin)
        print "start", pin, lastL
        lastValidL = lastL
        while not sghGC.encoderStopCounting[pin]:
            time.sleep(0.002)
            val = sghGC.pinRead(pin)
            #print "val", countingPin, val
            if val == lastL and val != lastValidL:
                sghGC.pinCount[pin] += (sghGC.countDirection[pin] * 1)
                sghGC.encoderTimeDiff[pin] = time.time() - sghGC.encoderTime[pin]
                sghGC.encoderTime[pin] = time.time()
                lastValidL = val
                #print "count" ,pin , sghGC.pinCount[pin]
            lastL = val
        print "encoderCountExit for pin", pin

    def moveMotor(self, motorList, count, pin):
        speed = self.turnSpeed

        #This thread gets invoked when a command is given to turn the motor a number of steps
        print "encoder count at thread start", sghGC.encoderInUse
        print "counting pin", pin
        print "motor pins", sghGC.pinValue[motorList[1]], sghGC.pinValue[motorList[2]]
        #countingPin = motorList[1][3] # use 1st motor counting pin only
        print "Previous EncoderDiff:", sghGC.pinEncoderDiff[pin]
        #sghGC.pinEncoderDiff[countingPin] = 0
        sghGC.encoderStopCounting[pin] = False
        #start encoder count thread for this motor encoder
        encoderMoveThread = threading.Thread(target=self.encoderCount, args=[pin])
        encoderMoveThread.start()
        startCount = sghGC.pinCount[pin]
        countwanted = startCount + count + sghGC.pinEncoderDiff[pin]  # modifiy count based on previous result
        if (rtnSign(sghGC.pinEncoderDiff[pin]) != rtnSign(count)):
            print "doubling diff on pin ", pin
            countattempted = startCount + count + int(2 * sghGC.pinEncoderDiff[pin])  # allow for modified behaviour
        else:
            countattempted = startCount + count + int(1 * sghGC.pinEncoderDiff[pin])  # allow for modified behaviour
        print "extra count wanted/going to attempt", (countwanted - startCount), (countattempted - startCount)
        turningStartTime = time.time()  # used to timeout if necessary
        thisTurnSpeed = self.turnSpeed
        if pin == 12:
            thisTurnSpeed = self.turnSpeed + self.turnSpeedAdj
        print "pin turnspeed at start", pin, (self.turnSpeed + self.turnSpeedAdj)

        if count >= 0:
            sghGC.motorUpdate(motorList[1], motorList[2], thisTurnSpeed)
            while ((sghGC.pinCount[pin] < int(countattempted)) and ((time.time() - turningStartTime) < 20)):
                if pin == 13:
                    if sghGC.pinCount[13] > sghGC.pinCount[12]:
                        self.turnSpeedAdj = 0 - ( self.turnSpeed / 2)
                        #print "turnspeeed sub" ,self.turnSpeedAdj
                        time.sleep(0.005)
                    if sghGC.pinCount[13] < sghGC.pinCount[12]:
                        self.turnSpeedAdj = ( self.turnSpeed / 2)
                        #print "turnspeeed add" ,self.turnSpeedAdj
                        time.sleep(0.005)
                    if sghGC.pinCount[13] == sghGC.pinCount[12]:
                        self.turnSpeedAdj = 0
                        #print "turnspeeed stay" ,self.turnSpeedAdj
                        time.sleep(0.005)
                    sghGC.motorUpdate(motorList[1], motorList[2],
                                      max(0, min(100, (self.turnSpeed + self.turnSpeedAdj ))))
                else:
                    sghGC.motorUpdate(motorList[1], motorList[2], thisTurnSpeed)
                    print "encoder time diff", sghGC.encoderTimeDiff[pin]
                    #if ((sghGC.encoderTimeDiff[pin] > 0.04) and (sghGC.encoderTimeDiff[pin] < 1)):
                    #thisTurnSpeed += 1

                time.sleep(0.002)
        else:
            sghGC.motorUpdate(motorList[1], motorList[2], 0 - thisTurnSpeed)
            while ((sghGC.pinCount[pin] > int(countattempted)) and ((time.time() - turningStartTime) < 20)):
                if pin == 13:
                    if sghGC.pinCount[13] < sghGC.pinCount[12]:
                        self.turnSpeedAdj = 0 - ( self.turnSpeed / 2)
                        #print "turnspeeed sub" ,self.turnSpeedAdj
                        time.sleep(0.005)
                    if sghGC.pinCount[13] > sghGC.pinCount[12]:
                        self.turnSpeedAdj = ( self.turnSpeed / 2)
                        #print "turnspeeed add" ,self.turnSpeedAdj
                        time.sleep(0.005)
                    if sghGC.pinCount[13] == sghGC.pinCount[12]:
                        self.turnSpeedAdj = 0
                        #print "turnspeeed stay" ,self.turnSpeedAdj
                        time.sleep(0.005)
                    sghGC.motorUpdate(motorList[1], motorList[2],
                                      0 - max(0, min(100, (self.turnSpeed + self.turnSpeedAdj ))))
                else:
                    sghGC.motorUpdate(motorList[1], motorList[2], 0 - thisTurnSpeed)

                time.sleep(0.002)
        if pin == 13:
            print "pin turnspeed at end", pin, (self.turnSpeed + self.turnSpeedAdj )

        sghGC.motorUpdate(motorList[1], motorList[2], 0)
        print "motors off ", pin

        time.sleep(0.2)  #wait until motors have actually stopped
        sghGC.encoderStopCounting[pin] = True
        print ("how many moved", (sghGC.pinCount[pin] - startCount))
        sghGC.pinEncoderDiff[pin] = (countwanted - (sghGC.pinCount[pin]))  #work out new error in position
        msgQueue.put((5,'sensor-update "encoderdiff' + str(pin)) + '"' + str(
            sghGC.pinEncoderDiff[pin]) + '"')  # inform Scratch that turning is finished

        print "count wantedDiff:", countwanted, " / ", sghGC.pinEncoderDiff[pin]

        print "turning finished"
        print " "
        with lock:
            sghGC.encoderInUse -= 1
            print "encoders in use count at end of moveMotor for pin", pin, sghGC.encoderInUse

    def beep(self, pin, freq, duration):
        logging.debug("Freq:%s", freq)
        if sghGC.pinUse != sghGC.PPWM:  # Checks use of pin if not PWM mode then
            sghGC.pinUpdate(pin, 0, "pwm")  #Set pin to PWM mode
        startCount = time.time()  #Get current time
        sghGC.pinFreq(pin, freq)  # Set freq used for PWM cycle
        sghGC.pinUpdate(pin, 50, "pwm")  # Set duty cycle to 50% to produce square wave
        while (time.time() - startCount) < (duration * 1.0):  # Wait until duration has passed
            time.sleep(0.01)
        sghGC.pinUpdate(pin, 0, "pwm")  #Turn pin off

    def vListHBridge2(self, motorlist):
        for loop in motorlist:
            if self.vFindValue(loop[0]):
                svalue = min(100, max(-100, int(self.valueNumeric))) if self.valueIsNumeric else 0
                logging.debug("motor:%s valuee:%s", loop[0], svalue)
                sghGC.motorUpdate(loop[1], loop[2], svalue)

    def startUltra(self, pinTrig, pinEcho, OnOrOff):
        if OnOrOff == 0:
            try:
                sghGC.pinUltraRef[pinTrig].stop()
                sghGC.pinUse[pinTrig] = sghGC.PUNUSED
                sghGC.pinUltraRef[pinTrig] = None
                print "ultra stopped"
            except:
                pass
        else:
            print "Attemping to start ultra on pin:", pinTrig
            print sghGC.pinUltraRef[pinTrig]
            if True:  #if sghGC.pinUltraRef[pinTrig] is None:  NEEDS INVESTIGATING
                sghGC.pinUse[pinTrig] = sghGC.PSONAR
                sghGC.pinUltraRef[pinTrig] = ultra(pinTrig, pinEcho, self.scratch_socket)
                sghGC.pinUltraRef[pinTrig].start()
                print 'Ultra started pinging on', str(pinTrig)

    # noinspection PyPep8Naming
    def run(self):
        global firstRun, cycle_trace, step_delay, stepType, INVERT, \
            Ultra, ultraTotalInUse, piglow, PiGlow_Brightness, compass, ADDON, \
            meVertical, meHorizontal, meDistance, host



        #firstRun = True #Used for testing in overcoming Scratch "bug/feature"
        firstRunData = ''
        anyAddOns = False
        ADDON = ""
        #ultraThread = None

        #semi global variables used for servos in PiRoCon
        panoffset = 0
        tiltoffset = 0
        pan = 0
        tilt = 0
        steppersInUse = None
        beepDuration = 0.5
        beepNote = 60
        self.arm = None
        meHorizontal = 0
        meDistance = 100
        meVertical = 50
        tcolours = None  # set tcolours to None so it can be detected later
        pnblcd = None
        cheerList = None
        UH = None
        GPIOPlus = True
        ADDON = ""
        piglow = None
        if not GPIOPlus:
            with lock:
                print "set pins standard"
                for pin in sghGC.validPins:
                    sghGC.pinUse[pin] = sghGC.PINPUT
                sghGC.pinUse[3] = sghGC.PUNUSED
                sghGC.pinUse[5] = sghGC.PUNUSED
                sghGC.pinUse[11] = sghGC.POUTPUT
                sghGC.pinUse[12] = sghGC.POUTPUT
                sghGC.pinUse[13] = sghGC.POUTPUT
                sghGC.pinUse[15] = sghGC.POUTPUT
                sghGC.pinUse[16] = sghGC.POUTPUT
                sghGC.pinUse[18] = sghGC.POUTPUT
                sghGC.setPinMode()

        if piglow is not None:
            PiGlow_Values = [0] * 18
            PiGlow_Lookup = [0, 1, 2, 3, 14, 12, 17, 16, 15, 13, 11, 10, 6, 7, 8, 5, 4, 9]
            PiGlow_Brightness = 255


            #This is main listening routine
        lcount = 0
        dataPrevious = ""
        debugLogging = False

        listenLoopTime = time.time() + 10000
        datawithCAPS = ''
        #This is the main loop that listens for messages from Scratch and sends appropriate commands off to various routines
        while not self.stopped():

            #print "ListenLoopTime",listenLoopTime-time.time()
            listenLoopTime = time.time()
            #lcount += 1
            #print lcount
            try:
                #print "try reading socket"
                BUFFER_SIZE = 512  # This size will accomdate normal Scratch Control 'droid app sensor updates
                data ="1234"
                #data = dataPrevious + self.scratch_socket.recv(BUFFER_SIZE)  # get the data from the socket plus any data not yet processed
                logging.debug("datalen: %s", len(data))
                logging.debug("RAW: %s", data)
                print data
                exit

                if "send-vars" in data:
                    #Reset if New project detected from Scratch
                    #tell outer loop that Scratch has disconnected
                    if cycle_trace == 'running':
                        cycle_trace = 'disconnected'
                        print "cycle_trace has changed to", cycle_trace
                        break

                if len(data) > 0:  # Connection still valid so process the data received

                    dataIn = data
                    datawithCAPS = data
                    #dataOut = ""
                    dataList = []  # used to hold series of broadcasts or sensor updates
                    dataPrefix = ""  # data to be re-added onto front of incoming data
                    while len(dataIn) > 0:  # loop thru data
                        if len(dataIn) < 4:  #If whole length not received then break out of loop
                            #print "<4 chrs received"
                            dataPrevious = dataIn  # store data and tag it onto next data read
                            break
                        sizeInfo = dataIn[0:4]
                        size = struct.unpack(">L", sizeInfo)[0]  # get size of Scratch msg
                        #print "size:", size
                        if size > 0:
                            #print dataIn[4:size + 4]
                            dataMsg = dataIn[4:size + 4].lower()  # turn msg into lower case
                            #print "msg:",dataMsg
                            if len(dataMsg) < size:  # if msg recieved is too small
                                #print "half msg found"
                                #print size, len(dataMsg)
                                dataPrevious = dataIn  # store data and tag it onto next data read
                                break
                            if len(dataMsg) == size:  # if msg recieved is correct
                                if "alloff" in dataMsg:
                                    allSplit = dataMsg.find("alloff")

                                    logging.debug("Whole message:%s", dataIn)
                                    #dataPrevious = dataIn # store data and tag it onto next data read
                                    #break
                                #print "half msg found"
                                #print size, len(dataMsg)
                                dataPrevious = dataIn  # store data and tag it onto next data read
                                #break

                            dataPrevious = ""  # no data needs tagging to next read
                            if ("alloff" in dataMsg) or ("allon" in dataMsg):
                                dataList.append(dataMsg)
                            else:
                                if dataMsg[0:2] == "br":  # removed redundant "broadcast" and "sensor-update" txt
                                    if dataPrefix == "br":
                                        dataList[-1] = dataList[-1] + " " + dataMsg[10:]
                                    else:
                                        dataList.append(dataMsg)
                                        dataPrefix = "br"
                                else:
                                    if dataPrefix == "se":
                                        dataList[-1] += dataMsg[10:]
                                    else:
                                        dataList.append(dataMsg)
                                        dataPrefix = "se"

                            dataIn = dataIn[size + 4:]  # cut data down that's been processed

                            #print "previous:", dataPrevious



                #print 'Cycle trace' , cycle_trace
                if len(data) == 0:
                    #This is due to client disconnecting or user loading new Scratch program so temp disconnect
                    #I'd like the program to retry connecting to the client
                    #tell outer loop that Scratch has disconnected
                    if cycle_trace == 'running':
                        cycle_trace = 'disconnected'
                        print "cycle_trace has changed to", cycle_trace
                        break

            except (KeyboardInterrupt, SystemExit):
                print "reraise error"
                raise
            except socket.timeout:
                #print "No data received: socket timeout"
                continue
            except:
                print "Unknown error occured with receiving data"
                #raise
                continue

            #At this point dataList[] contains a series of strings either broadcast or sensor-updates
            #print "data being processed:" , dataraw
            #This section is only enabled if flag set - I am in 2 minds as to whether to use it or not!
            #if (firstRun == True) or (anyAddOns == False):
            #print
            #logging.debug("dataList: %s",dataList)
            #print
            #print
            #print "old datalist" , dataList
            if any("move" in s for s in dataList) or any("turn" in s for s in dataList):# or any("cheerlight" in s for s in dataList):
                #print "move/turn found in dataList so going to expandList"

                newList = []
                for item in dataList:
                    #print "item" , item
                    if "sensor-update" in item:
                        newList.append(item)
                    if "broadcast" in item:
                        bList = shlex.split(item)  #item.split(" ")
                        for bItem in bList[1:]:
                            newList.append('broadcast "' + bItem + '"')
                dataList = newList
                #print "new dataList" ,dataList

            #print "GPIOPLus" , GPIOPlus
            print "dataList to be processed", dataList
            raise
            for dataItem in dataList:
                #print dataItem
                #dataraw = ' '.join([item.replace(' ','') for item in shlex.split(dataItem)])
                dataraw = ' '
                #print "CAPS", datawithCAPS
                for item in shlex.split(dataItem):
                    #print "item in space remover" ,item
                    if item[0:4] == 'line':
                        origpos = datawithCAPS.lower().find(item)
                        item = datawithCAPS[origpos:origpos + len(item)]
                        item = 'line' + item[4:].strip()
                        item = item[0:5] + item[5:].lstrip()
                        dataraw = dataraw + ''.join(item.replace(' ', chr(254))) + ' '
                    else:
                        dataraw = dataraw + ''.join(item.replace(' ', '')) + ' '
                self.dataraw = dataraw

                logging.debug("processing dataItems: %s", self.dataraw)



###  End of  ScratchListner Class


if __name__ == "__main__":
    host ="192.168.0.86"
    port = 42001
    listener = None
    try:
        server = HTTPServer(('localhost', 1234), MyHandler)

        while True:
            try:
                print 'Trying'
                scratch_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                scratch_socket.bind(("192.168.0.47", port))
                print "socket", scratch_socket
                #become a server socket
                scratch_socket.listen(5)

                conn, addr = scratch_socket.accept()
                print 'Connected with ' + addr[0] + ':' + str(addr[1])
                time.sleep(3)
                listener = ScratchListener(scratch_socket)
                listener.start()

                break
            except socket.error:
                print "There was an error connecting to ScratchGPIO!"
                print "I couldn't find a connection to host: %s, port: %s" % (host, port)
                time.sleep(3)

        print('Started http server')
        server.serve_forever()
    except KeyboardInterrupt:
        print('^C received, shutting down server')
        listener.stop()
        listener.join()
        server.socket.close()
        scratch_socket2.socket.close()