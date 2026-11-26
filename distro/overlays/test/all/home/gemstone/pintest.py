#!/usr/bin/env python3

import argparse
import atexit
import base64
import glob
import json
import mmap
import os
import re
import select
import socket
import struct
import sys
import termios
import time

MAIN_PAD, MCU_PAD = 0xF4000, 0x4084000
PINS_ALL = [
    ( 3, MCU_PAD,  0x048, 0x4201000, 18, "MCU_I2C0_SDA (pulled up)"),
    ( 5, MCU_PAD,  0x044, 0x4201000, 17, "MCU_I2C0_SCL (pulled up)"),
    ( 7, MAIN_PAD, 0x09C, 0x0600000, 38, "GPIO0_38"),
    ( 8, MAIN_PAD, 0x1B0, 0x0601000, 14, "UART1 TX (control channel)"),
    (10, MAIN_PAD, 0x1AC, 0x0601000, 13, "UART1 RX (control channel)"),
    (11, MAIN_PAD, 0x198, 0x0601000,  8, "GPIO1_8"),
    (12, MAIN_PAD, 0x1A4, 0x0601000, 11, "GPIO1_11"),
    (13, MAIN_PAD, 0x088, 0x0600000, 33, "GPIO0_33"),
    (15, MAIN_PAD, 0x0A8, 0x0600000, 41, "GPIO0_41"),
    (16, MCU_PAD,  0x01C, 0x4201000,  7, "MCU_GPIO0_7"),
    (18, MCU_PAD,  0x028, 0x4201000, 10, "MCU_GPIO0_10"),
    (19, MCU_PAD,  0x00C, 0x4201000,  3, "MCU_GPIO0_3"),
    (21, MCU_PAD,  0x010, 0x4201000,  4, "MCU_GPIO0_4"),
    (22, MAIN_PAD, 0x0AC, 0x0600000, 42, "GPIO0_42"),
    (23, MCU_PAD,  0x008, 0x4201000,  2, "MCU_GPIO0_2"),
    (24, MCU_PAD,  0x000, 0x4201000,  0, "MCU_GPIO0_0"),
    (26, MCU_PAD,  0x024, 0x4201000,  9, "MCU_GPIO0_9"),
    (29, MAIN_PAD, 0x1B4, 0x0601000, 15, "GPIO1_15"),
    (31, MAIN_PAD, 0x1BC, 0x0601000, 17, "GPIO1_17"),
    (32, MAIN_PAD, 0x1B8, 0x0601000, 16, "GPIO1_16"),
    (33, MAIN_PAD, 0x1C0, 0x0601000, 18, "GPIO1_18"),
    (35, MAIN_PAD, 0x1A8, 0x0601000, 12, "GPIO1_12"),
    (36, MAIN_PAD, 0x194, 0x0601000,  7, "GPIO1_7"),
    (37, MAIN_PAD, 0x094, 0x0600000, 36, "GPIO0_36"),
    (38, MAIN_PAD, 0x1A0, 0x0601000, 10, "GPIO1_10"),
    (40, MAIN_PAD, 0x19C, 0x0601000,  9, "GPIO1_9"),
]
CONTROL_PINS = {8, 10}
PMIC_PINS = {27, 28}
SKIP_PINS = set()
PINS = [p for p in PINS_ALL if p[0] not in CONTROL_PINS | SKIP_PINS]
UART_DEV = "/dev/ttyS3"
CAN_IF = "can0"
CAN_BITRATE = 500_000
CAN_ID_MASTER = 0x123
CAN_ID_SLAVE = 0x321
REPORT = "/home/gemstone/pintest-report.txt"
REPORT_JSON = "/home/gemstone/pintest-report.json"
API_SOCK = "/run/pintest.sock"     # the API asks the slave for a fresh test here
MASTER_IDLE_TIMEOUT = 5            # s without any master command => master considered absent
RUN_TIMEOUT = 60                   # s of master silence during a requested test => test failed
POLL_INTERVAL = 0.5                # s between the idle master's POLLs


