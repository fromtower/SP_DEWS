from RPLCD.i2c import CharLCD


class LCD:
    """I2C 16×2 LCD (PCF8574, 0x27). HD44780 문자셋이라 한글 불가 → ASCII만 쓸 것."""

    def __init__(self):
        self._lcd = CharLCD(
            i2c_expander='PCF8574',
            address=0x27,
            port=1,
            cols=16,
            rows=2,
            dotsize=8,
            charmap='A02',
            auto_linebreaks=True,
            backlight_enabled=True,
        )

    def write(self, lines: list[str]) -> None:
        if len(lines) > 2:
            print("LCD: 2줄 초과, 앞 2줄만 표시")
        try:
            for row, s in enumerate(lines[:2]):
                self._lcd.cursor_pos = (row, 0)
                self._lcd.write_string(s[:16].ljust(16))   # 16자로 채워 이전 글자가 남지 않게
        except OSError as e:                               # I2C 끊김 등은 알리고 계속
            print(f"LCD 쓰기 실패: {e}")
