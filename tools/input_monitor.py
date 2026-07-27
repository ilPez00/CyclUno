#!/usr/bin/env python3
"""CyclUno input monitor — live joystick map + button press recorder.

Reads the v2 wire frames (cyclops_shared.h: AA 55 len16 type payload crc16)
from the Uno's USB serial and renders an ANSI dashboard:

  * joy2 position map (raw axes in APP mode, step pulses in AION mode)
  * button states with press counters (A/B only forwarded in APP mode)
  * MODE + STATUS telemetry, CRC error counter, scrolling event log

Usage:  python3 tools/input_monitor.py [--port /dev/ttyACM1] [--log FILE]

Opening the port pulses DTR and resets the Uno: keep hands off both
sticks for the first two seconds so center calibration lands true.
"""

import argparse
import struct
import sys
import time

import serial

MSG_INPUT_EVENT = 3
MSG_STATUS = 8

SRC_NAMES = {0: "JOY1", 1: "JOY2", 3: "BTN", 4: "MODE"}
JOY_CODES = {0: "step-x", 1: "step-y", 2: "raw-x", 3: "raw-y"}
BTN_NAMES = {0: "A", 1: "B", 2: "J2", 4: "MODE", 5: "X", 6: "Y"}

MAP_W, MAP_H = 21, 11          # joystick map grid (odd -> true center cell)
RAW_FULL = 512                 # ADC counts from center to rail
STEP_DECAY_S = 0.35            # how long a step pulse stays on the map
LOG_LINES = 8


def crc16_ccitt_false(data: bytes, seed: int = 0xFFFF) -> int:
    crc = seed
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else (crc << 1)
            crc &= 0xFFFF
    return crc


class FrameDecoder:
    """Streaming mirror of cyclops::FrameDecoder."""

    def __init__(self, on_frame):
        self.on_frame = on_frame
        self.crc_errors = 0
        self._reset()

    def _reset(self):
        self.state = "M1"
        self.length = 0
        self.buf = bytearray()
        self.crc_lo = 0

    def push(self, byte: int):
        st = self.state
        if st == "M1":
            if byte == 0xAA:
                self.state = "M2"
        elif st == "M2":
            self.state = "L1" if byte == 0x55 else ("M2" if byte == 0xAA else "M1")
        elif st == "L1":
            self.length = byte
            self.state = "L2"
        elif st == "L2":
            self.length |= byte << 8
            self.state = "T"
        elif st == "T":
            if self.length > 253:
                self._reset()
                return
            self.buf = bytearray([self.length & 0xFF, self.length >> 8, byte])
            self.state = "P" if self.length else "CR1"
        elif st == "P":
            self.buf.append(byte)
            if len(self.buf) - 3 >= self.length:
                self.state = "CR1"
        elif st == "CR1":
            self.crc_lo = byte
            self.state = "CR2"
        elif st == "CR2":
            crc_recv = self.crc_lo | (byte << 8)
            if crc_recv == crc16_ccitt_false(bytes(self.buf)):
                self.on_frame(self.buf[2], bytes(self.buf[3:]))
            else:
                self.crc_errors += 1
            self._reset()


