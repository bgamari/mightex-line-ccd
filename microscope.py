import serial

class Microscope(object):
    def __init__(self, port='COM1:'):
        self.device = serial.Serial(port, baudrate=19200, timeout=1,
                                    stopbits=serial.STOPBITS_ONE,
                                    
                                    parity=serial.PARITY_EVEN)
        self.device.write('\r\n')
        self.device.write('2LOG IN\r\n')
        self.device.readline()

    def get_unit(self):
        self.device.write('1UNIT?\r\n')
        return self.device.readline()

    def get_position(self):
        """ Get the current focus position in tens of nanometers """
        self.device.write('2POS?\r\n')
        response, value = self.device.readline().split(' ')
        if response != '2POS':
            raise RuntimeError('Unexpected response')
        return int(value)

    def move(self, x):
        self._state_cmd('2MOV', '%s,%d' % ('F' if x < 0 else 'N', abs(x)))

    def stop(self):
        self._state_cmd('2STOP', '')
        
    def _state_cmd(self, cmd, value):
        self.device.write('%s %s\r\n' % (cmd, value))
        resp = self.device.readline()
        if not resp.startswith('%s +' % cmd):
            raise RuntimeError('Unexpected response: ' + resp)
        
    def enable_jog(self):
        self._state_cmd('2JOG', 'ON')
        self._state_cmd('2joglmt', 'ON')

    def set_jog_sensitivity(self, value):
        self._state_cmd('2JOGSNS', str(value))

    def disable_jog(self):
        self._state_cmd('2JOG', 'OFF')

    def enable_buttons(self):
        self._state_cmd('1SW', 'ON')

    def disable_buttons(self):
        self._state_cmd('1SW', 'OFF')

if __name__ == '__main__':
    import time

    m = Microscope()
    print m.get_unit()
    m.enable_jog()
    while True:
        print m.get_position()
        m.move(-2000)
        time.sleep(5)
        print m.get_position() 
        m.move(2000)
        time.sleep(5)
