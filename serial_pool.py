#coding=utf-8
# !/usr/bin/env python
"""
---------------------------------------------------------------------
   File Name:    serial_pool.py  
   Description:  Serial pool maintains couples of serial ports instance.
   Author:       Zhang Wei
   Date:         2017/04/06
---------------------------------------------------------------------
   Change Activity:
                   2017/04/06: Initial draft.
---------------------------------------------------------------------
"""

import time
import serial
# import fcntl
from serial_threaded import Protocol, ReaderThread

class DirectRelayer(Protocol):
    """
    Read binary data from serial port, and relay to destination receiver.
    The class also keeps track of the transport.
    """

    def __init__(self, params):
        self.buffer = bytearray()
        self.transport = None
        self.relay = params  # This parameter is the destination for received data.

    def connection_made(self, transport):
        """Store transport"""
        self.transport = transport

    def connection_lost(self, exc):
        """Forget transport"""
        self.transport = None
        del self.buffer[:]
        super(DirectRelayer, self).connection_lost(exc)

    def data_received(self, data):
        """Buffer received data, find TERMINATOR, call handle_packet"""
        self.buffer.extend(data)
        if self.relay:
            self.relay.write(self.buffer)
            print self.buffer
            del self.buffer[:]

    def handle_packet(self, packet):
        """Process packets - to be overridden by subclassing"""
        raise NotImplementedError('please implement functionality in handle_packet')

    def set_relay(self, relay):
        """set relay caller for received data."""
        self.relay = relay

    def write_line(self, text):
        """Write text to the transport."""
        if self.transport:
            self.transport.write(text)


class SerialPool(object):
    """
    class definition for serial pool.
    """
    def __init__(self):
        self.pool = dict()

    def add(self, one_ser):
        """
        Add one serial into pool.
        :param one_ser: {
                    'port': 'COM1',
                    'baudrate': 9600,
                    'bytesize': 8,
                    'parity': 'N',
                    'stopbits': 1,
                    'timeout': 0.5,
                    'xonxoff': False,
                    'rtscts': False,
                    'dsrdtr': False
                }
        :return: serial instance or None
        """
        if not isinstance(one_ser, dict):
            return None

        # check if it already exists.
        if not 'port' in one_ser.keys():
            return None
        portstr = one_ser['port']
        if portstr in self.pool.keys():
            ser = self.pool[portstr]
            if ser and ser.isOpen():
                return self.pool[portstr]
            else:
                if ser: del self.pool[portstr]
                return None

        # this port is new, add it.
        ser = serial.Serial()
        ser.port = portstr
        ser.timeout = 0.5
        if one_ser['baudrate']: ser.baudrate = one_ser['baudrate']
        if one_ser['bytesize']: ser.bytesize = one_ser['bytesize']
        if one_ser['parity']: ser.parity = one_ser['parity']
        if one_ser['stopbits']: ser.stopbits = one_ser['stopbits']
        if one_ser['timeout']: ser.timeout = one_ser['timeout']
        if one_ser['xonxoff']: ser.xonxoff = one_ser['xonxoff']
        if one_ser['rtscts']: ser.rtscts = one_ser['rtscts']
        if one_ser['dsrdtr']: ser.dsrdtr = one_ser['dsrdtr']
        # open the serial port, throw exception to caller.
        try:
            ser.open()
            # if ser.isOpen():
            #     try:
            #         fcntl.flock(port.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            #     except IOError:
            #         ser.close()
            #         return None
        except serial.SerialException as e:
            if serial.serial_for_url:
                try:
                    ser = serial.serial_for_url(ser.port,
                                                baudrate = ser.baudrate,
                                                bytesize = ser.bytesize,
                                                parity = ser.parity,
                                                stopbits = ser.stopbits,
                                                timeout = ser.timeout,
                                                xonxoff = ser.xonxoff,
                                                rtscts = ser.rtscts,
                                                dsrdtr = ser.dsrdtr)
                except serial.SerialException as e0:
                    return None
            else:
                return None

        self.pool[portstr] = ser
        print("Serial open on {} [{},{},{},{}{}{}]".format(
            ser.portstr,
            ser.baudrate,
            ser.bytesize,
            ser.parity,
            ser.stopbits,
            ' RTS/CTS' if ser.rtscts else '',
            ' Xon/Xoff' if ser.xonxoff else '',
        ))
        return ser

    def delete(self, portstr):
        if not isinstance(portstr, str):
            return False
        if not portstr in self.pool.keys():
            return False
        # it exists
        ser = self.pool[portstr]
        if ser.isOpen(): ser.close()
        del self.pool[portstr]
        return True

    def delete_all(self):
        for port, ser in self.pool.items():
            if ser.isOpen(): ser.close()
        self.pool.clear()

    def get(self, portstr):
        if not isinstance(portstr, str):
            return None
        if not portstr in self.pool.keys():
            return None
        # it exists
        ser = self.pool[portstr]
        if ser.isOpen():
            return ser
        else:
            del self.pool[portstr]
            return None


