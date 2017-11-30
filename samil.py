#!/usr/bin/env python3
# samil.py
#
# Library and CLI tool for SolarLake TL-PM
# series (Samil Power inverters).
#
# (Requires Python 3)

import socket
import threading
import logging
import argparse
import sys
import time

logger = logging.getLogger(__name__)

# Maximum time between packets (seconds float). If this time is reached a
# keep-alive packet is sent.
keep_alive_time = 1.0
advertisement = b'\x55\xaa\x00\x0c\x01\x00\x00\x00\x00\x07\x00\x00\x00\x00\x01\x13'
model_request = b'\x55\xaa\x00\x11\x01\x00\x00\x00\x00\x00\x00\x00\x02\x80\x01\x00\x00\x00\x7a\x02\x0e'
data_request = 	b'\x55\xaa\x00\x11\x01\x00\x00\x00\x00\x00\x00\x03\x02\x80\x01\x03\xe8\x00\x4a\x02\xcc'

class InverterListener:
    def __init__(self, interface_ip=''):
        # Start server to listen for incoming connections
        listen_port = 60001
        logger.debug('Binding TCP socket to %s:%s', interface_ip, listen_port)
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((interface_ip, listen_port))
        self.server.settimeout(5.0) # Timeout defines time between broadcasts
        self.server.listen(5)
        # Creating and binding broadcast socket
        logger.debug('Binding UDP socket to %s:%s', interface_ip, 0)
        self.bc_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.bc_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.bc_sock.bind((interface_ip, 0))

    def __enter__(self):
        return self

    def __exit__(self, *args):
        # Stop listening server
        self.server.close()
        self.bc_sock.close()

    def connect(self):
        """Makes a connection to an inverter (the inverter that responds first).
        Blocks while waiting for an incoming inverter connection. Will keep blocking
        if no inverters respond.
        
        An instance of the Inverter class is returned.
        
        You can connect to multiple inverters by calling this function multiple
        times (each subsequent call will make a connection to a new inverter)."""
        logger.info('Searching for an inverter in the network')
        # Looping to wait for incoming connections while sending broadcasts
        tries = 0
        while True:
            if tries == 10:
                logger.warning('Connecting to inverter is taking a long '
                        'time, is it reachable?')
            logger.debug('Broadcasting server existence')
            self.bc_sock.sendto(advertisement, ('<broadcast>', 60000))
            try:
                sock, addr = self.server.accept()
            except socket.timeout:
                tries += 1
            else:
                logger.info('Connected with inverter on address %s', addr)
                return Inverter(sock, addr)