class Mem:
    def __init__(self, pins):
        """Open /dev/mem to drive the given header pins through padcfg and GPIO registers."""
        self.pins = pins
        self.fd = os.open("/dev/mem", os.O_RDWR | os.O_SYNC)
        self.maps, self.saved = {}, {}

    def _m(self, base):
        """Return a cached 4 KiB mapping of the register block at base."""
        if base not in self.maps:
            self.maps[base] = mmap.mmap(self.fd, 0x1000, offset=base)
        return self.maps[base]

    def r32(self, base, off):
        """Read a 32-bit register."""
        return struct.unpack_from("<I", self._m(base), off)[0]

    def w32(self, base, off, val):
        """Write a 32-bit register."""
        struct.pack_into("<I", self._m(base), off, val)

    def _gpio(self, p, reg):
        """Return (base, offset, bit) of a pin's GPIO register (reg: 0=DIR 1=OUT 2=SET 3=CLR 4=IN)."""
        bank, bit_ = p[4] // 32, p[4] % 32
        return p[3], 0x10 + 0x28 * bank + 4 * reg, bit_

    def setup(self):
        """Mux the pins as pulled-down GPIO inputs and enable the IMU so it does not clamp pin 21."""
        GB = 0x4201000
        if not hasattr(self, "_imu_dir"):
            self._imu_dir = self.r32(GB, 0x10)
            self._imu_out = self.r32(GB, 0x14)
        self.w32(GB, 0x18, 1 << 12)
        self.w32(GB, 0x10, self.r32(GB, 0x10) & ~(1 << 12))
        for p in self.pins:
            self.saved.setdefault((p[1], p[2]), self.r32(p[1], p[2]))
            self.w32(p[1], p[2], 0x40007)
            gb, go, b = self._gpio(p, 0)
            self.w32(gb, go, self.r32(gb, go) | (1 << b))
        time.sleep(0.1)

    def restore(self):
        """Restore the saved pinmux, switch all pins back to input and restore IMU_EN."""
        for (base, off), val in self.saved.items():
            self.w32(base, off, val)
        for p in self.pins:
            gb, go, b = self._gpio(p, 0)
            self.w32(gb, go, self.r32(gb, go) | (1 << b))
        GB = 0x4201000
        if hasattr(self, "_imu_dir"):
            self.w32(GB, 0x14, self._imu_out)
            self.w32(GB, 0x10, self._imu_dir)

    def read_all(self):
        """Read all pins into a bitmask where bit i is pins[i]."""
        bits = 0
        for i, p in enumerate(self.pins):
            gb, go, b = self._gpio(p, 4)
            if self.r32(gb, go) & (1 << b):
                bits |= 1 << i
        return bits

    def drive(self, idx, val):
        """Make pin idx an output and drive it to val."""
        p = self.pins[idx]
        gb, go, b = self._gpio(p, 2 if val else 3)
        self.w32(gb, go, 1 << b)
        db, do, dbit = self._gpio(p, 0)
        self.w32(db, do, self.r32(db, do) & ~(1 << dbit))

    def release(self, idx):
        """Switch pin idx back to input."""
        db, do, dbit = self._gpio(self.pins[idx], 0)
        self.w32(db, do, self.r32(db, do) | (1 << dbit))


def _led_write(led, trigger, ms=None, bright=None):
    """Set an LED's trigger and, optionally, its blink delay and brightness."""
    try:
        open(led + "/trigger", "w").write(trigger)
        if ms is not None:
            open(led + "/delay_on", "w").write(ms)
            open(led + "/delay_off", "w").write(ms)
        if bright is not None:
            open(led + "/brightness", "w").write(str(bright))
    except OSError:
        pass


def _user_leds():
    """Return the (green, red) user LED paths; red is None when only a single LED exists."""
    g, r = "/sys/class/leds/GREEN", "/sys/class/leds/RED"
    if os.path.isdir(g) and os.path.isdir(r):
        return g, r
    cands = [d for d in glob.glob("/sys/class/leds/*") if "act" in d.lower()] \
        or sorted(glob.glob("/sys/class/leds/*"))
    return (cands[0], None) if cands else (None, None)


def _read_text(path):
    """Return the stripped contents of a text file, or "?" if it cannot be read."""
    try:
        return open(path).read().replace("\x00", "").strip()
    except OSError:
        return "?"


def board_info():
    """Return the board identity: hostname, MAC addresses, machine id and serial number."""
    eth = _read_text("/sys/class/net/eth0/address")
    wlan = _read_text("/sys/class/net/wlan0/address")
    mid = _read_text("/etc/machine-id")
    serial = _read_text("/proc/device-tree/serial-number")
    return (f"host={os.uname().nodename} eth0-mac={eth} wlan0-mac={wlan} "
            f"machine-id={mid} serial-no={serial}")


def led_set(mode):
    """Show a state on the user LEDs: ready (slow green), busy (yellow blink), fail (fast red), ok (solid green)."""
    g, r = _user_leds()
    if g is None:
        return
    if r is None:
        if mode == "ok":
            _led_write(g, "none", bright=255)
        else:
            _led_write(g, "timer", ms={"ready": "500", "busy": "250", "fail": "100"}[mode])
        return
    if mode == "ready":
        _led_write(g, "timer", ms="500")
        _led_write(r, "none", bright=0)
    elif mode == "busy":
        _led_write(g, "timer", ms="250")
        _led_write(r, "timer", ms="250")
    elif mode == "fail":
        _led_write(g, "none", bright=0)
        _led_write(r, "timer", ms="100")
    elif mode == "ok":
        _led_write(g, "none", bright=255)
        _led_write(r, "none", bright=0)


def led_restore():
    """Turn the user LEDs off and give the ACT LED its heartbeat trigger back."""
    g, r = _user_leds()
    if r is not None:
        _led_write(g, "none", bright=0)
        _led_write(r, "none", bright=0)
    for d in glob.glob("/sys/class/leds/*"):
        if "act" in d.lower():
            _led_write(d, "heartbeat")


