import tkinter as tk
from tkinter.font import BOLD, Font
from threading import Thread
from enum import Enum
import serial
import time
from jproperties import Properties

class SerialThr(Thread):

    def __init__(self, comPort, baudrate, sensorIni, sensorFim, onIni=None, onFim=None):
        super().__init__()

        self.sensorIni = sensorIni
        self.sensorFim = sensorFim
        self._onIni = onIni
        self._onFim = onFim

        self.comPort = serial.Serial(
            port=comPort, 
            baudrate=baudrate,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS
            )
        
    def run(self):
        while self.comPort:
            if self.comPort.in_waiting > 0:
                dataRead = bytearray(self.comPort.read(100))
                self.comPort.reset_input_buffer()
                c = ~dataRead.pop()
                
                vIni = bool((c>>(self.sensorIni))&1)
                vFim = bool((c>>(self.sensorFim))&1)

                if self._onIni and callable(self._onIni) and vIni :
                    self._onIni()

                if self._onFim and callable(self._onFim) and vFim :
                    self._onFim()

    def closePort(self):
        self.comPort.close()

class Estado(Enum):
    WAITING = 1
    RUNNING = 2
    STOPPED = 3
    DESTROY = 4

class Timer(Thread): 

    def __init__(self):
        super().__init__()
        self.cont = 0
        self.estado = Estado.WAITING
        self._tick = 0

    def run(self):
        while(self.estado != Estado.DESTROY):
            
            match self.estado:
                case Estado.WAITING:
                    self._tick = time.time()
                case Estado.RUNNING:
                    time.sleep(0.0001)
                    self.cont = time.time()-self._tick


    def reset(self):
        self.cont = 0
        self.estado = Estado.WAITING

    def pause(self):
        self.estado = Estado.STOPPED

    def resume(self):
        self.estado = Estado.RUNNING

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.timer = Timer()
        
        configs = Properties()

        with open('config.properties', 'rb') as config_file:
            configs.load(config_file)

        port = configs.get('PORT').data
        baudrate = int(configs.get('BAUDRATE').data)
        iniBit = int(configs.get('INI_BIT').data)
        fimBit = int(configs.get('FIM_BIT').data)

        self.serialThr = SerialThr(port, baudrate, iniBit, fimBit, self.onIni, self.onFim)

        self.title('Cronometro Robocharq')
        self.configure(background='black')
        self.columnconfigure(0,weight=1)

        self._fullscreen = True

        self.attributes('-fullscreen', self._fullscreen)
        self.geometry("800x600")
        self.fontSize = int(configs.get('FONTSIZE').data)
        font = Font(self, size=self.fontSize, weight=BOLD, family='Arial')
        self.label = tk.Label(self, text='00:00,00', font=font, anchor=tk.CENTER)
        self.label.pack()
        self.label.configure(foreground='#00FF00', background='black')

        txtHelp = """
        ESC - Sair
        H - Ajuda
        Z - Armar Cronometro
        F - Tela Cheia
        ESPAÇO - Pausar/Contar Manualmente
        [ - Diminuir Fonte
        ] - Aumentar Fonte
        """
        font = Font(self, size=24, weight=BOLD, family='Arial')
        self.labelHelp = tk.Label(self, text=txtHelp, font=font)
        self.labelHelp.configure(foreground='white', background='black')
        self.showHelp = False

        self.bind('<Escape>', lambda e: self.destroy())
        self.bind('<z>', lambda e: self.timer.reset())
        self.bind('<f>', lambda e: self.onFullscreen() )
        self.bind('<space>', lambda e: self.pauseResume())
        self.bind('<]>', lambda e: self.onResizeFont(1.1))
        self.bind('<[>', lambda e: self.onResizeFont(0.9))
        self.bind('<h>', lambda e: self.onHelp())
        self.updateTime()
        self.timer.start()
        self.serialThr.start()

    def pauseResume(self):
        self.timer.pause() if self.timer.estado == Estado.RUNNING else self.timer.resume()

    def onResizeFont(self, factor):
        self.fontSize *= factor 
        font = Font(self, size=int(self.fontSize), weight=BOLD, family='Arial')
        self.label.config(font=font)

    def onHelp(self):
        self.showHelp = not self.showHelp
        self.labelHelp.pack() if self.showHelp else self.labelHelp.pack_forget()
        
    def onFullscreen(self):
        print('fullscreen')
        self._fullscreen = not self._fullscreen
        self.attributes('-fullscreen', self._fullscreen)

    def onIni(self):
        print('onIni')
        if self.timer.estado == Estado.WAITING:
            self.timer.resume()

    def onFim(self):
        print('onFim')
        if self.timer.estado == Estado.RUNNING:
            self.timer.pause()

    def destroy(self) -> None:
        self.timer.estado = Estado.DESTROY
        self.serialThr.closePort()
        return super().destroy()
        
    def updateTime(self):
        time = self.timer.cont*1000
        min = time // 60000
        time = time % 60000
        seg = time // 1000
        time = time % 1000
        cs = time // 10

        if self.timer.estado != Estado.STOPPED:
            txt = "{min:02.0f}:{seg:02.0f},{cs:02.0f}"
            self.label.configure(text=txt.format(min=min, seg=seg, cs=cs))
        

        match self.timer.estado:
            case Estado.WAITING:
                self.label.config(fg='white')

            case Estado.RUNNING:
                self.label.config(fg='#00FF00')

            case Estado.STOPPED:
                self.label.config(fg='orange')

        self.after(16, self.updateTime)

if __name__ == "__main__":
    app = App()
    app.mainloop()
    