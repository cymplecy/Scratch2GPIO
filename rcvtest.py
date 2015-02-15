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





###  End of  ScratchListner Class


if __name__ == "__main__":
    host ="192.168.0.86"
    port = 42001
    listener = None
    try:


        while True:

            print 'Trying'
            scratch_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            scratch_socket.bind(("192.168.0.47", port))
            print "socket", scratch_socket
            #become a server socket
            scratch_socket.listen(5)

            conn, addr = scratch_socket.accept()
            print 'Connected with ' + addr[0] + ':' + str(addr[1])
            time.sleep(3)

            #This is main listening routine
            lcount = 0
            dataPrevious = ""
            debugLogging = False


            datawithCAPS = ''
            #This is the main loop that listens for messages from Scratch and sends appropriate commands off to various routines
            while True:

                #lcount += 1
                #print lcount
                    #print "try reading socket"
                BUFFER_SIZE = 512  # This size will accomdate normal Scratch Control 'droid app sensor updates
                #data ="1234"
                data = dataPrevious + conn.recv(BUFFER_SIZE)  # get the data from the socket plus any data not yet processed
                logging.debug("datalen: %s", len(data))
                logging.debug("RAW: %s", data)
                print data
                exit


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

                print "dataList to be processed", dataList


        print('Started http server')

    except KeyboardInterrupt:
        print('^C received, shutting down server')
        server.socket.close()
        scratch_socket2.socket.close()