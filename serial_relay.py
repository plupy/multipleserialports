# -*- coding: utf-8 -*-
# !/usr/bin/env python
"""
---------------------------------------------------------------------
   File Name:    serial_relay.py  
   Description:  Serial relay support for configured two serial ports.
                 For given port1 and port2, read from port1, 
                 and write into port2 after analysis.
   Author:       Zhang Wei
   Date:         2017/04/01
---------------------------------------------------------------------
   Change Activity:
                   2017/04/01: Initial draft.
---------------------------------------------------------------------
"""

import serial
from multiprocessing import JoinableQueue
import threading
import time


class SerialTerminal(object):
    """
    class definition for serial terminal, role as 'reader' or 'writer'.
    """
    def __init__(self, settings, que=None, role='reader'):
        self.role = role.lower().strip()
        self.serial = serial.Serial()
        self.settings = settings
        self.serial.timeout = 0.5  # make sure that the alive event can be checked from time to time
        self.queue = que
        self.thread = None
        self.alive = threading.Event()
        self.setup(settings)


    def start(self):
        """Start the receiver thread"""
        thread_func = self.__getattribute__(self.role+'_thread')
        if thread_func:
            self.thread = threading.Thread(target=thread_func)
            self.thread.setDaemon(1)
            self.alive.set()
            self.thread.start()
            self.serial.rts = True
            self.serial.dtr = True


    def stop(self):
        """Stop the receiver thread, wait until it's finished."""
        if self.thread is not None:
            self.alive.clear()          # clear alive event for thread
            if self.queue:
                self.queue.put(None)
            self.thread.join()          # wait until thread has finished
            self.thread = None


    def reader_thread(self):
        """
        Thread that handles the incoming traffic for source serial port. Does the basic input
        transformation (callback) and generates an SerialRx to writer. 
        """
        print("Serial {} enter".format(self.role))
        while self.alive.isSet():
            b = self.serial.read(self.serial.in_waiting or 1)
            if b:
                # got data
                if self.queue:
                    self.queue.put(b)
        print("Serial {} quit".format(self.role))

    def writer_thread(self):
        """
        Thread that handles the incoming traffic for source serial port. Does the basic input
        transformation (callback) and generates an SerialRx to writer. 
        """
        while self.alive.isSet():
            if self.queue:
                b = self.queue.get()
                if b:
                    # got data
                    self.serial.write(b)
                    self.queue.task_done()
            else:
                print("Serial {} no queue".format(self.role))
                time.sleep(1)

        print("Serial {} quit".format(self.role))


    def setup(self, settings=None):
        # close serial port first.
        self.teardown()

        if settings:
            self.serial.port = settings['port']
            if settings['baudrate']: self.serial.baudrate = settings['baudrate']
            if settings['bytesize']: self.serial.bytesize = settings['bytesize']
            if settings['parity']: self.serial.parity = settings['parity']
            if settings['stopbits']: self.serial.stopbits = settings['stopbits']
            if settings['timeout']: self.serial.timeout = settings['timeout']
            if settings['xonxoff']: self.serial.xonxoff = settings['xonxoff']
            if settings['rtscts']: self.serial.rtscts = settings['rtscts']
            if settings['dsrdtr']: self.serial.dsrdtr = settings['dsrdtr']

        # open the serial port, throw exception to caller.
        self.serial.open()
        self.settings = self.serial.get_settings()
        print("Serial {} open on {} [{},{},{},{}{}{}]".format(
            self.role,
            self.serial.portstr,
            self.serial.baudrate,
            self.serial.bytesize,
            self.serial.parity,
            self.serial.stopbits,
            ' RTS/CTS' if self.serial.rtscts else '',
            ' Xon/Xoff' if self.serial.xonxoff else '',
        ))


    def teardown(self):
        self.stop()
        if self.serial.isOpen():
            self.serial.close()


class SerialRelay(object):
    """
    class definition for serial relay.
    """
    def __init__(self, ser_settings, callback=None):
        """
        build relay object.
        ser_settings:{
            ser_src, ser_dest: {
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
        # source serial port setting
        self.s_src = ser_settings['ser_src'] if ser_settings else None
        # destination serial port setting
        self.s_dest = ser_settings['ser_dest'] if ser_settings else None
        # callback function for data passing, the callback should be non-blocking.
        self.callback = callback
        # serial reader, read data from source port
        self.sr = None
        # serial writer, write data to destination port
        self.sw = None
        # the queue used for transfer data from source to destination.
        self._queue = JoinableQueue()
        # alive for this relay
        self.alive = threading.Event()

        self.setup()

    def setup(self, ser_settings=None):
        """
        Setup the serial relay.
        Open serial ports,
        """
        self.teardown()

        self.sw = SerialTerminal(self.s_dest, self._queue, 'writer')
        self.sr = SerialTerminal(self.s_src, self._queue, 'reader')

    def teardown(self):
        if self.sr: self.sr.teardown()
        if self.sw: self.sw.teardown()
        self.alive.clear()
        self.sr = None
        self.sw = None

    def start(self):
        if not self.alive.isSet():
            if self.sw: self.sw.start()
            if self.sr: self.sr.start()
            self.alive.set()


    def stop(self):
        if self.alive.isSet():
            if self.sr: self.sr.stop()
            if self.sw: self.sw.stop()
            self.alive.clear()


# script main entry
if __name__ == '__main__':
    ser_settings = {
        'ser_src': {
            'port': 'COM11',
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

    relay1 = SerialRelay(ser_settings)
    relay1.start()

    while relay1.alive:
        time.sleep(1)