class Inverter:
    """This class has all functionality. Making a new instance of this class
    will search the network for an inverter and connect to it. The
    initialization blocks until the connection is made. If there is no inverter,
    the call will keep on blocking.
    
    When the connection is made you can use the methods to make data requests to
    the inverter. All request methods block while waiting for the answer (for me
    it takes typically 1.5 seconds for the response to arrive).
    
    When the connection is lost an exception is raised the next time a request
    is made.
    
    Connecting to multiple inverters is possible by making multiple instances of
    this class. Each next instance will connect to a different inverter in the
    network. When there is no inverter available anymore, the next instance
    initialization will keep on blocking.
    
    (The request methods are thread-safe.)"""
    
    def __init__(self, sock, addr):
        self.sock = sock
        self.addr = addr
        # A lock to ensure a single message at a time
        self.lock = threading.Lock()
        # Start keep-alive sequence
        self.keep_alive = threading.Timer(keep_alive_time, self.__keep_alive)
        self.keep_alive.daemon = True
        self.keep_alive.start()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.sock.shutdown(socket.SHUT_RDWR)
        self.sock.close()

    def request_model_info(self):
        """Requests model information like the type, software version, and
        inverter 'name'."""
        response = self.__make_request(model_request)
        # TODO: format a nice return value
        #raise NotImplementedError('Not yet implemented')
        logger.info('Model info: %s', response)
        return response

    def request_values(self):
        """Requests current values which are returned as a dictionary."""
        # Make request and receive response
        header, payload, end = self.__make_request(data_request)
        # Operating modes
        op_modes = {0: 'wait', 1: 'normal', 5: 'pv_power_off'}
        op_mode = op_modes[int.from_bytes(payload[48:50], byteorder='big')] if int.from_bytes(payload[48:50], byteorder='big') in op_modes else str(int.from_bytes(payload[48:50], byteorder='big'))
        result = {
            'ambiant_temp': int.from_bytes(payload[0:2], byteorder='big') / 10.0,
            'Inverter_temp': int.from_bytes(payload[14:16], byteorder='big') / 10.0,# degrees
            'pv1_voltage': int.from_bytes(payload[2:4], byteorder='big') / 10.0, # V
            'pv2_voltage': int.from_bytes(payload[4:6], byteorder='big') / 10.0, # V
            'pv1_current': int.from_bytes(payload[6:8], byteorder='big') / 10.0, # A
            'pv2_current': int.from_bytes(payload[8:10], byteorder='big') / 10.0, # A
            'total_operation_hours': int.from_bytes(payload[38:42], byteorder='big'), # h
            # Operating mode needs more testing/verifying
            'operating_mode': op_mode,
            'energy_today': int.from_bytes(payload[42:44], byteorder='big') / 100.0, # kWh
            #'pv1_input_power': ints[19], # W
            #'pv2_input_power': ints[20], # W
            'grid_current': int.from_bytes(payload[22:24], byteorder='big') / 10.0, # A
            'grid_voltage': int.from_bytes(payload[18:20], byteorder='big') / 10.0, # V
            'grid_frequency': int.from_bytes(payload[20:22], byteorder='big') / 100.0, # Hz
            'output_power': int.from_bytes(payload[44:48], byteorder='big'), # W
            'energy_total': int.from_bytes(payload[34:38], byteorder='big') / 10.0, # kWh
        }
        # For more info on the data format:
        # https://github.com/mhvis/solar/wiki/Communication-protocol#messages
        logger.debug('Current values: %s', result)
        return result

    
    def __make_request(self, request, response_id=None):
        """Directly makes a request and returns the response."""
        # Acquire socket request lock
        with self.lock:
            # Cancel a (possibly) running keep-alive timer
            self.keep_alive.cancel()
            self.sock.send(request)
            # Receive message, possibly retrying when wrong message arrived
            while True:
                data = self.sock.recv(1024)
                response = _tear_down_response(data)
                if not response_id or response_id == response[0]:
                    break
                else:
                    logger.info('Received unexpected message, waiting for a '
                            'new one')
            logger.debug('Request: %s', request)
            logger.debug('Response: %s', response)
            # Set keep-alive timer
            self.keep_alive = threading.Timer(keep_alive_time, self.__keep_alive)
            self.keep_alive.daemon = True
            self.keep_alive.start()
        return response
    
    def __keep_alive(self):
        """Makes a keep-alive request."""
        logger.debug('Keep alive')
        # I was not able to find a keep alive request so I just use a data request
        try:
            values = self.request_values();
            logging.info(values);
        except Exception as err:
            logger.warning('Error in keep alive thread: %s', err)

    def __str__(self):
        # Possibly also return model name/serial number
        return self.addr[0]

    def __repr__(self):
        # See __str__
        return self.addr[0]


def _tear_down_response(data):
    """Helper function to extract header, payload and end from received response
    data."""
    response_header = data[2:17]
    # Below is actually not used
    response_payload_size = data[18]
    response_payload = data[19:-2]
    response_end = data[-2:]
    return response_header, response_payload, response_end

# Test procedure
if __name__ == '__main__':
    import time
    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
    with InverterListener() as listener:
        inverter = listener.connect()
    with inverter:
        inverter.request_model_info()
        while True:
            inverter.request_values()
            time.sleep(1)
