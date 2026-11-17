"""
rssi_check.py — E22 무선부 살아 있는지 확인 (채널 잡음 세기 측정, 패킷 해석 없음)

  1) M1 = 3.3V 로 두고   python rssi_check.py --port COM17 --enable
     (잡음 RSSI 기능을 임시로 켬. USB를 뽑으면 꺼짐 → 이후 USB 뽑지 말 것)
  2) M1 = GND 로 옮기고  python rssi_check.py --port COM17
     → 0.2초마다 현재 채널 세기(dBm) 출력
  3) 다른 모듈에서 test_send.py --raw 실행 → 1초마다 숫자가 크게 튀면 정상
     '마지막 수신 패킷'이 바뀌면 모듈이 패킷을 풀어낸 것 (그런데도 PC에 안 오면 TXD→USB 경로 문제)

  평소 -100 dBm 근처, 1~3 m 거리 송신 시 -30 ~ -70 dBm 정도로 올라가는 게 보통
"""
import argparse
import time

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # e22·protocol은 상위 modules/ 에 있음
from e22 import E22

ap = argparse.ArgumentParser()
ap.add_argument("--port", required=True)
ap.add_argument("--enable", action="store_true", help="CONFIG 모드(M1=3.3V)에서 잡음 RSSI 켜기")
args = ap.parse_args()

# e22.py --read 와 같은 경로로 보냄 (그쪽은 동작 확인됨)
lora = E22(args.port, use_gpio=False)

if args.enable:
    cmd = bytes([0xC2, 0x04, 0x01, 0x23])      # REG1: 240 B, 잡음 RSSI 켬, 10 dBm (C2 = 임시)
    r = lora._config_cmd(cmd, 4)
    print("켜짐" if r == bytes([0xC1]) + cmd[1:] else f"실패: {r.hex(' ') or '응답 없음'}")
    raise SystemExit

lora.close()
print("측정 중... (Ctrl+C로 종료)")
try:
    while True:
        # shortcut: 포트를 연 직후 첫 명령에만 응답함(원인 미확인) → 측정마다 다시 엶. 원인 찾으면 한 번만 열기
        with E22(args.port, use_gpio=False) as lora:
            # 00 = 지금 채널 잡음, 01 = 마지막으로 풀어낸 패킷의 세기 (0이면 아직 한 번도 못 풂)
            lora.ser.write(bytes([0xC0, 0xC1, 0xC2, 0xC3, 0x00, 0x02]))
            r = lora._read_exact(5, 1.0)
        if len(r) == 5 and r[:3] == bytes([0xC1, 0x00, 0x02]):
            dbm = -(256 - r[3])
            last = "없음" if r[4] == 0 else f"{-(256 - r[4])} dBm"
            print(f"{dbm:5d} dBm {'#' * max(0, (dbm + 110) // 3):<34} 마지막 수신 패킷: {last}")
        else:
            print(f"응답 없음 ({r.hex(' ')}) — --enable 먼저, M1=GND 확인")
        time.sleep(0.1)
except KeyboardInterrupt:
    pass
