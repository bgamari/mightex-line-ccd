#!/usr/bin/python

import numpy as np
from numpy import exp, sqrt, pi
from camera import *
import microscope
import wx
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
from matplotlib.backends.backend_wxagg import NavigationToolbar2Wx as Toolbar
from matplotlib.figure import Figure


class PlotPanel(wx.Panel):
    def __init__(self, parent, camera):
        self.camera = camera
        wx.Panel.__init__(self, parent, -1)

        self.fig = Figure((5,4), 75)
        self.canvas = FigureCanvasWxAgg(self, -1, self.fig)
        self.toolbar = Toolbar(self.canvas) #matplotlib toolbar
        self.toolbar.Realize()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, wx.LEFT|wx.TOP|wx.GROW)
        sizer.Add(self.toolbar, 0, wx.GROW)
        self.SetSizer(sizer)
        self.Fit()        

        im = self.read_frame()
        self.image_sz = len(im)
        self.clear_background()
            
        self.oversamples = 10
        self.images = np.zeros((self.image_sz-39, self.oversamples)) # FIXME
        self.image_n = 0
        self.set_window_size(10)
        self.init_plot_data()

        self.update_timer = wx.PyTimer(self.update)
        self.OnStartStop(None)

    def set_window_size(self, window_sz):
        self.kernel = exp(-np.arange(4*window_sz)**2 / window_sz**2) / sqrt(2*pi) / window_sz

    def clear_background(self):
        self.background = np.zeros(self.image_sz)
        
    def read_frame(self):
        frame = None
        for i in range(5): # Try five times to get frame
            try: frame = self.camera.get_frame()
            except: pass
        if frame is None:
            raise RuntimeError('Failed to acquire frame')
        return frame[1] - np.mean(frame[0])
        
    def init_plot_data(self):
        self.read_frame()
        
        self.ax1 = self.fig.add_subplot(211)
        self.curve, = self.ax1.plot([], [])
        self.ax1.set_ylim(-10, 0xffff+10)
        self.ax1.set_xlim(0, 3648)
        self.ax1.axvline(x=1824, color='r')

        self.ax2 = self.fig.add_subplot(212)
        self.maxima = []
        self.max_curve, = self.ax2.plot(self.maxima)
        self.ax2.set_xlim(0,2000)
        self.ax2.set_ylim(1000,2000)

        #self.toolbar.update()

    def update(self):
        data = self.read_frame() - self.background
        data = np.convolve(data, self.kernel, 'valid')
        self.images[:,self.image_n] = data
        data = np.mean(self.images, axis=1)
        self.image_n = (self.image_n + 1) % self.oversamples
        x = np.arange(len(data))
        self.curve.set_data(x, data)

        max_x = np.argmax(data)
        self.maxima.append(max_x)
        self.maxima = self.maxima[:1000]
        n = len(self.maxima)
        self.max_curve.set_data(np.arange(n), self.maxima)
        self.ax2.relim()
        self.ax2.autoscale_view(scaley=False)

        self.fig.canvas.draw()   
    
    def GetToolBar(self):
        return self.toolbar

    def OnStartStop(self, evt):
        if self.update_timer.IsRunning():
            self.update_timer.Stop()
        else:
            self.update_timer.Start(100, False)
            self.canvas.draw()

    def OnAcquireBackground(self, evt):
        self.clear_background()
        while self.background is None:
            self.background = self.read_frame()

        self.setpoint = self.read_frame() - self.background

    def OnClearBackground(self, evt):
        self.clear_background()
        
    def onEraseBackground(self, evt):
        pass

#m = Microscope()
#print 'Connected to microscope: %s' % m.get_unit()
#m.enable_buttons()

c = LineCamera()
print('Firmware version', c.get_firmware_ver())
print('Device version', c.get_device_info())
c.set_work_mode(WorkMode.NORMAL)
c.set_exposure_time(0x0015)

if __name__ == '__main__':
    app = wx.PySimpleApp()
    frame = wx.Frame(None, -1, 'Plotter')
    plotter = PlotPanel(frame, c)
    frame.Show()
    app.MainLoop()