class Dashboard:
    def __init__(self, log_path=None):
        self.raw = {"x": 0, "y": 0}                   # APP-mode joy2 raw
        self.step = {"x": 0, "y": 0}                  # AION-mode last step
        self.step_at = 0.0
        self.buttons = {n: {"down": False, "count": 0} for n in BTN_NAMES.values()}
        self.mode = "?"
        self.status = ""
        self.frames = 0
        self.events = []
        self.log_file = open(log_path, "w") if log_path else None

    def log(self, text):
        stamp = time.strftime("%H:%M:%S") + f".{int(time.time() % 1 * 1000):03d}"
        line = f"{stamp}  {text}"
        self.events.append(line)
        self.events = self.events[-LOG_LINES:]
        if self.log_file:
            self.log_file.write(line + "\n")
            self.log_file.flush()

    def on_frame(self, msg_type, payload):
        self.frames += 1
        if msg_type == MSG_STATUS:
            self.status = payload.decode("ascii", "replace")
            return
        if msg_type != MSG_INPUT_EVENT or len(payload) != 4:
            return
        src, code = payload[0], payload[1]
        (val,) = struct.unpack("<h", payload[2:4])

        if src == 4:  # MODE toggle
            self.mode = "APP" if val else "AION"
            self.log(f"MODE -> {self.mode}")
        elif src == 3:  # button
            name = BTN_NAMES.get(code, f"btn{code}")
            state = self.buttons.setdefault(name, {"down": False, "count": 0})
            state["down"] = bool(val)
            if val:
                state["count"] += 1
            self.log(f"BTN {name} {'DOWN' if val else 'up'}")
        elif src in (0, 1):  # joystick
            axis = "x" if code in (0, 2) else "y"
            if code in (2, 3):  # raw stream (APP)
                self.raw[axis] = val
            else:  # step (AION)
                self.step[axis] = val
                self.step_at = time.time()
                arrow = {("x", 1): ">", ("x", -1): "<",
                         ("y", 1): "v", ("y", -1): "^"}.get((axis, val), "?")
                self.log(f"{SRC_NAMES[src]} step {arrow}")

    def joystick_map(self):
        """Grid of joy2 position: raw dot in APP, decaying step pulse in AION."""
        cx, cy = MAP_W // 2, MAP_H // 2
        if self.mode == "APP":
            px = cx + round(self.raw["x"] / RAW_FULL * cx)
            py = cy + round(self.raw["y"] / RAW_FULL * cy)
        elif time.time() - self.step_at < STEP_DECAY_S:
            px = cx + self.step["x"] * cx // 2
            py = cy + self.step["y"] * cy // 2
        else:
            px, py = cx, cy
        px, py = max(0, min(MAP_W - 1, px)), max(0, min(MAP_H - 1, py))

        rows = []
        for y in range(MAP_H):
            row = ""
            for x in range(MAP_W):
                if (x, y) == (px, py):
                    row += "\x1b[1;32m@\x1b[0m"
                elif (x, y) == (cx, cy):
                    row += "+"
                elif x == cx or y == cy:
                    row += "\x1b[2m·\x1b[0m"
                else:
                    row += " "
            rows.append("|" + row + "|")
        return rows

    def render(self):
        out = ["\x1b[H\x1b[2J\x1b[1mCyclUno input monitor\x1b[0m   "
               f"mode: \x1b[1m{self.mode}\x1b[0m   frames: {self.frames}",
               f"status: {self.status or '(waiting for 1 Hz status frame)'}",
               ""]

        map_rows = self.joystick_map()
        btn_rows = ["  joy2 " + ("raw x=%+4d y=%+4d" % (self.raw["x"], self.raw["y"])
                    if self.mode == "APP" else "steps (AION)"), ""]
        for name in ("A", "B", "J2", "X", "Y", "MODE"):
            st = self.buttons[name]
            dot = "\x1b[1;31m●\x1b[0m" if st["down"] else "○"
            note = ""
            if name in ("A", "B"):
                note = "  (APP mode only)" if self.mode != "APP" else ""
            btn_rows.append(f"  {dot} {name:<4} presses: {st['count']:3d}{note}")

        top = "+" + "-" * MAP_W + "+"
        left = [top] + map_rows + [top]
        for i in range(max(len(left), len(btn_rows))):
            l = left[i] if i < len(left) else " " * (MAP_W + 2)
            r = btn_rows[i] if i < len(btn_rows) else ""
            out.append(f"{l}   {r}")

        out += ["", "\x1b[2m-- events " + "-" * 30 + "\x1b[0m"]
        out += self.events or ["  (move joy2 / press X, Y, J2 — A/B/joy1 stay local in AION)"]
        out += ["", "\x1b[2mCtrl-C to quit\x1b[0m"]
        sys.stdout.write("\n".join(out) + "\n")
        sys.stdout.flush()


def main():
    ap = argparse.ArgumentParser(description="CyclUno joystick map + button recorder")
    ap.add_argument("--port", default="/dev/ttyACM1")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--log", help="also append events to this file")
    args = ap.parse_args()

    dash = Dashboard(args.log)
    dec = FrameDecoder(dash.on_frame)

    with serial.Serial(args.port, args.baud, timeout=0.05) as port:
        dash.log(f"opened {args.port} (board resets now — hands off sticks)")
        last_draw = 0.0
        try:
            while True:
                for byte in port.read(256):
                    dec.push(byte)
                now = time.time()
                if now - last_draw > 0.05:
                    dash.render()
                    if dec.crc_errors:
                        sys.stdout.write(f"CRC errors: {dec.crc_errors}\n")
                    last_draw = now
        except KeyboardInterrupt:
            pass
    total = sum(b["count"] for b in dash.buttons.values())
    print(f"\ndone: {dash.frames} frames, {total} button presses, "
          f"{dec.crc_errors} CRC errors")


if __name__ == "__main__":
    main()
