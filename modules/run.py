import threading
import time
from lcd import LCD
from e22 import E22
from protocol import Alert, SeqCounter, encode_alert, now_ms16
from queue import Queue
from dataclasses import dataclass

#pipeline에 들어갈 Event 형식
@dataclass
class Event:
    id: int #인식 개체 id? seq?
    status:str #거리 상태
    vel:float #(가능하다면)속도

class Pipeline:
    def __init__(self):
        self._msg_q = Queue()
        self._display_q = Queue()
        self._lcd = LCD()
        self._runningFlag = True

    def thread_lcd(self):
        while self._runningFlag:
            if not self._display_q.empty():
                data:Event = self._display_q.get()
                string = [[f'ID:{data.id}|sta:{data.status}'],
                          [f'VEL:{data.vel}']]
                self._lcd.write(string)
            time.sleep(0.01)