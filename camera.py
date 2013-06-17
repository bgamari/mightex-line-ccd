import struct
import numpy as np
import usb.core
import usb.util

# endpoints
cmd_out = 0x01
cmd_in  = 0x81
data_in = 0x82

class WorkMode:
    NORMAL = 0x0
    TRIGGER = 0x1

class CameraError (RuntimeError):
    pass

device_info = struct.Struct('B14s14s14s')

class LineCamera (object):
    def __init__(self):
        self.dev = usb.core.find(idVendor=0x04B4, idProduct=0x0328)
        if self.dev is None:
            raise RuntimeError('Device not found')

    def _write_cmd(self, msg):
        a = self.dev.write(cmd_out, msg, 0) == len(msg)
        if not a:
            raise RuntimeError('Command write failed: ')

    def _read_cmd(self, data_length):
        a = self.dev.read(cmd_in, data_length+2, 0)
        if len(a) != data_length+2:
            raise RuntimeError('Command read failed')
        (result, length) = a[0:2]
        if result != 0x01:
            raise CameraError()
        data = a[2:]
        return data
            
    def get_firmware_ver(self):
        self._write_cmd(b'\x01\x01\x02')
        a = self._read_cmd(3)
        (major, minor, revision) = a[0:3]
        return (major, minor, revision)

    def get_device_info(self):
        self._write_cmd(b'\x21\x01\x00')
        a = self._read_cmd(device_info.size)
        info = device_info.unpack(a)
        return info

    def set_work_mode(self, mode):
        self._write_cmd(bytearray('\x30\x01')+bytearray([mode]))

    def set_exposure_time(self, time):
        if 0 > time > 0xffff:
            raise ValueError("Invalid exposure time")
        self._write_cmd(bytearray('\x31\x02')+bytearray([(time & 0xff00) >> 8, time & 0xff]))

    def get_buffered_frames_count(self):
        self._write_cmd(b'\x33\x01\x00')
        a = self._read_cmd(1)
        return a[0]

    def _prepare_frames(self, nframes):
        if 0 > nframes > 0xff:
            raise ValueError('Invalid frame count')
        self._write_cmd(b'\x34\x01'+bytearray([nframes]))

    def _read_frames(self, nframes):
        # For TCN-1304-U
        frame_length = 7680 # bytes
        a = self.dev.read(data_in, nframes*frame_length, 0)
        if len(a) != frame_length*nframes:
            raise RuntimeError("Incorrect frame size")
        a = np.frombuffer(a, dtype='<u2')
        def parse_frame(i):
            b = a[i*frame_length/2:(i+1)*frame_length/2]
            dark = a[16:29]
            image = a[32:32+3648]
            timestamp = a[3832]
            exp_time = a[3833]
            trigger_occurred = a[3434]
            trigger_count = a[3435]
            return (dark, image, timestamp, exp_time)
        return map(parse_frame, range(nframes))

    def get_frames(self, nframes=None):
        n = self.get_buffered_frames_count()
        if nframes is not None and n < nframes:
            raise RuntimeError('Not enough frames')
        if nframes is not None:
            n = nframes
        self._prepare_frames(n)
        return self._read_frames(n)

    def get_frame(self):
        n = self.get_buffered_frames_count()
        if n == 0: return None
        a = self._prepare_frames(1)
        return self._read_frames(1)[0]
        
    def set_gains(self, gains):
        if gains.__class__ is not tuple:
            red,green,blue = (gains, gains, gains)
        else:
            red,green,blue = gains
        self._write_cmd(b'\x39\x01'+[red,green,blue])
        
    
if __name__ == '__main__':
    c = LineCamera()
    print(c.get_firmware_ver())
    print(c.get_device_info())
    c.set_exposure_time(0x0004)
    c.set_work_mode(WorkMode.NORMAL)

    import time
    while True:
        time.sleep(1e-2)
        count = c.get_buffered_frames_count()
        if count == 0: continue
        c._prepare_frames(1)
        frame = c._read_frames(1)
        print frame[2], frame[0]

    
