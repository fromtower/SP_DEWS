"""
test_alert.py — alert_tx ↔ alert_rx 하드웨어 없는 시험. `python test_alert.py`

E22 대신 서로 연결된 가짜 모듈 2개로 확인하는 것:
  우선순위 순서, 경보 유실 → 재전송, ACK 유실 → 중복 제거 + 재회신, GUI로 UDP JSON 전달
"""
import json
import queue
import socket
import threading
import time

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # e22·protocol은 상위 modules/ 에 있음
from alert_rx import AlertRx
from alert_tx import AlertTx
from protocol import Alert


class FakeLora:
    """send()한 바이트가 상대의 recv()로 나옴. drop > 0이면 그만큼 송신을 버림 (무선 유실 흉내)."""

    def __init__(self):
        self.inbox: queue.Queue = queue.Queue()
        self.peer = None
        self.drop = 0

    def send(self, data: bytes) -> None:
        if self.drop:
            self.drop -= 1
            return
        self.peer.inbox.put(data)

    def recv(self) -> bytes:
        try:
            return self.inbox.get(timeout=0.005)
        except queue.Empty:
            return b""


def alert(level: int, track: int) -> Alert:
    return Alert(node_id=0, seq=0, track_id=track, level=level, stereo=True,
                 dist_m=10.0, speed_mps=1.0, tta_s=None, az_deg=0.0, el_deg=0.0)


tx_lora, rx_lora = FakeLora(), FakeLora()
tx_lora.peer, rx_lora.peer = rx_lora, tx_lora

gui = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
gui.bind(("127.0.0.1", 0))
gui.settimeout(1.0)

tx = AlertTx(tx_lora, node_id=3, ack_timeout=0.05, retries=2)
rx = AlertRx(rx_lora, gui.getsockname())
got: list[Alert] = []
stop = threading.Event()


def wait_got(n: int) -> None:
    """rx는 ACK를 보낸 뒤 목록에 추가하므로 flush() 직후엔 마지막 건이 아직 없을 수 있음."""
    t_end = time.monotonic() + 1.0
    while len(got) < n and time.monotonic() < t_end:
        time.sleep(0.005)


def rx_loop():
    while not stop.is_set():
        got.extend(rx.poll())


threading.Thread(target=rx_loop, daemon=True).start()

# 1) 시작 전에 넣어 두면 등급 높은 것부터 나가야 함 (같은 등급은 넣은 순서)
for lv, tr in [(1, 10), (1, 11), (3, 12), (2, 13)]:
    assert tx.submit(alert(lv, tr))
tx_lora.drop = 1      # 첫 경보의 첫 송신 유실 → 재전송
tx.start()
tx.flush()
wait_got(4)
assert [a.track_id for a in got] == [12, 13, 10, 11], [a.track_id for a in got]

# 2) ACK 유실 → 같은 seq 재전송 → 지휘소는 중복으로 걸러내고 다시 ACK
rx_lora.drop = 1
tx.submit(alert(2, 14))
tx.flush()
wait_got(5)
stop.set()
tx.close()

assert tx.stats == {"acked": 5, "failed": 0, "retries": 2, "dropped": 0}, tx.stats
assert rx.stats == {"alerts": 5, "dups": 1}, rx.stats
assert len({a.seq for a in got}) == 5 and all(a.node_id == 3 for a in got)

msgs = [json.loads(gui.recv(1024)) for _ in range(5)]
assert [m["track_id"] for m in msgs] == [12, 13, 10, 11, 14], msgs

# 3) 큐가 가득 차면 버리고 False
full = AlertTx(tx_lora, maxsize=1)
assert full.submit(alert(1, 1)) and not full.submit(alert(1, 2)) and full.stats["dropped"] == 1

print("test_alert.py 시험 모두 통과:", tx.stats, rx.stats)
