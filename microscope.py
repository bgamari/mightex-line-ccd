import time
import serial
import threading

# From protocol description at http://madhadron.com/olympus-ix-81-chassis-commands
class Microscope(object):
    def __init__(self, port='COM1:'):
        self.device = serial.Serial(port, baudrate=19200, timeout=1,
                                    stopbits=serial.STOPBITS_ONE,
                                    
                                    parity=serial.PARITY_EVEN)

        self.device.write('\r\n')
        self.device.write('1LOG IN\r\n')
        self.device.readline()
        self.device.write('2LOG IN\r\n')
        self.device.readline()
        self.device.flush()
        
        self.reader = threading.Thread(target=self._reader)
        self.reader.daemon = True
        self.reader.start()
        self.responses = []
        self.responses_cond = threading.Condition()

    def _reader(self):
        while True:
            l = self.device.readline()
            parts = l.split()
            if len(parts) == 0:
                pass
            elif l.startswith('1x') or l.startswith('2x'):
                print 'Invalid command'
            else:
                self.responses_cond.acquire()
                self.responses.append(parts)
                self.responses_cond.notify_all()
                self.responses_cond.release()

    def _expect_reply(self, cmd):
        self.responses_cond.acquire()
        while len([r for r in self.responses if r[0] == cmd]) == 0:
            self.responses_cond.wait()
        resp = [r for r in self.responses if r[0] == cmd][0]
        self.responses.remove(resp)
        self.responses_cond.release()
        return resp[1:]
                
    def _state_cmd(self, cmd, value=''):
        self.device.write('%s %s\r\n' % (cmd, value))
        return self._expect_reply(cmd)

    def _query_cmd(self, cmd):
        self.device.write('%s?\r\n' % cmd)
        return self._expect_reply(cmd)
    
    def get_unit(self):
        self.device.write('1UNIT?\r\n')
        return self._expect_reply('1UNIT')

    def get_position(self):
        """ Get the current focus position in tens of nanometers """
        self.device.write('2POS?\r\n')
        return int(self._expect_reply('2POS')[0])
        
    def move(self, x):
        self._state_cmd('2MOV', '%s,%d' % ('F' if x < 0 else 'N', abs(x)))

    def stop(self):
        self._state_cmd('2STOP', '')
        
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

    def set_lamp_state(self, on):
        self._state_cmd('1LMPSW', 'ON' if on else 'OFF')

    def set_lamp_intensity(self, intensity):
        self._state_cmd('1LMP', str(intensity))

    def set_light_path(self, camera):
        self._state_cmd('1PRISM', '2' if camera else '1')
        
class ButtonfulMicroscope(Microscope):
    def __init__(self, port='COM1:'):
        Microscope.__init__(self, port)
        
        self.enable_buttons()
        self.lamp_state = True if self._query_cmd('1LMPSW')[0] == 'ON' else False
        self.lamp_intensity = int(self._query_cmd('1LMP')[0])
        self.light_path = int(self._query_cmd('1PRISM')[0])
        self.jog_sensitivity = int(self._query_cmd('2JOGSNS')[0])
        self.jog_speed = 0
        self.jog_start = threading.Event()

        self.jog_thread = threading.Thread(target=self._jog_worker)
        self.jog_thread.daemon = True
        self.jog_thread.start()
        
        self.button_thread = threading.Thread(target=self._button_worker)
        self.button_thread.daemon = True
        self.button_thread.start()

    def _button_worker(self):
        while True:
            button = int(self._expect_reply('1SW')[0])
            self._on_button(button)
        
    def _jog_worker(self):
        while True:
            self.jog_start.wait()
            self.jog_start.clear()
            while self.jog_speed != 0:
                self.move(self.jog_speed)
                self.jog_speed *= 1.05
                time.sleep(0.03)
                
    def _on_button(self, button):
        print 'button', button
        if button == 100:                       # jog down
            self.jog_speed = -200
            self.jog_start.set()
        elif button == 400:                     # jog up
            self.jog_speed = 200
            self.jog_start.set()
        elif button == 2:                       # lamp on/off
            self.lamp_state = not self.lamp_state
            self.set_lamp_state(self.lamp_state)
        elif button == 8:                       # lamp intensity up
            self.lamp_intensity += 2
            self.set_lamp_intensity(self.lamp_intensity)
        elif button == 10:                      # lamp intensity down
            self.lamp_intensity -= 2
            self.set_lamp_intensity(self.lamp_intensity)
        elif button == 1:                       # light path
            self.light_path = not self.light_path
            self.set_light_path(self.light_path)
        elif button == 200:                     # fine/coarse
            self.jog_sensitivity = 2 if self.jog_sensitivity == 8 else 8
            self.set_jog_sensitivity(self.jog_sensitivity)
            print 'jog sensitivity', self.jog_sensitivity
        elif button == 0:
            self.jog_speed = 0
            
if __name__ == '__main__':
    import time

    m = ButtonfulMicroscope()
    print m.get_unit()
    m.enable_jog()
    while True:
        print m.get_position()
        #m.move(-2000)
        time.sleep(1)