class Uart:
    def __init__(self, dev):
        """Open the UART in raw 115200 8N1 mode after stopping any getty on it."""
        os.system("systemctl stop serial-getty@ttyS3.service "
                  "serial-getty@ttyAMA0.service 2>/dev/null")
        self.fd = os.open(dev, os.O_RDWR | os.O_NOCTTY)
        a = termios.tcgetattr(self.fd)
        a[0] = a[1] = a[3] = 0
        a[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
        a[4] = a[5] = termios.B115200
        a[6][termios.VMIN], a[6][termios.VTIME] = 0, 1
        termios.tcsetattr(self.fd, termios.TCSANOW, a)
        termios.tcflush(self.fd, termios.TCIOFLUSH)
        self.buf = b""

    def send(self, line):
        """Send one protocol line."""
        os.write(self.fd, (line + "\n").encode())

    def readline(self, timeout):
        """Return the next received line, or None after timeout seconds."""
        end = time.time() + timeout
        while time.time() < end:
            if b"\n" in self.buf:
                line, self.buf = self.buf.split(b"\n", 1)
                return line.decode(errors="replace").strip()
            self.buf += os.read(self.fd, 4096)
        return None

    def read_lines(self):
        """Read what has arrived (call when the fd is readable) and return the complete lines."""
        self.buf += os.read(self.fd, 4096)
        *lines, self.buf = self.buf.split(b"\n")
        return [ln.decode(errors="replace").strip() for ln in lines]

    def flush_input(self):
        """Drop any unread input so a late reply cannot be taken as the answer to the next command."""
        termios.tcflush(self.fd, termios.TCIFLUSH)
        self.buf = b""


class ApiRequests:
    """Test requests from the local API (unix socket), handed to the master when it sends POLL.

    Every caller gets the result of a test that started after its request: requests that arrive
    while a test is already running wait for the next one. Replies are one line: "OK <json>" or
    "ERR <message>".
    """

    def __init__(self, path=API_SOCK):
        """Listen on the unix socket the API connects to."""
        if os.path.exists(path):
            os.unlink(path)
        self.srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.srv.bind(path)
        os.chmod(path, 0o660)
        self.srv.listen(8)
        self.srv.setblocking(False)
        self.waiting, self.in_test = [], []
        self.test_active = False
        self.last_master = 0.0

    def accept(self):
        """Take a new API request, or refuse it at once if the master is not there."""
        try:
            conn, _ = self.srv.accept()
        except BlockingIOError:
            return
        conn.settimeout(2)
        try:
            req = conn.recv(64)
        except OSError:
            conn.close()
            return
        if not req.startswith(b"RUN"):
            self._reply(conn, b"ERR unknown request")
            return
        idle = time.time() - self.last_master
        if idle > MASTER_IDLE_TIMEOUT:
            self._reply(conn, b"ERR master not connected (no command from the master for "
                        + (b"ever" if self.last_master == 0 else b"%.0f s" % idle)
                        + b") - is pintest-master.service running and the pin 8<->10 link ok?")
            return
        self.waiting.append(conn)
        print("[slave] test requested via API, waiting for the master to start it")

    def poll(self):
        """Answer the master's POLL: True when it should run a test now."""
        if self.waiting:
            self.in_test += self.waiting
            self.waiting = []
            self.test_active = True
        return self.test_active

    def finish(self, line):
        """Send the result line to everyone waiting on the current test."""
        for conn in self.in_test:
            self._reply(conn, line)
        self.in_test = []
        self.test_active = False

    def check(self):
        """Fail requests whose master went silent."""
        idle = time.time() - self.last_master
        if self.test_active and idle > RUN_TIMEOUT:
            print("[slave] master went silent during the requested test")
            self.finish(b"ERR master stopped responding during the test")
        if self.waiting and idle > MASTER_IDLE_TIMEOUT and not self.test_active:
            for conn in self.waiting:
                self._reply(conn, b"ERR master disconnected before the test started")
            self.waiting = []

    @staticmethod
    def _reply(conn, line):
        """Send one reply line and close the connection, ignoring a caller that already left."""
        try:
            conn.sendall(line + b"\n")
        except OSError:
            pass
        conn.close()


def run_slave(args):
    """Serve master commands received over the UART, and API test requests, until stopped."""
    mem = Mem(PINS)
    uart = Uart(args.uart)
    api = ApiRequests()
    atexit.register(mem.restore)
    atexit.register(led_restore)
    led_set("ready")
    print(f"[slave] ready — listening on {args.uart} and {API_SOCK}, waiting for master...")
    while True:
        readable, _, _ = select.select([uart.fd, api.srv], [], [], 0.5)
        if api.srv in readable:
            api.accept()
        lines = uart.read_lines() if uart.fd in readable else []
        if lines:
            api.last_master = time.time()
        api.check()
        for line in lines:
            if line:
                _slave_command(line, uart, mem, api)


def _slave_command(line, uart, mem, api):
    """Execute one master command and send the reply."""
    t = line.split()
    try:
        c = t[0].upper()
        if c == "POLL":
            uart.send("#>Q 1" if api.poll() else "#>Q 0")
        elif c == "REPORT":
            data = base64.b64decode(t[1])
            json.loads(data)
            tmp = REPORT_JSON + ".tmp"
            with open(tmp, "wb") as fp:
                fp.write(data)
            os.replace(tmp, REPORT_JSON)
            uart.send(f"#>S {len(data):X}")
            if api.test_active:
                api.finish(b"OK " + data)
        elif c == "FAIL":
            print("[slave] master reported a test error: " + line[5:])
            uart.send("#>OK")
            if api.test_active:
                api.finish(b"ERR test error on the master: " + line[5:].encode())
        elif c == "PING":
            uart.send("#>PONG")
        elif c == "INFO":
            uart.send("#>I " + board_info())
        elif c == "SETUP":
            mem.setup()
            led_set("busy")
            print("[slave] test started: pins switched to GPIO input")
            uart.send("#>OK")
        elif c == "READ":
            uart.send("#>R %07X" % mem.read_all())
        elif c == "DRIVE":
            mem.drive(int(t[1]), int(t[2]))
            uart.send("#>OK")
        elif c == "RELEASE":
            mem.release(int(t[1]))
            uart.send("#>OK")
        elif c == "RESTORE":
            mem.restore()
            led_set("ready")
            print("[slave] test finished: pinmux restored")
            uart.send("#>OK")
        elif c == "ECHO":
            uart.send("#>E " + line[5:])
        elif c == "ETHCFG":
            os.system(f"ip addr replace {t[1]} dev eth0 && ip link set eth0 up")
            uart.send("#>OK")
        elif c == "ETHRECV":
            import socket as so
            srv = so.socket(); srv.setsockopt(so.SOL_SOCKET, so.SO_REUSEADDR, 1)
            srv.bind(("", int(t[1]))); srv.listen(1); srv.settimeout(20)
            uart.send("#>OK")
            conn2, _ = srv.accept()
            n, want = 0, int(t[2])
            while n < want:
                b = conn2.recv(1 << 20)
                if not b:
                    break
                n += len(b)
            conn2.close(); srv.close()
            uart.send(f"#>R {n:X}")
        elif c == "ETHSEND":
            import socket as so
            cl = so.socket(); cl.settimeout(20); cl.connect((t[1], int(t[2])))
            block = b"\x55" * (1 << 20)
            remaining = int(t[3])
            while remaining > 0:
                cl.sendall(block[:min(len(block), remaining)])
                remaining -= len(block)
            cl.close()
            uart.send("#>OK")
        elif c == "SAVEREPORT":
            import socket as so
            srv = so.socket(); srv.setsockopt(so.SOL_SOCKET, so.SO_REUSEADDR, 1)
            srv.bind(("", int(t[1]))); srv.listen(1); srv.settimeout(20)
            uart.send("#>OK")
            conn2, _ = srv.accept()
            data, want = b"", int(t[2])
            while len(data) < want:
                b = conn2.recv(1 << 20)
                if not b:
                    break
                data += b
            conn2.close(); srv.close()
            with open(REPORT_JSON, "wb") as fp:
                fp.write(data)
            uart.send(f"#>S {len(data):X}")
        elif c == "CANTEST":
            bitrate = int(t[1]) if len(t) > 1 else CAN_BITRATE
            if not os.path.exists(f"/sys/class/net/{CAN_IF}"):
                uart.send("#>C ERR can0 missing (no driver/hardware)")
            elif not _can_open(bitrate):
                uart.send("#>C ERR can0 could not be brought up")
            else:
                try:
                    cs = _can_socket()
                    _can_send(cs, CAN_ID_SLAVE, b"SLAVEOK1")
                    data = _can_recv(cs, CAN_ID_MASTER, 3.0)
                    cs.close()
                    if data is not None:
                        uart.send("#>C OK " + data.decode(errors="replace"))
                    else:
                        uart.send("#>C TIMEOUT")
                except OSError as e:
                    uart.send(f"#>C ERR {e}")
        elif c == "LED":
            led_set(t[1])
            uart.send("#>OK")
        elif c == "SAY":
            print("[master says] " + line[4:])
            uart.send("#>OK")
        else:
            uart.send("#>ERR unknown: " + c)
    except Exception as e:
        uart.send("#>ERR " + repr(e))


RESP_RE = re.compile(r"#>(\S+)(?:\s+(.*))?")


class Slave:
    def __init__(self, uart):
        """Use the UART as the command channel to the slave board."""
        self.uart = uart

    def cmd(self, line, timeout=3.0, retries=2):
        """Send a command and return the slave's (tag, payload) response, retrying on timeout."""
        for _ in range(retries + 1):
            self.uart.send(line)
            end = time.time() + timeout
            while time.time() < end:
                resp = self.uart.readline(timeout=end - time.time())
                if resp is None:
                    break
                m = RESP_RE.match(resp)
                if m:
                    if m.group(1) == "ERR":
                        raise RuntimeError(f"slave: '{line}' -> {resp}")
                    return m.group(1), m.group(2)
        raise RuntimeError(f"slave did not respond to '{line}' — "
                           f"check the UART link (pin 8↔10) and the slave")

    def read_pins(self):
        """Read the slave's pin bitmask."""
        tag, val = self.cmd("READ")
        return int(val, 16)


def bit(w, i):
    """Return bit i of w."""
    return (w >> i) & 1


def analyze(results, pins):
    """Classify each pin as OK, OPEN, SHORT or ONE-WAY from the walking-1/0 results and find its peer pin."""
    n = len(pins)
    header_pins = [p[0] for p in pins]
    F, near_short = {}, {}
    for tag in ("A→B", "B→A"):
        F[tag], near_short[tag] = {}, {}
        bs = results[tag]["base_src"]
        for i in range(n):
            r = results[tag]["pins"][i]
            F[tag][i] = {j for j in range(n)
                         if bit(r["far1"], j) == 1 and bit(r["far0"], j) == 0}
            near_short[tag][i] = {j for j in range(n) if j != i and
                                  (bit(r["near1"], j) != bit(bs, j) or
                                   bit(r["near0"], j) != bit(bs, j))}
    verdicts, peers = {}, {}
    for i in range(n):
        pin = header_pins[i]
        ab = F["A→B"][i]
        ba = {j for j in range(n) if i in F["B→A"][j]}
        cand = ab | ba
        problems = []
        for tag, board in (("A→B", "master"), ("B→A", "slave")):
            if near_short[tag][i]:
                lst = ", ".join(f"pin {header_pins[j]}" for j in sorted(near_short[tag][i]))
                problems.append(f"possible short on {board} side: {lst}")
        if not cand:
            peers[pin] = None
            verdicts[pin] = ("OPEN", "; ".join(
                ["signal does not reach the other side in either direction"] + problems))
        elif len(cand) == 1:
            j = next(iter(cand))
            peers[pin] = header_pins[j]
            if (j in ab) and (j in ba) and not problems:
                verdicts[pin] = ("OK", "")
            elif (j in ab) and (j in ba):
                verdicts[pin] = ("SHORT", "; ".join(problems))
            else:
                direction = "master→slave" if j in ab else "slave→master"
                problems.append(f"only the {direction} direction works")
                verdicts[pin] = ("ONE-WAY", "; ".join(problems))
        else:
            peers[pin] = sorted(header_pins[j] for j in cand)
            lst = ", ".join(f"pin {header_pins[j]}" for j in sorted(cand))
            verdicts[pin] = ("SHORT", "; ".join(
                [f"followed by more than one peer pin: {lst}"] + problems))
    return verdicts, peers


def measure_uart_speed(slave):
    """Measure the control channel's round trip (ms/command) and effective rate (kbit/s) with 20 echoes."""
    payload = "A" * 200
    n = 20
    t0 = time.time()
    for _ in range(n):
        tag, echoed = slave.cmd("ECHO " + payload, timeout=5)
        if echoed != payload:
            return None, None
    dt = time.time() - t0
    nbytes = n * (len(payload) + 10) * 2
    return (dt / n) * 1000.0, nbytes * 8 / dt / 1000.0


def _can_open(bitrate=CAN_BITRATE):
    """Bring can0 up at the given bitrate."""
    os.system(f"ip link set {CAN_IF} down 2>/dev/null")
    rc = os.system(f"ip link set {CAN_IF} type can bitrate {bitrate} 2>/dev/null")
    os.system(f"ip link set {CAN_IF} up 2>/dev/null")
    return rc == 0


def _can_socket():
    """Open a raw CAN socket on can0 with loopback disabled."""
    import socket as so
    s = so.socket(so.PF_CAN, so.SOCK_RAW, so.CAN_RAW)
    s.setsockopt(so.SOL_CAN_RAW, so.CAN_RAW_LOOPBACK, struct.pack("i", 0))
    s.bind((CAN_IF,))
    return s


def _can_send(s, can_id, data):
    """Send one CAN frame."""
    frame = struct.pack("=IB3x8s", can_id, len(data), data.ljust(8, b"\x00"))
    s.send(frame)


def _can_recv(s, expected_id, timeout=3.0):
    """Return the payload of the next frame with expected_id, or None on timeout."""
    s.settimeout(timeout)
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            frame = s.recv(16)
        except OSError:
            return None
        can_id, dlc, data = struct.unpack("=IB3x8s", frame)
        if (can_id & 0x1FFFFFFF) == expected_id:
            return data[:dlc]
    return None


def can_test(slave, bitrate=CAN_BITRATE):
    """Test the CAN bus between the boards in both directions; return (report lines, JSON data)."""
    if not os.path.exists(f"/sys/class/net/{CAN_IF}"):
        return (["- CAN Bus    : can0 missing (no driver/hardware) — skipped."],
                {"result": "SKIPPED", "detail": "can0 missing (no driver/hardware)"})
    if not _can_open(bitrate):
        detail = f"can0 could not be brought up (bitrate {bitrate})"
        return ([f"- CAN Bus    : {detail} — check cable/transceiver."],
                {"result": "FAIL", "detail": detail})
    try:
        s = _can_socket()
    except OSError as e:
        return ([f"- CAN Bus    : could not open socket: {e}"],
                {"result": "FAIL", "detail": f"could not open socket: {e}"})
    slave.uart.send(f"CANTEST {bitrate}")
    time.sleep(0.4)
    _can_send(s, CAN_ID_MASTER, b"MASTER01")
    data_from_slave = _can_recv(s, CAN_ID_SLAVE, 3.0)
    s.close()
    response = _wait_response(slave, 5)
    if response:
        m = RESP_RE.match(response)
        slave_result = (m.group(2) or "") if m and m.group(1) == "C" else "unexpected response"
    else:
        slave_result = "no response (timeout)"
    lines = []
    slave_to_master_ok = data_from_slave is not None
    if slave_to_master_ok:
        lines.append(f"- CAN Bus    : master<-slave OK (received: {data_from_slave.decode(errors='replace')}, "
                     f"bitrate {bitrate})")
    else:
        lines.append("- CAN Bus    : master<-slave TIMEOUT — check cable/CANH-CANL/termination.")
    master_to_slave_ok = slave_result.startswith("OK")
    if master_to_slave_ok:
        lines.append(f"- CAN Bus    : master->slave OK (confirmed by slave: {slave_result})")
    else:
        lines.append(f"- CAN Bus    : master->slave FAILED ({slave_result})")
    data = {
        "result": "OK" if (master_to_slave_ok and slave_to_master_ok) else "FAIL",
        "bitrate": bitrate,
        "master_to_slave": "OK" if master_to_slave_ok else "FAIL",
        "slave_to_master": "OK" if slave_to_master_ok else "TIMEOUT",
    }
    return lines, data


def eth_test(slave):
    """Test the direct Ethernet link (ping and TCP throughput both ways); return (report lines, JSON data)."""
    MIP, SIP, PORT, NBYTE = "10.77.0.1", "10.77.0.2", 5599, 50 * (1 << 20)
    try:
        carrier = open("/sys/class/net/eth0/carrier").read().strip() == "1"
    except OSError:
        carrier = False
    if not carrier:
        return (["- Ethernet   : cable not connected (no eth0 carrier) — skipped."],
                {"result": "SKIPPED", "detail": "cable not connected (no eth0 carrier)"})
    os.system(f"ip addr replace {MIP}/24 dev eth0 && ip link set eth0 up")
    slave.cmd(f"ETHCFG {SIP}/24", timeout=10)
    time.sleep(1)
    p = os.popen(f"ping -c3 -i0.2 -W2 {SIP} 2>/dev/null | tail -1").read()
    m = re.search(r"= [\d.]+/([\d.]+)/", p)
    if not m:
        detail = f"link is up but {SIP} does not answer ping"
        return ([f"- Ethernet   : {detail} — check cable/configuration."],
                {"result": "FAIL", "detail": detail})
    rtt = float(m.group(1))
    lines = [f"- Ethernet   : direct link OK ({MIP} <-> {SIP}), ping RTT avg {rtt:.2f} ms"]
    import socket as so
    slave.cmd(f"ETHRECV {PORT} {NBYTE}", timeout=10)
    cl = so.socket(); cl.settimeout(20); cl.connect((SIP, PORT))
    block = b"\xaa" * (1 << 20)
    t0 = time.time()
    remaining = NBYTE
    while remaining > 0:
        cl.sendall(block[:min(len(block), remaining)])
        remaining -= 1 << 20
    cl.close()
    _wait_response(slave, 25)
    elapsed_m2s = time.time() - t0
    rate_m2s = NBYTE * 8 / elapsed_m2s / 1e6
    lines.append(f"- Ethernet   : TCP master->slave  {rate_m2s:.0f} Mbit/s "
                 f"({NBYTE >> 20} MB / {elapsed_m2s:.2f} s)")
    srv = so.socket(); srv.setsockopt(so.SOL_SOCKET, so.SO_REUSEADDR, 1)
    srv.bind(("", PORT)); srv.listen(1); srv.settimeout(20)
    slave.uart.send(f"ETHSEND {MIP} {PORT} {NBYTE}")
    conn2, _ = srv.accept()
    t0 = time.time()
    n = 0
    while n < NBYTE:
        b = conn2.recv(1 << 20)
        if not b:
            break
        n += len(b)
    elapsed_s2m = time.time() - t0
    conn2.close(); srv.close()
    _wait_response(slave, 10)
    rate_s2m = n * 8 / elapsed_s2m / 1e6
    lines.append(f"- Ethernet   : TCP slave->master  {rate_s2m:.0f} Mbit/s "
                 f"({n >> 20} MB / {elapsed_s2m:.2f} s)")
    data = {
        "result": "OK",
        "ping_ms": round(rtt, 2),
        "tcp_master_to_slave_mbps": round(rate_m2s),
        "tcp_slave_to_master_mbps": round(rate_s2m),
    }
    return lines, data


def _wait_response(slave, seconds):
    """Return the next protocol response from the slave, or None after the given seconds."""
    deadline = time.time() + seconds
    while time.time() < deadline:
        line = slave.uart.readline(timeout=max(0.1, deadline - time.time()))
        if line and RESP_RE.match(line):
            return line
    return None


def send_report_to_slave(slave, json_bytes):
    """Send the JSON report over the UART control channel so the slave saves it to REPORT_JSON
    (and hands it to the API caller waiting for this test). Works even when Ethernet is down."""
    tag, _ = slave.cmd("REPORT " + base64.b64encode(json_bytes).decode(), timeout=10, retries=1)
    if tag != "S":
        raise RuntimeError(f"unexpected reply to REPORT: {tag}")


def run_master(args):
    """Run the pin, Ethernet and CAN tests against the slave, then run them again whenever
    the slave's API asks for a fresh test (unless --once)."""
    mem = Mem(PINS)
    uart = Uart(args.uart)
    slave = Slave(uart)
    atexit.register(mem.restore)
    atexit.register(led_restore)
    led_set("busy")

    print(f"[master] looking for slave ({args.uart}, via pin 8↔10)...")
    for attempt in range(90):
        try:
            slave.cmd("PING", timeout=2, retries=0)
            break
        except RuntimeError:
            print(f"  attempt {attempt + 1}/90 — is the slave running?")
    else:
        led_set("fail")
        sys.exit("[master] slave not found. Start the slave first; "
                 "check the pin 8↔10 wiring.")
    print("[master] slave found ✓  (pins 8 and 10 verified as well: UART works)")
    _master_test_safely(args, mem, slave)
    if args.once:
        return
    print("[master] waiting for test requests from the slave's API (GET /pintest)...")
    slave_lost = False
    while True:
        try:
            uart.flush_input()
            tag, val = slave.cmd("POLL", timeout=1.0, retries=0)
        except RuntimeError as e:
            if not slave_lost:
                print(f"[master] slave not answering POLL ({e}); retrying...")
                slave_lost = True
            time.sleep(1)
            continue
        if slave_lost:
            print("[master] slave is answering again")
            slave_lost = False
        if tag == "Q" and (val or "").strip() == "1":
            print("[master] fresh test requested via the API")
            _master_test_safely(args, mem, slave)
        else:
            time.sleep(POLL_INTERVAL)


def _master_test_safely(args, mem, slave):
    """Run one full test; on an error restore the pins and tell the slave so the API caller is not left waiting."""
    t0 = time.time()
    try:
        run_master_test(args, mem, slave)
        print(f"[master] test finished in {time.time() - t0:.1f} s")
    except Exception as e:
        print(f"[master] test aborted: {type(e).__name__}: {e}")
        mem.restore()
        led_set("fail")
        try:
            slave.uart.flush_input()
            slave.cmd("RESTORE", timeout=3, retries=1)
            slave.cmd(f"FAIL {type(e).__name__}: {e}".replace("\n", " "), timeout=3, retries=1)
        except RuntimeError:
            pass


def run_master_test(args, mem, slave):
    """Run the pin, Ethernet and CAN tests once and publish the reports (master disk + slave)."""
    led_set("busy")
    u_ms, u_kbps = measure_uart_speed(slave)
    if u_ms:
        print(f"[master] UART measurement: command round trip {u_ms:.1f} ms, effective {u_kbps:.1f} kbit/s")
    try:
        _, slave_id = slave.cmd("INFO", timeout=5)
    except RuntimeError:
        slave_id = "unavailable (old slave version?)"

    mem.setup()
    slave.cmd("SETUP")
    n = len(PINS)
    results = {}
    for tag in ("A→B", "B→A"):
        local_drives = tag == "A→B"
        results[tag] = {
            "base_src": mem.read_all() if local_drives else slave.read_pins(),
            "base_dst": slave.read_pins() if local_drives else mem.read_all(),
            "pins": {}}
        for i in range(n):
            rec = {}
            for v in (1, 0):
                if local_drives:
                    mem.drive(i, v)
                    time.sleep(args.settle)
                    rec[f"far{v}"], rec[f"near{v}"] = slave.read_pins(), mem.read_all()
                else:
                    slave.cmd(f"DRIVE {i} {v}")
                    time.sleep(args.settle)
                    rec[f"far{v}"], rec[f"near{v}"] = mem.read_all(), slave.read_pins()
            (mem.release(i) if local_drives else slave.cmd(f"RELEASE {i}"))
            results[tag]["pins"][i] = rec
            print(f"\r[master] test... {tag} pin {PINS[i][0]:>2}   ", end="", flush=True)
    print()
    slave.cmd("RESTORE")
    mem.restore()
    print("[master] running Ethernet test...")
    try:
        eth_lines, eth_data = eth_test(slave)
    except Exception as e:
        eth_lines = [f"- Ethernet   : test error ({type(e).__name__}: {e})"]
        eth_data = {"result": "FAIL", "detail": f"test error: {e}"}
    for line in eth_lines:
        print("  " + line)

    print("[master] running CAN bus test...")
    try:
        can_lines, can_data = can_test(slave)
    except Exception as e:
        can_lines = [f"- CAN Bus    : test error ({type(e).__name__}: {e})"]
        can_data = {"result": "FAIL", "detail": f"test error: {e}"}
    for line in can_lines:
        print("  " + line)

    verdicts, peers = analyze(results, PINS)
    bad = sum(1 for s, _ in verdicts.values() if s != "OK")

    model = _read_text("/proc/device-tree/model")
    kernel = os.uname().release
    lines = [
        "=" * 58,
        "T3 GEMSTONE O1 — BOARD-TO-BOARD HAT PIN TEST REPORT",
        "=" * 58,
        f"Date/time     : {time.strftime('%Y-%m-%d %H:%M:%S %z')}",
        f"Model/kernel  : {model} | kernel {kernel}",
        "",
        "BOARD IDENTITIES",
        f"- Master : {board_info()}",
        f"- Slave  : {slave_id}",
        "",
        "METHOD",
        f"- Control channel: UART-MAIN1 ({UART_DEV}), 115200 baud, 8N1, raw mode;",
        "  physical pin 8 (TX) <-> 10 (RX) cross-wired. Establishing the channel",
        "  also verifies pins 8 and 10.",
        "- Pins are muxed via /dev/mem to mode 7 (GPIO) + input + internal pulldown",
        "  (padcfg=0x40007); GPIO is accessed at register level.",
        "- Walking-1/0: each pin in turn is made an output on one board and driven",
        "  1, then 0; ALL pins of the other board and the remaining pins of the",
        "  driving board are read. Then the direction is reversed.",
        f"  Total: 2 directions x {len(PINS)} pins x 2 levels = {4 * len(PINS)} drives,",
        f"  both boards are fully read on every drive (settle: {args.settle} s).",
        "- The connection map is discovered automatically; intentionally crossed",
        "  TX/RX pairs are not counted as faults and are shown in the 'link' column.",
        "- Fault classes: OPEN (no conduction in either direction), SHORT (more than",
        "  one pin follows), ONE-WAY (driver/receiver fault).",
        "- The pinmux is restored to its original values when the test ends.",
        "",
        "SCOPE",
        f"- Tested: {len(PINS)} GPIO pins + control channel (pins 8, 10)",
        "- Pin 21: shared with the MISO line of the on-board IMU (ICM-20948);",
        "  tested with IMU_EN enabled, restored to its previous state afterwards.",
        f"- Excluded: pins {sorted(SKIP_PINS)},",
        f"  pins {sorted(PMIC_PINS)} (PMIC I2C line — must not be wired),",
        "  power pins 1/2/4/17 (disconnected), GNDs common.",
        "",
        "=== PIN TEST RESULT ===",
        f"{'pin':>4} {'link':<10} {'status':<12} {'function':<15} detail"]
    functions = {p[0]: p[5].split(" (")[0].split(" —")[0] for p in PINS}
    for pin in sorted(verdicts):
        st, det = verdicts[pin]
        peer = peers.get(pin)
        link = "—" if peer is None else f"↔ {peer}"
        lines.append(f"{pin:>4} {link:<10} {'✅ ' + st if st == 'OK' else '❌ ' + st:<12} "
                     f"{functions.get(pin, ''):<15} {det}")
    lines.append(f"\npin 8 ↔ 10 : ✅ OK (UART control channel — UART1/ttyS3)")
    lines.append("")
    lines.append("INTERFACE MEASUREMENTS")
    if u_ms:
        lines.append(f"- UART       : {UART_DEV}, 115200 baud 8N1; measured command round trip "
                     f"{u_ms:.1f} ms, effective data rate {u_kbps:.1f} kbit/s "
                     f"(including line protocol overhead; raw line capacity 115.2 kbit/s)")
    lines.extend(eth_lines)
    lines.extend(can_lines)
    lines.append("- I2C        : continuity of the I2C pins (3/5) is verified by the GPIO test. "
                 "A real I2C protocol test between two Linux boards is not performed because "
                 "it requires the I2C controller's slave mode (not supported by the driver).")
    lines.append("")
    lines.append(f"{len(verdicts) - bad}/{len(verdicts)} GPIO pins OK.")
    lines.append("")
    lines.append("=" * 58)
    overall_fail = bad or eth_data["result"] == "FAIL" or can_data["result"] == "FAIL"
    if overall_fail:
        parts = ([f"{bad} FAULTY PINS"] if bad else []) + \
                (["ETHERNET FAIL"] if eth_data["result"] == "FAIL" else []) + \
                (["CAN BUS FAIL"] if can_data["result"] == "FAIL" else [])
        lines.append("   ❌❌  TEST FAILED — " + ", ".join(parts))
        lines.append("=" * 58)
        if bad:
            lines.append("FAULTY PINS:")
            for pin in sorted(verdicts):
                st, det = verdicts[pin]
                if st != "OK":
                    lines.append(f"   pin {pin:>2} : {st}" + (f" — {det}" if det else ""))
    else:
        lines.append("   ✅✅  TEST PASSED — ALL PINS OK 🎉")
        lines.append("=" * 58)
    report = "\n".join(lines)
    print(report)
    try:
        with open(REPORT, "w") as fp:
            fp.write(report + "\n")
        archive = REPORT.replace(".txt", time.strftime("-%Y%m%d-%H%M%S.txt"))
        with open(archive, "w") as fp:
            fp.write(report + "\n")
        print(f"[master] report written: {REPORT}  (archive: {archive})")
    except OSError as e:
        print(f"[master] could not write report: {e}")

    failed_pins = [{"pin": pin, "status": st, "detail": det}
                   for pin in sorted(verdicts)
                   for st, det in [verdicts[pin]] if st != "OK"]
    json_data = {
        "date": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "master_id": board_info(),
        "slave_id": slave_id,
        "gpio": {
            "result": "FAIL" if bad else "OK",
            "passed": len(verdicts) - bad,
            "total": len(verdicts),
            "failed_pins": failed_pins,
        },
        "can": can_data,
        "ethernet": eth_data,
    }
    try:
        with open(REPORT_JSON, "w") as fp:
            json.dump(json_data, fp, ensure_ascii=False, indent=1)
        print(f"[master] JSON report written: {REPORT_JSON}")
    except OSError as e:
        print(f"[master] could not write JSON report: {e}")

    try:
        json_bytes = json.dumps(json_data, ensure_ascii=False).encode("utf-8")
        send_report_to_slave(slave, json_bytes)
        print(f"[master] JSON report also saved on the slave ({REPORT_JSON}, via UART)")
    except Exception as e:
        print(f"[master] could not send JSON report to the slave: {e}")
        try:
            slave.cmd(f"FAIL could not deliver the report: {e}".replace("\n", " "), timeout=3)
        except RuntimeError:
            pass

    state = "fail" if overall_fail else "ok"
    led_set(state)
    atexit.unregister(led_restore)
    try:
        slave.cmd(f"LED {state}")
        summary = f"{len(verdicts) - bad}/{len(verdicts)} pins OK" + \
                  (f", {bad} FAULTY: " + ", ".join(str(p) for p, (s, _) in
                   sorted(verdicts.items()) if s != "OK") if bad else "")
        slave.cmd("SAY test finished — " + summary)
    except RuntimeError:
        pass


def run_safe(args):
    """Put all header pins in Hi-Z (until reboot) so the other board can be powered on safely."""
    mem = Mem(PINS)
    mem.setup()
    print(f"[safe] {len(PINS)} header pins set to Hi-Z — you can power on the other board now. "
          f"(Run again if this board reboots.)")


def main():
    """Parse the arguments and run the selected role."""
    if os.geteuid() != 0:
        sys.exit("root required: sudo python3 pintest.py master|slave|safe")
    ap = argparse.ArgumentParser(description="T3 Gemstone O1 board-to-board HAT pin test")
    ap.add_argument("role", choices=["master", "slave", "safe"],
                    help="start 'slave' first, then 'master'; 'safe' puts all header pins in Hi-Z")
    ap.add_argument("--uart", default=UART_DEV)
    ap.add_argument("--settle", type=float, default=0.02)
    ap.add_argument("--once", action="store_true",
                    help="master: run the test once and exit instead of waiting for API requests")
    args = ap.parse_args()
    sys.stdout.reconfigure(line_buffering=True)  # show progress in the journal as it happens
    try:
        {"master": run_master, "slave": run_slave, "safe": run_safe}[args.role](args)
    except KeyboardInterrupt:
        print("\ninterrupted — restoring pinmux")


if __name__ == "__main__":
    main()