class SerialDelegator(object):
    """
    class definition for serial delegator.
    """
    def __init__(self, pool=None):
        # serial pool
        self.s_pool = pool or SerialPool()
        # delagator type
        self.d_type = None
        # source serial port setting
        self.s_src = None
        # destination serial port setting
        self.s_dest = None
        # serial reader, read data from source port
        self.sr = None
        # serial writer, write data to destination port
        self.sw = None
        # reader thread
        self.tr = None
        # relay class object
        self.relayer = None

    def setup(self, settings):
        """
        add serial pair.
        settings:{
            'd_type': 'direct'
            'ser_src', 'ser_dest': {
                'port': 'COM1',
                'baudrate': 9600,
                'bytesize': 8,
                'parity': 'N',
                'stopbits': 1,
                'timeout': 0.5,
                'xonxoff': False,
                'rtscts': False,
                'dsrdtr': False
            }
        }
        """
        if not isinstance(settings, dict):
            return None
        # delagator type
        self.d_type = settings['d_type'] if settings.has_key('d_type') else None
        # source serial port setting
        self.s_src = settings['ser_src'] if settings.has_key('ser_src') else None
        # destination serial port setting
        self.s_dest = settings['ser_dest'] if settings.has_key('ser_dest') else None
        # serial reader, read data from source port
        self.sr = self.s_pool.add(self.s_src)
        if not self.sr:
            self.teardown()
            return None
        # serial writer, write data to destination port
        self.sw = self.s_pool.add(self.s_dest)
        if not self.sw:
            self.teardown()
            return None
        # reader thread
        if (not self.d_type) or self.d_type == 'direct':
            self.tr = ReaderThread(self.sr, DirectRelayer, self.sw)
        else:
            return None
        if not self.tr:
            self.teardown()
            return None

        # start
        self.tr.start()
        self.tr, self.relayer = self.tr.connect()
        return self

    def teardown(self):
        if self.tr: self.tr.close()
        self.tr = None
        if self.sr: self.s_pool.delete(self.sr.portstr)
        self.sr = None
        if self.sw: self.s_pool.delete(self.sw.portstr)
        self.sw = None
        self.relayer = None

    def is_running(self):
        return self.tr.alive if self.tr else False


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
if __name__ == '__main__':
    ser_settings = {
        'ser_src': {
            'port': 'COM14',
            'baudrate': 9600,
            'bytesize': 8,
            'parity': 'N',
            'stopbits': 1,
            'timeout': 0.5,
            'xonxoff': False,
            'rtscts': False,
            'dsrdtr': False
        },
        'ser_dest': {
            'port': 'COM12',
            'baudrate': 9600,
            'bytesize': 8,
            'parity': 'N',
            'stopbits': 1,
            'timeout': 0.5,
            'xonxoff': False,
            'rtscts': False,
            'dsrdtr': False
        }
    }

    deleg1 = SerialDelegator()

    if deleg1:
        deleg1.setup(ser_settings)

        while deleg1.is_running():
            time.sleep(1)

