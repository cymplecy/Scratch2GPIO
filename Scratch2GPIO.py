# Copyright Simon Walters 2015 from original code by Alan Yorinks (s2a_fm project)
# All code is provided under GPL2 and any copies must also be distributed under GPL2 or a later version
#
# Version is 0.0.1 alpha
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import urlparse
from string import split
import socket
import time as time

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


if __name__ == "__main__":
    host ="192.168.0.86"
    port = 42001
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
                time.sleep(5)


                break
            except socket.error:
                print "There was an error connecting to ScratchGPIO!"
                print "I couldn't find a connection to host: %s, port: %s" % (host, port)
                time.sleep(3)

        print('Started http server')
        server.serve_forever()
    except KeyboardInterrupt:
        print('^C received, shutting down server')
        server.socket.close()
        scratch_socket2.socket.close()