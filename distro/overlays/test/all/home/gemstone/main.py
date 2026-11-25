import fcntl
import glob
import json
import os
import re
import socket
import subprocess
import threading
import time
import spidev
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="T3 Gemstone O1 Hardware Test API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CAMERA_OUTPUT_DIR = "/home/gemstone/camera_output"
os.makedirs(CAMERA_OUTPUT_DIR, exist_ok=True)

app.mount("/images", StaticFiles(directory=CAMERA_OUTPUT_DIR), name="images")

PINTEST_REPORT_FILE = "/home/gemstone/pintest-report.json"
PINTEST_SOCKET = "/run/pintest.sock"   # served by pintest-slave.service
PINTEST_RUN_TIMEOUT = 180              # s; a full test normally takes well under a minute

CAMERA_LEFTOVER_GLOB = "/home/gemstone/camera_output/imx219-image-*"

CAMERA_SETUP_CMD = ["sudo", "-n", "/usr/local/bin/gem-camera-setup"]

SYSTEM_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
_path_entries = [p for p in os.environ.get("PATH", "").split(os.pathsep) if p]
os.environ["PATH"] = os.pathsep.join(
    _path_entries + [p for p in SYSTEM_PATH.split(os.pathsep) if p not in _path_entries]
)

ANSI_ESCAPE_RE = re.compile(r"\x1B(?:\[[0-?]*[ -/]*[@-~]|\][^\x07\x1B]*(?:\x07|\x1B\\)|[ -/]*[0-~])")


def strip_ansi(text):
    """Removes ANSI escape codes from text."""
    return ANSI_ESCAPE_RE.sub("", text or "")


BAROMETER_SENSOR = {
    "name": "LPS22DFTR",
    "type": "Barometer / Pressure Sensor",
    "bus": 0,
    "cs": 1,
    "who_am_i_reg": 0x0F,
    "who_am_i_value": 0xB4,
    "speed_hz": 100000
}

IMU_SENSOR = {
    "name": "ICM-20948",
    "type": "IMU / Accelerometer-Gyroscope Sensor",
    "bus": 0,
    "cs": 3,
    "who_am_i_reg": 0x00,
    "who_am_i_value": 0xEA,
    "speed_hz": 7000000
}

def _spi_read_register(bus, cs, reg, speed_hz, length=1, mode=0):
    """Reads one register over SPI. Returns (ok, response, error)."""
    spi = None
    try:
        spi = spidev.SpiDev()
        spi.open(bus, cs)
        spi.max_speed_hz = speed_hz
        spi.mode = mode
        response = spi.xfer2([reg | 0x80] + [0x00] * length)
        return True, response, None
    except Exception as e:
        return False, None, str(e)
    finally:
        if spi is not None:
            try:
                spi.close()
            except Exception:
                pass

def check_spi_sensor(sensor):
    """Reads an SPI sensor's WHO_AM_I register and checks its ID."""
    results = {
        "sensor": sensor["name"],
        "type": sensor["type"],
        "interface": f"SPI{sensor['bus']} CS{sensor['cs']}",
        "who_am_i_register": f"0x{sensor['who_am_i_reg']:02X}",
        "expected_id": f"0x{sensor['who_am_i_value']:02X}",
        "read_id": None,
        "raw_response": None,
        "bus_ok": False,
        "id_match": False
    }

    ok, response, err = _spi_read_register(
        sensor["bus"], sensor["cs"], sensor["who_am_i_reg"], sensor["speed_hz"]
    )

    if not ok:
        results["error"] = err
        return results

    results["bus_ok"] = True
    results["raw_response"] = [f"0x{b:02X}" for b in response]
    read_id = response[1] if len(response) > 1 else None
    if read_id is not None:
        results["read_id"] = f"0x{read_id:02X}"
    results["id_match"] = read_id == sensor["who_am_i_value"]

    return results

HDC2010_SENSOR = {
    "name": "HDC2010",
    "type": "Temperature / Humidity Sensor",
    "addresses": [0x40, 0x41],
    "preferred_buses": [3],
    "manufacturer_id": 0x5449,
    "device_id": 0x07D0,
    "iio_driver_name": "hdc2010"
}

HDC2010_REG_TEMP_LOW = 0x00
HDC2010_REG_DRDY_INT = 0x04
HDC2010_REG_RESET_DRDY_CONF = 0x0E
HDC2010_REG_MEAS_CONF = 0x0F
HDC2010_REG_MANUFACTURER_ID = 0xFC
HDC2010_REG_DEVICE_ID = 0xFE

I2C_SLAVE = 0x0703
I2C_SLAVE_FORCE = 0x0706


def _i2c_buses():
    """Returns the sorted numbers of the /dev/i2c-N buses."""
    buses = []
    for path in glob.glob("/dev/i2c-*"):
        suffix = path.rsplit("-", 1)[-1]
        if suffix.isdigit():
            buses.append(int(suffix))
    return sorted(buses)


def _i2c_open(bus, addr):
    """Opens an I2C bus and selects the slave address."""
    fd = os.open(f"/dev/i2c-{bus}", os.O_RDWR)
    try:
        try:
            fcntl.ioctl(fd, I2C_SLAVE, addr)
        except OSError:
            fcntl.ioctl(fd, I2C_SLAVE_FORCE, addr)
    except Exception:
        os.close(fd)
        raise
    return fd


def _i2c_read_regs(bus, addr, reg, length=1):
    """Reads length bytes starting at reg. Returns (ok, data, error)."""
    fd = None
    try:
        fd = _i2c_open(bus, addr)
        os.write(fd, bytes([reg]))
        data = os.read(fd, length)
        if len(data) != length:
            return False, None, f"Expected {length} bytes but read {len(data)} bytes"
        return True, list(data), None
    except Exception as e:
        return False, None, str(e)
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except Exception:
                pass


def _i2c_write_reg(bus, addr, reg, value):
    """Writes one byte to a register. Returns (ok, error)."""
    fd = None
    try:
        fd = _i2c_open(bus, addr)
        os.write(fd, bytes([reg, value]))
        return True, None
    except Exception as e:
        return False, str(e)
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except Exception:
                pass


def _hdc2010_read_word(bus, addr, reg):
    """Reads a little-endian 16-bit HDC2010 register. Returns (value, error)."""
    ok, data, err = _i2c_read_regs(bus, addr, reg, 2)
    if not ok:
        return None, err
    return data[0] | (data[1] << 8), None


def _hdc2010_locate(sensor):
    """Finds the bus and address the HDC2010 answers on."""
    available = _i2c_buses()
    ordered = [b for b in sensor["preferred_buses"] if b in available]
    ordered += [b for b in available if b not in ordered]

    for bus in ordered:
        for addr in sensor["addresses"]:
            manufacturer, err = _hdc2010_read_word(bus, addr, HDC2010_REG_MANUFACTURER_ID)
            if err is not None or manufacturer != sensor["manufacturer_id"]:
                continue
            device_id, _ = _hdc2010_read_word(bus, addr, HDC2010_REG_DEVICE_ID)
            return {
                "bus": bus,
                "address": addr,
                "manufacturer_id": manufacturer,
                "device_id": device_id
            }, ordered

    return None, ordered


def _hdc2010_measure(bus, addr):
    """Triggers one HDC2010 measurement and returns temperature and humidity."""
    ok, err = _i2c_write_reg(bus, addr, HDC2010_REG_RESET_DRDY_CONF, 0x00)
    if not ok:
        return None, None, None, err

    ok, err = _i2c_write_reg(bus, addr, HDC2010_REG_MEAS_CONF, 0x01)
    if not ok:
        return None, None, None, err

    ready = False
    for _ in range(20):
        time.sleep(0.01)
        ok, resp, _ = _i2c_read_regs(bus, addr, HDC2010_REG_DRDY_INT, 1)
        if ok and (resp[0] & 0x80):
            ready = True
            break
        ok, resp, _ = _i2c_read_regs(bus, addr, HDC2010_REG_MEAS_CONF, 1)
        if ok and not (resp[0] & 0x01):
            ready = True
            break

    if not ready:
        return None, None, None, "Measurement did not complete: the sensor did not report a finished conversion within 200 ms (DRDY/MEAS_TRIG)"

    ok, data, err = _i2c_read_regs(bus, addr, HDC2010_REG_TEMP_LOW, 4)
    if not ok:
        return None, None, None, err

    temp_raw = data[0] | (data[1] << 8)
    hum_raw = data[2] | (data[3] << 8)

    temperature = (temp_raw / 65536.0) * 165.0 - 40.0
    humidity = (hum_raw / 65536.0) * 100.0

    raw = {
        "data_ready": ready,
        "temperature_raw": f"0x{temp_raw:04X}",
        "humidity_raw": f"0x{hum_raw:04X}"
    }
    return round(temperature, 2), round(humidity, 2), raw, None


def _hdc2010_iio_device(sensor):
    """Returns the sysfs path of the HDC2010 iio device, or None."""
    for path in sorted(glob.glob("/sys/bus/iio/devices/iio:device*")):
        try:
            with open(f"{path}/name", 'r') as f:
                if f.read().strip() == sensor["iio_driver_name"]:
                    return path
        except Exception:
            continue
    return None


def check_hdc2010_sensor(sensor):
    """Finds the HDC2010, checks its ID and takes a measurement."""
    results = {
        "sensor": sensor["name"],
        "type": sensor["type"],
        "interface": None,
        "bus": None,
        "address": None,
        "scanned_buses": [],
        "candidate_addresses": [f"0x{a:02X}" for a in sensor["addresses"]],
        "iio_device": None,
        "expected_manufacturer_id": f"0x{sensor['manufacturer_id']:04X}",
        "expected_device_id": f"0x{sensor['device_id']:04X}",
        "read_manufacturer_id": None,
        "read_device_id": None,
        "bus_ok": False,
        "id_match": False,
        "measurement_ok": False,
        "temperature_c": None,
        "humidity_percent": None,
        "raw_measurement": None,
        "values_plausible": False
    }

    results["iio_device"] = _hdc2010_iio_device(sensor)

    available = _i2c_buses()
    if not available:
        results["error"] = "No /dev/i2c-* devices on the system"
        return results

    found, scanned = _hdc2010_locate(sensor)
    results["scanned_buses"] = scanned

    if found is None:
        return results

    results["bus_ok"] = True
    results["bus"] = found["bus"]
    results["address"] = f"0x{found['address']:02X}"
    results["interface"] = f"I2C{found['bus']} {results['address']}"
    results["read_manufacturer_id"] = f"0x{found['manufacturer_id']:04X}"
    if found["device_id"] is not None:
        results["read_device_id"] = f"0x{found['device_id']:04X}"
    results["id_match"] = found["device_id"] == sensor["device_id"]

    if not results["id_match"]:
        return results

    temperature, humidity, raw, err = _hdc2010_measure(found["bus"], found["address"])
    if err is not None:
        results["error"] = err
        return results

    results["measurement_ok"] = True
    results["temperature_c"] = temperature
    results["humidity_percent"] = humidity
    results["raw_measurement"] = raw
    results["values_plausible"] = (-20.0 <= temperature <= 85.0) and (1.0 <= humidity <= 99.0)

    return results

DD_TIMEOUT = 120
BLOCK_CMD_TIMEOUT = 30


def _dd_speed(stderr):
    """Extracts the transfer speed from dd's summary line."""
    lines = (stderr or "").strip().split('\n')
    return lines[-1].split(',')[-1].strip() if lines else ""


def _lsblk_snapshot():
    """Returns the lsblk output as JSON. Returns (data, error)."""
    try:
        process = subprocess.run(
            ["lsblk", "-J", "-o", "NAME,PATH,TYPE,SIZE,FSTYPE,TRAN,RM,MOUNTPOINT"],
            capture_output=True, text=True, timeout=BLOCK_CMD_TIMEOUT
        )
        if process.returncode == 0:
            return json.loads(process.stdout), None
        return None, process.stderr.strip()
    except Exception as e:
        return None, str(e)

def _is_true(value):
    """Parses an lsblk flag that may be True/False or "1"/"0"."""
    return value is True or str(value).strip() in ("1", "true", "True")

def _find_usb_storage():
    """Finds attached USB storage devices and their partitions."""
    data, err = _lsblk_snapshot()
    candidates = []

    if data:
        for disk in data.get("blockdevices", []):
            name = disk.get("name", "")
            tran = (disk.get("tran") or "").lower()

            if tran != "usb" and not (_is_true(disk.get("rm")) and name.startswith("sd")):
                continue

            partitions = [c for c in (disk.get("children") or []) if c.get("type") == "part"]
            for entry in (partitions or [disk]):
                candidates.append({
                    "path": entry.get("path") or f"/dev/{entry.get('name')}",
                    "fstype": entry.get("fstype"),
                    "mountpoint": entry.get("mountpoint"),
                    "size": entry.get("size")
                })
    else:
        try:
            for name in sorted(os.listdir('/sys/block')):
                if not name.startswith('sd'):
                    continue
                try:
                    with open(f"/sys/block/{name}/removable", 'r') as f:
                        if f.read().strip() != "1":
                            continue
                except Exception:
                    continue

                parts = sorted(p for p in os.listdir(f"/sys/block/{name}") if p.startswith(name) and p != name)
                for entry in (parts or [name]):
                    candidates.append({
                        "path": f"/dev/{entry}",
                        "fstype": None,
                        "mountpoint": None,
                        "size": None
                    })
        except Exception as e:
            err = err or str(e)

    candidates.sort(key=lambda c: 0 if c.get("fstype") else 1)
    return candidates, err

def _raw_block_read_test(device, size_mb=100):
    """Reads a block device directly to test the USB data path without a filesystem."""
    variants = [
        ["sudo", "dd", f"if={device}", "of=/dev/null", "bs=1M", f"count={size_mb}", "iflag=direct"],
        ["sudo", "dd", f"if={device}", "of=/dev/null", "bs=1M", f"count={size_mb}"]
    ]
    last_err = ""
    for cmd in variants:
        code, _, err = run_cmd(cmd, timeout=DD_TIMEOUT)
        if code == 0:
            return True, _dd_speed(err), ""
        last_err = err
    return False, "", last_err

def run_led_sequence():
    """Blinks the red and green LEDs alternately."""
    try:
        for _ in range(10):
            with open('/sys/class/leds/RED/brightness', 'w') as f: f.write('0')
            with open('/sys/class/leds/GREEN/brightness', 'w') as f: f.write('1')
            time.sleep(0.25)

            with open('/sys/class/leds/RED/brightness', 'w') as f: f.write('1')
            with open('/sys/class/leds/GREEN/brightness', 'w') as f: f.write('0')
            time.sleep(0.25)

        with open('/sys/class/leds/RED/brightness', 'w') as f: f.write('0')
        with open('/sys/class/leds/GREEN/brightness', 'w') as f: f.write('0')
    except Exception as e:
        print(f"LED test error: {e}")


def _run_fresh_pintest(timeout):
    """Has pintest-slave ask the master for a new GPIO/Ethernet/CAN test; returns (report, None) or (None, error)."""
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    buf = b""
    try:
        sock.connect(PINTEST_SOCKET)
        sock.sendall(b"RUN\n")
        while not buf.endswith(b"\n"):
            chunk = sock.recv(65536)
            if not chunk:
                break
            buf += chunk
    except (FileNotFoundError, ConnectionRefusedError):
        return None, f"pintest-slave.service is not running ({PINTEST_SOCKET} is missing)"
    except socket.timeout:
        return None, f"the test did not finish within {timeout:.0f} s"
    except OSError as e:
        return None, str(e)
    finally:
        sock.close()

    line = buf.decode(errors="replace").strip()
    if line.startswith("OK "):
        try:
            return json.loads(line[3:]), None
        except ValueError as e:
            return None, f"invalid report from the slave: {e}"
    if line.startswith("ERR "):
        return None, line[4:]
    return None, line or "pintest-slave closed the connection without a result"


@app.get("/pintest")
def get_pintest_report(run: bool = True):
    """Runs a fresh board-to-board test (GPIO, Ethernet, CAN) and returns its JSON report.

    run=false returns the last saved report without testing.
    """
    if run:
        report, err = _run_fresh_pintest(PINTEST_RUN_TIMEOUT)
        if err:
            return JSONResponse(
                status_code=503,
                content={"status": "error", "message": f"Pin test could not be run: {err}"}
            )
        return JSONResponse(content=report)

    if not os.path.isfile(PINTEST_REPORT_FILE):
        return JSONResponse(
            status_code=404,
            content={
                "status": "error",
                "message": f"Pin test report not found: {PINTEST_REPORT_FILE}"
            }
        )

    return FileResponse(PINTEST_REPORT_FILE, media_type="application/json")

def _delete_single_file(path):
    """Deletes one regular file and reports the result."""
    result = {
        "file": path,
        "existed": False,
        "deleted": False,
        "size_bytes": None,
        "error": None
    }

    try:
        if not os.path.isfile(path) or os.path.islink(path):
            return result

        result["existed"] = True
        result["size_bytes"] = os.path.getsize(path)

        os.remove(path)

        if os.path.exists(path):
            result["error"] = "File could not be deleted; it still exists."
            return result

        result["deleted"] = True
        return result

    except PermissionError as e:
        result["error"] = f"Permission error: {e}"
        return result
    except Exception as e:
        result["error"] = str(e)
        return result


@app.api_route("/api/actions/delete-pintest", methods=["GET", "DELETE"])
def delete_pintest_report():
    """Deletes the pin test report and leftover camera images."""
    report = _delete_single_file(PINTEST_REPORT_FILE)

    results = {
        "file": report["file"],
        "existed": report["existed"],
        "deleted": report["deleted"],
        "size_bytes": report["size_bytes"],
        "images": [],
        "images_found": 0,
        "images_deleted": 0
    }

    errors = []
    if report["error"]:
        errors.append(f"{report['file']}: {report['error']}")

    try:
        image_paths = sorted(glob.glob(CAMERA_LEFTOVER_GLOB))
    except Exception as e:
        image_paths = []
        errors.append(f"{CAMERA_LEFTOVER_GLOB}: could not be listed ({e})")

    for path in image_paths:
        image_result = _delete_single_file(path)
        if not image_result["existed"] and not image_result["error"]:
            continue
        results["images"].append(image_result)
        if image_result["existed"]:
            results["images_found"] += 1
        if image_result["deleted"]:
            results["images_deleted"] += 1
        if image_result["error"]:
            errors.append(f"{path}: {image_result['error']}")

    parts = []
    if results["deleted"]:
        parts.append(f"pin test report deleted ({results['size_bytes']} bytes)")
    if results["images_deleted"]:
        parts.append(f"{results['images_deleted']} camera images deleted")

    if errors:
        return {
            "status": "error",
            "message": "Cleanup incomplete: " + "; ".join(errors),
            "details": (", ".join(parts) if parts else "No file could be deleted."),
            "data": results
        }

    if not parts:
        return {
            "status": "warning",
            "message": (
                "No files to delete (already gone): "
                f"{PINTEST_REPORT_FILE} and {CAMERA_LEFTOVER_GLOB}"
            ),
            "data": results
        }

    return {
        "status": "success",
        "message": "Cleanup complete: " + ", ".join(parts) + ".",
        "data": results
    }

@app.get("/api/system/uptime")
def get_uptime():
    """Returns the system uptime."""
    try:
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
        hours = int(uptime_seconds // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        return {"status": "success", "uptime_seconds": uptime_seconds, "uptime_formatted": f"{hours} hours, {minutes} minutes"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def _sensor_test_response(sensor):
    """Builds the API response for an SPI sensor test."""
    results = check_spi_sensor(sensor)

    if not results["bus_ok"]:
        return {
            "status": "error",
            "message": (
                f"{sensor['name']} test FAILED: could not open the {results['interface']} bus. "
                f"The SPI interface is not enabled or the device file is missing."
            ),
            "details": results.get("error"),
            "data": results
        }

    if results["id_match"]:
        return {
            "status": "success",
            "message": (
                f"{sensor['name']} test PASSED. Identity verified over "
                f"{results['interface']} (WHO_AM_I = {results['expected_id']})."
            ),
            "data": results
        }

    return {
        "status": "error",
        "message": (
            f"{sensor['name']} test FAILED. The {results['interface']} bus opened but "
            f"the ID did not match (expected {results['expected_id']}, read {results['read_id']}). "
            f"The sensor may be unsoldered, unpowered, or on the wrong CS line."
        ),
        "data": results
    }

@app.get("/api/actions/test-barometer")
def test_barometer_sensor():
    """Tests the LPS22DFTR barometer over SPI."""
    return _sensor_test_response(BAROMETER_SENSOR)

@app.get("/api/actions/test-imu")
def test_imu_sensor():
    """Tests the ICM-20948 IMU over SPI."""
    return _sensor_test_response(IMU_SENSOR)

def _hdc2010_test_response(sensor):
    """Builds the API response for the HDC2010 test."""
    results = check_hdc2010_sensor(sensor)

    if results.get("error") and not results["bus_ok"]:
        return {
            "status": "error",
            "message": (
                f"{sensor['name']} test FAILED: could not open the I2C bus. "
                f"The I2C interface is not enabled or the device file is missing."
            ),
            "details": results["error"],
            "data": results
        }

    if not results["bus_ok"]:
        scanned = ", ".join(f"I2C{b}" for b in results["scanned_buses"]) or "none"
        return {
            "status": "error",
            "message": (
                f"{sensor['name']} test FAILED: sensor not found on any bus. "
                f"Scanned buses: {scanned}; tried addresses: "
                f"{', '.join(results['candidate_addresses'])}. "
                f"The sensor may be unsoldered, unpowered, or on the wrong I2C bus."
            ),
            "data": results
        }

    if not results["id_match"]:
        return {
            "status": "error",
            "message": (
                f"{sensor['name']} test FAILED. Got a response at {results['interface']} "
                f"but the device ID did not match (expected "
                f"{results['expected_device_id']}, read {results['read_device_id']}). "
                f"There may be a different chip at this address."
            ),
            "data": results
        }

    if not results["measurement_ok"]:
        return {
            "status": "error",
            "message": (
                f"{sensor['name']} identity verified over {results['interface']} but "
                f"no measurement could be taken. The sensor may be only partly communicating."
            ),
            "details": results.get("error"),
            "data": results
        }

    if not results["values_plausible"]:
        return {
            "status": "warning",
            "message": (
                f"{sensor['name']} identity verified and a measurement was taken, but the values "
                f"are outside the plausible range ({results['temperature_c']} C, {results['humidity_percent']}%). "
                f"The sensor may be stuck at an extreme value."
            ),
            "data": results
        }

    return {
        "status": "success",
        "message": (
            f"{sensor['name']} test PASSED. Identity verified over {results['interface']} "
            f"(Device ID = {results['expected_device_id']}); measured: "
            f"{results['temperature_c']} C, {results['humidity_percent']}% relative humidity."
        ),
        "data": results
    }

@app.get("/api/actions/test-hdc2010")
def test_hdc2010_sensor():
    """Tests the HDC2010 temperature/humidity sensor over I2C."""
    return _hdc2010_test_response(HDC2010_SENSOR)

@app.get("/api/sensors/health-check")
def get_all_sensors_health():
    """Returns a PASSED/FAILED summary of the on-board sensors."""
    barometer = check_spi_sensor(BAROMETER_SENSOR)
    imu = check_spi_sensor(IMU_SENSOR)
    hdc2010 = check_hdc2010_sensor(HDC2010_SENSOR)
    systems = {
        "pressure_sensor": "PASSED" if barometer["id_match"] else "FAILED",
        "imu_sensor": "PASSED" if imu["id_match"] else "FAILED",
        "temp_humidity_sensor": "PASSED" if hdc2010["id_match"] else "FAILED"
    }
    return {
        "status": "success",
        "systems": systems,
        "data": systems
    }

@app.get("/api/actions/test-leds")
def trigger_led_test(background_tasks: BackgroundTasks):
    """Starts the LED blink test in the background."""
    background_tasks.add_task(run_led_sequence)
    return {"status": "success", "message": "LED test started."}

FAN_HWMON_NAMES = ("pwmfan", "pwm-fan")
FAN_COOLING_DEVICE_TYPES = ("pwm-fan", "pwmfan")
FAN_PWM_MAX = 255

FAN_RAMP_PERCENTS = (0, 25, 50, 75, 100)

FAN_TEST_LOCK = threading.Lock()


def _read_sysfs_text(path):
    """Reads a sysfs file as stripped text; None on error."""
    try:
        with open(path, 'r') as f:
            return f.read().strip().strip("\x00")
    except Exception:
        return None


def _read_sysfs_int(path):
    """Reads a sysfs file as an integer; None on error."""
    value = _read_sysfs_text(path)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _write_sysfs(path, value):
    """Writes a value to a sysfs file. Returns (ok, error)."""
    try:
        with open(path, 'w') as f:
            f.write(str(value))
        return True, None
    except Exception as e:
        return False, str(e)


def _find_fan_hwmon():
    """Finds the pwm_fan hwmon directory."""
    for path in sorted(glob.glob("/sys/class/hwmon/hwmon*")):
        name = _read_sysfs_text(f"{path}/name")
        if name in FAN_HWMON_NAMES and os.path.exists(f"{path}/pwm1"):
            return path
    return None


def _find_fan_cooling_device():
    """Finds the fan's thermal cooling device."""
    for path in sorted(glob.glob("/sys/class/thermal/cooling_device*")):
        if _read_sysfs_text(f"{path}/type") in FAN_COOLING_DEVICE_TYPES:
            return path
    return None


def _thermal_zones_using(cooling_device):
    """Lists the thermal zones bound to a cooling device."""
    if not cooling_device:
        return []

    target = os.path.realpath(cooling_device)
    zones = []
    for zone in sorted(glob.glob("/sys/class/thermal/thermal_zone*")):
        for link in glob.glob(f"{zone}/cdev*"):
            if link.endswith("_trip_point") or link.endswith("_weight"):
                continue
            if os.path.realpath(link) == target:
                zones.append(zone)
                break
    return zones


def _proc_interrupts_cpu_count():
    """Returns the number of CPU columns in /proc/interrupts."""
    try:
        with open("/proc/interrupts", 'r') as f:
            header = f.readline()
        return sum(1 for token in header.split() if token.startswith("CPU"))
    except Exception:
        return 0


def _irq_count_by_name(irq_name):
    """Returns the total count of a named interrupt from /proc/interrupts."""
    if not irq_name:
        return None

    ncpu = _proc_interrupts_cpu_count()
    if not ncpu:
        return None

    try:
        with open("/proc/interrupts", 'r') as f:
            for line in f:
                if line.rstrip().endswith(irq_name):
                    fields = line.split()[1:1 + ncpu]
                    return sum(int(x) for x in fields if x.lstrip("-").isdigit())
    except Exception:
        return None
    return None


def _read_thermal_temps():
    """Returns every thermal zone's temperature in Celsius."""
    temps = {}
    for zone in sorted(glob.glob("/sys/class/thermal/thermal_zone*")):
        millidegrees = _read_sysfs_int(f"{zone}/temp")
        if millidegrees is not None:
            name = _read_sysfs_text(f"{zone}/type") or os.path.basename(zone)
            temps[name] = round(millidegrees / 1000.0, 1)
    return temps


@app.get("/api/actions/test-fan")
def test_cooling_fan(dwell: float = 2.0, hold_seconds: float = 4.0):
    """Runs the fan test unless another one is already running."""
    if not FAN_TEST_LOCK.acquire(blocking=False):
        return {
            "status": "error",
            "message": "Fan test is already running; wait for it to finish and try again.",
            "data": None
        }
    try:
        return _run_fan_test(dwell, hold_seconds)
    finally:
        FAN_TEST_LOCK.release()


def _run_fan_test(dwell, hold_seconds):
    """Ramps the fan from 0% to 100% and checks PWM control and the tachometer."""
    dwell = max(0.5, min(float(dwell), 5.0))
    hold_seconds = max(0.0, min(float(hold_seconds), 10.0))

    results = {
        "hwmon_path": None,
        "driver_name": None,
        "irq_name": None,
        "pwm_max": FAN_PWM_MAX,
        "original_pwm": None,
        "original_pwm_enable": None,
        "cooling_device": None,
        "thermal_zones_suspended": [],
        "thermal_override_detected": False,
        "tach_present": False,
        "tach_irq_before": None,
        "tach_irq_after": None,
        "tach_pulses": None,
        "temperatures_before_c": {},
        "temperatures_after_c": {},
        "steps": [],
        "pwm_control_ok": False,
        "fan_spinning": False,
        "max_rpm": None,
        "restored": False
    }

    hwmon = _find_fan_hwmon()
    if not hwmon:
        results["available_hwmon"] = [
            _read_sysfs_text(f"{p}/name") for p in sorted(glob.glob("/sys/class/hwmon/hwmon*"))
        ]
        return {
            "status": "error",
            "message": (
                "Fan test FAILED: pwm_fan hwmon device not found. "
                "The pwm_fan module is not loaded or not defined in the device tree."
            ),
            "data": results
        }

    pwm_path = f"{hwmon}/pwm1"
    enable_path = f"{hwmon}/pwm1_enable"
    rpm_path = f"{hwmon}/fan1_input"

    results["hwmon_path"] = hwmon
    results["driver_name"] = _read_sysfs_text(f"{hwmon}/name")
    results["irq_name"] = _read_sysfs_text(f"{hwmon}/of_node/name")
    results["original_pwm"] = _read_sysfs_int(pwm_path)
    results["original_pwm_enable"] = _read_sysfs_int(enable_path)
    results["tach_present"] = os.path.exists(rpm_path)
    results["temperatures_before_c"] = _read_thermal_temps()

    cooling_device = _find_fan_cooling_device()
    results["cooling_device"] = cooling_device
    zones = _thermal_zones_using(cooling_device)

    saved_modes = {}
    restore_errors = []

    try:
        for zone in zones:
            mode = _read_sysfs_text(f"{zone}/mode")
            if mode is None:
                continue
            saved_modes[zone] = mode
            ok, err = _write_sysfs(f"{zone}/mode", "disabled")
            if ok:
                results["thermal_zones_suspended"].append(zone)
            else:
                saved_modes.pop(zone, None)
                restore_errors.append(f"{zone}: {err}")

        if os.path.exists(enable_path) and results["original_pwm_enable"] != 1:
            _write_sysfs(enable_path, 1)

        results["tach_irq_before"] = _irq_count_by_name(results["irq_name"])

        control_ok = True
        max_rpm = 0
        for percent in FAN_RAMP_PERCENTS:
            target = round(FAN_PWM_MAX * percent / 100)
            ok, err = _write_sysfs(pwm_path, target)

            step = {
                "percent": percent,
                "pwm_set": target,
                "pwm_readback": None,
                "rpm": None,
                "write_ok": ok,
                "holds_value": False
            }

            if not ok:
                step["error"] = err
                control_ok = False
                results["steps"].append(step)
                continue

            time.sleep(dwell)

            readback = _read_sysfs_int(pwm_path)
            step["pwm_readback"] = readback
            step["holds_value"] = readback == target
            if not step["holds_value"]:
                control_ok = False
                results["thermal_override_detected"] = True

            rpm = _read_sysfs_int(rpm_path) if results["tach_present"] else None
            step["rpm"] = rpm
            if rpm is not None and rpm > max_rpm:
                max_rpm = rpm

            results["steps"].append(step)

        if hold_seconds:
            time.sleep(hold_seconds)
            rpm = _read_sysfs_int(rpm_path) if results["tach_present"] else None
            if rpm is not None and rpm > max_rpm:
                max_rpm = rpm
            results["full_speed_hold"] = {
                "seconds": hold_seconds,
                "pwm_readback": _read_sysfs_int(pwm_path),
                "rpm": rpm
            }

        results["tach_irq_after"] = _irq_count_by_name(results["irq_name"])
        if results["tach_irq_before"] is not None and results["tach_irq_after"] is not None:
            results["tach_pulses"] = results["tach_irq_after"] - results["tach_irq_before"]

        results["pwm_control_ok"] = control_ok
        results["max_rpm"] = max_rpm
        results["fan_spinning"] = max_rpm > 0 or bool(results["tach_pulses"])

    except Exception as e:
        results["error"] = str(e)
        return {
            "status": "error",
            "message": f"Critical error during fan test: {str(e)}",
            "data": results
        }

    finally:
        if results["original_pwm"] is not None:
            ok, err = _write_sysfs(pwm_path, results["original_pwm"])
            if not ok:
                restore_errors.append(f"pwm1: {err}")

        if results["original_pwm_enable"] is not None and os.path.exists(enable_path):
            ok, err = _write_sysfs(enable_path, results["original_pwm_enable"])
            if not ok:
                restore_errors.append(f"pwm1_enable: {err}")

        for zone, mode in saved_modes.items():
            ok, err = _write_sysfs(f"{zone}/mode", mode)
            if not ok:
                restore_errors.append(f"{zone}: {err}")

        results["restored"] = not restore_errors
        if restore_errors:
            results["restore_errors"] = restore_errors
        results["temperatures_after_c"] = _read_thermal_temps()

    ramp_summary = " -> ".join(
        f"%{s['percent']}({s['pwm_readback']})" for s in results["steps"]
    )

    if not results["pwm_control_ok"]:
        if results["thermal_override_detected"]:
            return {
                "status": "error",
                "message": (
                    "Fan test FAILED: the written PWM value did not hold, the thermal governor "
                    "is writing it back. The thermal zones on the fan may not have been "
                    f"disabled. Ramp: {ramp_summary}"
                ),
                "data": results
            }
        return {
            "status": "error",
            "message": (
                f"Fan test FAILED: could not write to {pwm_path}. "
                f"The service may not be running as root."
            ),
            "data": results
        }

    if not results["fan_spinning"]:
        return {
            "status": "warning",
            "message": (
                f"PWM control WORKING (ramp: {ramp_summary}) but no signal from the "
                f"tachometer: RPM was 0 at every step and the interrupt counter never increased. "
                f"The fan is not connected, not powered, or the tachometer (tach) wire is not connected. "
                f"Visually confirm that the fan physically spins."
            ),
            "data": results
        }

    return {
        "status": "success",
        "message": (
            f"Fan test PASSED. PWM ramped from 0% to 100% (ramp: {ramp_summary}), "
            f"the tachometer confirmed the fan spins (max {results['max_rpm']} RPM). "
            f"Fan restored to its previous setting."
        ),
        "data": results
    }

@app.get("/api/actions/test-camera")
def trigger_camera_test():
    """Runs gem-camera-setup and checks that a camera was detected."""
    green_led = '/sys/class/leds/GREEN/brightness'

    def set_green(value):
        """Sets the green LED, ignoring errors."""
        try:
            with open(green_led, 'w') as f:
                f.write(value)
        except OSError:
            pass

    try:
        set_green('1')

        process = subprocess.run(
            CAMERA_SETUP_CMD,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

        output = strip_ansi(process.stdout).strip()
        error_output = strip_ansi(process.stderr).strip()

        set_green('0')

        detected_cameras = [
            line.strip() for line in output.splitlines() if "detected" in line
        ]
        detected = process.returncode == 0 and bool(detected_cameras)

        if detected:
            message = (
                f"Camera test passed. gem-camera-setup detected "
                f"{len(detected_cameras)} camera(s)."
            )
        elif process.returncode != 0:
            message = (
                f"Camera test failed. gem-camera-setup exited with code "
                f"{process.returncode}."
            )
        else:
            message = (
                "Camera test failed. gem-camera-setup detected no camera "
                "(no 'detected' line in the output)."
            )

        return {
            "status": "success" if detected else "error",
            "camera_status": "PASSED" if detected else "FAILED",
            "message": message,
            "command": " ".join(CAMERA_SETUP_CMD),
            "returncode": process.returncode,
            "setup_output": output,
            "detected_cameras": detected_cameras,
            "stderr": error_output,
        }

    except subprocess.TimeoutExpired:
        set_green('0')
        return {
            "status": "error",
            "camera_status": "FAILED",
            "message": "gem-camera-setup did not finish within 60 seconds (timeout).",
            "command": " ".join(CAMERA_SETUP_CMD),
            "setup_output": "",
            "detected_cameras": [],
        }

    except FileNotFoundError:
        set_green('0')
        return {
            "status": "error",
            "camera_status": "FAILED",
            "message": "gem-camera-setup script not found on the system.",
            "command": " ".join(CAMERA_SETUP_CMD),
            "setup_output": "",
            "detected_cameras": [],
        }

    except Exception as e:
        set_green('0')
        return {
            "status": "error",
            "camera_status": "FAILED",
            "message": f"Error during camera test: {str(e)}",
            "command": " ".join(CAMERA_SETUP_CMD),
            "setup_output": "",
            "detected_cameras": [],
        }
@app.get("/api/system/mac")
def get_mac_addresses():
    """Returns the MAC addresses of the network interfaces."""
    interfaces = {}
    try:
        for iface in os.listdir('/sys/class/net/'):
            if iface != 'lo':
                with open(f'/sys/class/net/{iface}/address', 'r') as f:
                    interfaces[iface] = f.read().strip().upper()

        return {
            "status": "success",
            "device": "Gemstone O1",
            "mac_addresses": interfaces
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Could not read MAC addresses: {str(e)}"
        }

@app.get("/api/actions/test-usb")
def test_usb_drive():
    """Mounts a USB drive and runs a read/write speed test."""
    default_mount_point = "/mnt/usb"

    results = {
        "device": None,
        "fstype": None,
        "mount_point": None,
        "already_mounted": False,
        "mount_ok": False,
        "write_ok": False,
        "read_ok": False,
        "write_speed": "",
        "read_speed": "",
        "raw_read_ok": False,
        "raw_read_speed": "",
        "detected_devices": []
    }

    mounted_by_us = False
    mount_point = None
    test_file = None

    try:
        candidates, detect_err = _find_usb_storage()
        results["detected_devices"] = candidates

        if not candidates:
            return {
                "status": "error",
                "message": "No USB storage device detected on the system. Please make sure the USB drive is plugged in.",
                "details": detect_err or "No disk with TRAN=usb or a removable flag in the lsblk output.",
                "data": results
            }

        target = candidates[0]
        device = target["path"]
        results["device"] = device
        results["fstype"] = target.get("fstype")

        if not results["fstype"]:
            code, out, _ = run_cmd(
                ["sudo", "blkid", "-o", "value", "-s", "TYPE", device], timeout=BLOCK_CMD_TIMEOUT
            )
            if code == 0 and out:
                results["fstype"] = out

        if target.get("mountpoint"):
            mount_point = target["mountpoint"]
            results["already_mounted"] = True
            results["mount_ok"] = True
        else:
            mount_point = default_mount_point
            os.makedirs(mount_point, exist_ok=True)

            if os.path.ismount(mount_point):
                run_cmd(["sudo", "umount", mount_point], timeout=BLOCK_CMD_TIMEOUT)

            fstype_order = []
            if results["fstype"]:
                fstype_order.append(results["fstype"])
            for fstype in ("vfat", "exfat", "exfat-fuse", "ntfs3", "ntfs-3g", "ntfs", "ext4"):
                if fstype not in fstype_order:
                    fstype_order.append(fstype)

            attempts = [["sudo", "mount", device, mount_point]]
            attempts += [["sudo", "mount", "-t", fstype, device, mount_point] for fstype in fstype_order]

            mount_errors = []
            for cmd in attempts:
                code, _, err = run_cmd(cmd, timeout=BLOCK_CMD_TIMEOUT)
                if code == 0:
                    results["mount_ok"] = True
                    mounted_by_us = True
                    break
                mount_errors.append(f"{' '.join(cmd[2:])}: {err}")

            if not results["mount_ok"]:
                helper_hint = {
                    "exfat": "sudo apt install exfat-fuse exfatprogs",
                    "ntfs": "sudo apt install ntfs-3g",
                    "hfsplus": "sudo apt install hfsprogs"
                }.get((results["fstype"] or "").lower())

                fs_label = f" Filesystem: {results['fstype']}." if results["fstype"] else ""
                fix_hint = helper_hint or "Format the drive as FAT32 (vfat)."

                raw_ok, raw_speed, raw_err = _raw_block_read_test(device)
                results["raw_read_ok"] = raw_ok
                results["raw_read_speed"] = raw_speed

                if raw_ok:
                    return {
                        "status": "warning",
                        "message": (
                            f"USB HARDWARE WORKING: direct block read from {device} "
                            f"({target.get('size') or 'unknown size'}) PASSED ({raw_speed}). "
                            f"However the filesystem could not be mounted, so the read/write test was not run."
                            f"{fs_label} Fix: {fix_hint}"
                        ),
                        "details": " | ".join(mount_errors),
                        "data": results
                    }

                return {
                    "status": "error",
                    "message": (
                        f"USB drive ({device}) detected but it could neither be mounted nor "
                        f"read directly.{fs_label} Fix: {fix_hint}"
                    ),
                    "details": " | ".join(mount_errors) + (f" || raw read: {raw_err}" if raw_err else ""),
                    "data": results
                }

        results["mount_point"] = mount_point
        test_file = f"{mount_point}/testfile"

        write_variants = [
            ["sudo", "dd", "if=/dev/zero", f"of={test_file}", "bs=10M", "count=10", "oflag=direct"],
            ["sudo", "dd", "if=/dev/zero", f"of={test_file}", "bs=10M", "count=10", "conv=fsync"]
        ]
        for cmd in write_variants:
            code, _, err = run_cmd(cmd, timeout=DD_TIMEOUT)
            if code == 0:
                break

        if code == 0:
            results["write_ok"] = True
            results["write_speed"] = _dd_speed(err)
        else:
            return {
                "status": "error",
                "message": "File write FAILED (the drive may be read-only or full).",
                "details": err,
                "data": results
            }

        read_variants = [
            ["sudo", "dd", f"if={test_file}", "of=/dev/null", "bs=1M", "iflag=direct"],
            ["sudo", "dd", f"if={test_file}", "of=/dev/null", "bs=1M"]
        ]
        for cmd in read_variants:
            code, _, err = run_cmd(cmd, timeout=DD_TIMEOUT)
            if code == 0:
                break

        if code == 0:
            results["read_ok"] = True
            results["read_speed"] = _dd_speed(err)
        else:
            return {
                "status": "error",
                "message": "File read FAILED.",
                "details": err,
                "data": results
            }

        return {
            "status": "success",
            "message": f"USB drive test PASSED ({device}).",
            "data": results
        }

    except Exception as e:
        return {"status": "error", "message": f"Critical error during USB test: {str(e)}", "data": results}

    finally:
        if test_file and os.path.exists(test_file):
            run_cmd(["sudo", "rm", "-f", test_file], timeout=BLOCK_CMD_TIMEOUT)
        if mounted_by_us and mount_point:
            run_cmd(["sudo", "umount", mount_point], timeout=BLOCK_CMD_TIMEOUT)


INTERNET_TCP_TARGETS = [
    ("1.1.1.1", 443),
    ("8.8.8.8", 53),
    ("8.8.8.8", 443),
]


def run_cmd(cmd, timeout=10):
    """Runs a command and returns (returncode, stdout, stderr); never raises."""
    try:
        process = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return process.returncode, process.stdout.strip(), process.stderr.strip()
    except FileNotFoundError:
        return 127, "", f"command not installed: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, "", f"command timed out: {' '.join(cmd)}"
    except Exception as e:
        return 1, "", str(e)


def get_link_state(interface):
    """Returns the interface's operstate, carrier and whether the link is up."""
    state = {"operstate": None, "carrier": None, "is_up": False}

    try:
        with open(f"/sys/class/net/{interface}/operstate", 'r') as f:
            state["operstate"] = f.read().strip()
    except OSError:
        pass

    try:
        with open(f"/sys/class/net/{interface}/carrier", 'r') as f:
            state["carrier"] = f.read().strip()
    except OSError:
        pass

    state["is_up"] = state["operstate"] == "up" or state["carrier"] == "1"
    return state


def get_signal_from_proc(interface):
    """Reads the Wi-Fi signal level and link quality from /proc/net/wireless."""
    try:
        with open("/proc/net/wireless", 'r') as f:
            for line in f:
                if line.strip().startswith(f"{interface}:"):
                    fields = line.split()
                    return fields[3].rstrip('.'), fields[2].rstrip('.')
    except (OSError, IndexError):
        pass
    return None, None


def get_wifi_link_info(interface):
    """Collects the Wi-Fi SSID, signal and bitrate using iw, nmcli or wpa_cli."""
    info = {"associated": False, "ssid": None, "signal_dbm": None,
            "bitrate": None, "link_quality": None, "source": None}

    code, out, _ = run_cmd(["iw", "dev", interface, "link"])
    if code == 0 and out and "Not connected" not in out:
        info["associated"] = True
        info["source"] = "iw"
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("SSID:"):
                info["ssid"] = line.split("SSID:", 1)[1].strip()
            elif line.startswith("signal:"):
                info["signal_dbm"] = line.split("signal:", 1)[1].replace("dBm", "").strip()
            elif line.startswith("tx bitrate:"):
                info["bitrate"] = line.split("tx bitrate:", 1)[1].strip()

    if not info["ssid"]:
        code, out, _ = run_cmd(["nmcli", "-t", "-f", "ACTIVE,SSID,SIGNAL,RATE", "dev", "wifi"])
        if code == 0:
            for line in out.splitlines():
                if line.startswith("yes:"):
                    fields = line.split(":")
                    info["associated"] = True
                    info["source"] = "nmcli"
                    info["ssid"] = fields[1] or None
                    if len(fields) > 3:
                        info["bitrate"] = fields[3] or None
                    break

    if not info["ssid"]:
        code, out, _ = run_cmd(["wpa_cli", "-i", interface, "status"])
        if code == 0 and "wpa_state=COMPLETED" in out:
            info["associated"] = True
            info["source"] = "wpa_cli"
            for line in out.splitlines():
                if line.startswith("ssid="):
                    info["ssid"] = line.split("=", 1)[1].strip()

    level, quality = get_signal_from_proc(interface)
    if info["signal_dbm"] is None:
        info["signal_dbm"] = level
    info["link_quality"] = quality

    if not info["associated"] and level is not None:
        info["associated"] = True
        info["source"] = "/proc/net/wireless"

    return info


def get_ipv4_addresses(interface):
    """Returns all IPv4 addresses (CIDR) of the interface."""
    code, out, _ = run_cmd(["ip", "-4", "-oneline", "addr", "show", "dev", interface])
    if code != 0:
        return []
    return [field for field in out.split() if "/" in field and field[0].isdigit()]


def get_ipv4_address(interface):
    """Returns the first IPv4 address (CIDR) of the interface, or None."""
    addresses = get_ipv4_addresses(interface)
    return addresses[0] if addresses else None


def get_default_gateway(interface):
    """Returns the default gateway of the interface, or None."""
    code, out, _ = run_cmd(["ip", "-4", "route", "show", "default", "dev", interface])
    if code == 0 and out:
        fields = out.split()
        if "via" in fields:
            return fields[fields.index("via") + 1]
    return None


def tcp_connect_test(interface, host, port, timeout=2.5):
    """Tries a TCP handshake to host:port through the given interface."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, interface.encode())
        sock.settimeout(timeout)
        started = time.monotonic()
        sock.connect((host, port))
        return True, round((time.monotonic() - started) * 1000, 2), None
    except OSError as e:
        return False, None, str(e)
    finally:
        sock.close()


def icmp_ping_test(interface, target="8.8.8.8", count=4):
    """Pings a target through the given interface and parses the result."""
    result = {"ok": False, "avg_ms": None, "packet_loss": None, "output": None, "error": None}

    cmd = ["ping", "-n", "-I", interface, "-c", str(count), "-i", "0.3", "-W", "2", target]
    code, out, err = run_cmd(cmd, timeout=count * 3 + 5)

    result["output"] = out or None
    result["error"] = err or None
    result["ok"] = code == 0

    for line in out.splitlines():
        if "packet loss" in line:
            for field in line.split(","):
                if "packet loss" in field:
                    result["packet_loss"] = field.strip()
        if "min/avg/max" in line:
            try:
                result["avg_ms"] = line.split("=")[1].strip().split("/")[1]
            except (IndexError, ValueError):
                pass

    return result


def check_internet(interface):
    """Checks internet access over TCP and DNS resolution."""
    internet = {
        "tcp_ok": False,
        "tcp_target": None,
        "tcp_time_ms": None,
        "tcp_errors": [],
        "dns_ok": False,
    }

    for host, port in INTERNET_TCP_TARGETS:
        ok, elapsed_ms, error = tcp_connect_test(interface, host, port)
        if ok:
            internet["tcp_ok"] = True
            internet["tcp_target"] = f"{host}:{port}"
            internet["tcp_time_ms"] = elapsed_ms
            break
        internet["tcp_errors"].append(f"{host}:{port} -> {error}")

    code, out, _ = run_cmd(["getent", "ahostsv4", "cloudflare.com"], timeout=4)
    internet["dns_ok"] = code == 0 and bool(out)

    return internet


@app.get("/api/actions/test-wifi")
def test_wifi_connection():
    """Tests the Wi-Fi link, IP address, gateway and internet access."""
    interface = "wlan0"

    results = {
        "interface_exists": False,
        "is_up": False,
        "ssid": None,
        "ping_ok": False,
        "ping_time_ms": None,
        "interface_name": interface,
        "operstate": None,
        "carrier": None,
        "associated": False,
        "signal_dbm": None,
        "bitrate": None,
        "link_quality": None,
        "link_info_source": None,
        "ip_address": None,
        "gateway": None,
        "gateway_ping_ok": False,
        "power_save": None,
        "internet_ok": False,
        "internet_check": None,
        "icmp_detail": None,
    }

    try:
        if not os.path.exists(f"/sys/class/net/{interface}"):
            return {
                "status": "error",
                "message": f"Wi-Fi hardware not found (the {interface} interface does not exist).",
                "data": results
            }
        results["interface_exists"] = True

        link = get_link_state(interface)
        results["operstate"] = link["operstate"]
        results["carrier"] = link["carrier"]
        results["is_up"] = link["is_up"]

        if not results["is_up"]:
            return {
                "status": "error",
                "message": f"Wi-Fi interface is down (operstate={link['operstate']}). To bring it up: ip link set {interface} up",
                "data": results
            }

        wifi = get_wifi_link_info(interface)
        results["associated"] = wifi["associated"]
        results["ssid"] = wifi["ssid"]
        results["signal_dbm"] = wifi["signal_dbm"]
        results["bitrate"] = wifi["bitrate"]
        results["link_quality"] = wifi["link_quality"]
        results["link_info_source"] = wifi["source"]

        code, out, _ = run_cmd(["iw", "dev", interface, "get", "power_save"])
        if code == 0 and out:
            results["power_save"] = out.split(":")[-1].strip()
        elif wifi["ssid"]:
            code, out, _ = run_cmd(["nmcli", "-t", "-f", "802-11-wireless.powersave",
                                    "connection", "show", wifi["ssid"]])
            if code == 0 and ":" in out:
                results["power_save"] = out.split(":", 1)[1].strip()

        if not results["associated"]:
            return {
                "status": "error",
                "message": "Wi-Fi interface is up but not associated with any network.",
                "data": results
            }

        results["ip_address"] = get_ipv4_address(interface)
        results["gateway"] = get_default_gateway(interface)

        if not results["ip_address"]:
            return {
                "status": "warning",
                "message": f"Connected to '{results['ssid']}' but no IP address was obtained (DHCP failed).",
                "data": results
            }

        if results["gateway"]:
            gateway_ping = icmp_ping_test(interface, results["gateway"], count=3)
            results["gateway_ping_ok"] = gateway_ping["ok"]

        internet = check_internet(interface)
        results["internet_check"] = internet

        icmp = icmp_ping_test(interface)
        results["icmp_detail"] = icmp
        results["ping_ok"] = icmp["ok"]
        results["ping_time_ms"] = icmp["avg_ms"]

        results["internet_ok"] = internet["tcp_ok"] or icmp["ok"]

        if results["internet_ok"]:
            message = f"Wi-Fi connection active ('{results['ssid']}'), internet access PASSED."
            if not icmp["ok"]:
                message += " (Note: ICMP/ping is blocked on this network; verified over TCP.)"
            if not internet["dns_ok"]:
                message += " (Warning: DNS resolution is not working.)"
            return {"status": "success", "message": message, "data": results}

        if results["gateway_ping_ok"]:
            return {
                "status": "warning",
                "message": (f"Connected to '{results['ssid']}' and the gateway ({results['gateway']}) "
                            f"is reachable, but there is no internet access. The board is fine; the problem "
                            f"is the network's own internet uplink or the gateway configuration."),
                "data": results
            }

        if not results["gateway"]:
            return {
                "status": "warning",
                "message": f"Connected to '{results['ssid']}' but no default gateway (default route) is configured on {interface}.",
                "data": results
            }

        return {
            "status": "warning",
            "message": f"Connected to '{results['ssid']}' but neither the modem nor the internet is reachable (signal: {results['signal_dbm']} dBm, packet loss: {icmp['packet_loss']}).",
            "data": results
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Critical error during Wi-Fi test: {str(e)}",
            "data": results
        }

@app.get("/api/actions/test-ethernet")
def test_ethernet_connection():
    """Tests the Ethernet link and internet access."""

    interface = None
    try:
        for iface in os.listdir('/sys/class/net/'):
            if iface.startswith('eth') or iface.startswith('end') or iface.startswith('enp'):
                interface = iface
                break
    except Exception:
        pass

    results = {
        "interface_exists": False,
        "interface_name": interface,
        "is_up": False,
        "ping_ok": False,
        "ping_time_ms": None
    }

    if not interface:
        return {
            "status": "error",
            "message": "Ethernet interface not found. The hardware is not supported or the driver is not loaded.",
            "data": results
        }

    try:
        results["interface_exists"] = True

        with open(f"/sys/class/net/{interface}/operstate", 'r') as f:
            state = f.read().strip()
            if state == "up" or state == "unknown":
                with open(f"/sys/class/net/{interface}/carrier", 'r') as carrier_file:
                    if carrier_file.read().strip() == "1":
                        results["is_up"] = True

        ping = icmp_ping_test(interface, count=3)
        results["ping_ok"] = ping["ok"]
        results["ping_time_ms"] = ping["avg_ms"]

        if results["ping_ok"]:
            return {
                "status": "success",
                "message": f"Ethernet ({interface}) link active, internet access PASSED.",
                "data": results
            }
        elif results["is_up"]:
            return {
                "status": "warning",
                "message": f"Ethernet ({interface}) cable is plugged in but the internet is unreachable.",
                "data": results
            }
        else:
            return {
                "status": "error",
                "message": f"Ethernet ({interface}) cable is not plugged in or the link could not be established.",
                "data": results
            }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Critical error during Ethernet test: {str(e)}",
            "data": results
        }

EMMC_DEVICE = "/dev/mmcblk0"
EMMC_PREFERRED_PARTITION = "/dev/mmcblk0p2"
EMMC_MOUNT_POINT = "/mnt/emmc"

EMMC_MKFS_TIMEOUT = 300


def _emmc_layout():
    """Returns the eMMC disk's lsblk entry and partitions."""
    data, err = _lsblk_snapshot()
    if not data:
        return None, [], err

    for disk in data.get("blockdevices", []):
        if (disk.get("path") or f"/dev/{disk.get('name')}") == EMMC_DEVICE:
            partitions = [c for c in (disk.get("children") or []) if c.get("type") == "part"]
            return disk, partitions, None

    return None, [], f"{EMMC_DEVICE} is not in the lsblk output"


def _emmc_select_partition(partitions):
    """Picks the eMMC partition to test."""
    for part in partitions:
        if (part.get("path") or f"/dev/{part.get('name')}") == EMMC_PREFERRED_PARTITION:
            return part
    for part in partitions:
        if part.get("fstype"):
            return part
    return partitions[0]


def _emmc_blank_check(device):
    """Checks that the eMMC is truly blank before it is formatted."""
    code, out, err = run_cmd(["sudo", "blkid", "-p", device], timeout=BLOCK_CMD_TIMEOUT)
    if code == 0:
        return False, f"blkid found a signature: {out}"
    if code != 2:
        return False, f"blkid error (exit code {code}): {err}"

    try:
        head = subprocess.run(
            ["sudo", "dd", f"if={device}", "bs=1M", "count=1", "status=none"],
            capture_output=True, timeout=BLOCK_CMD_TIMEOUT
        )
    except Exception as e:
        return False, f"could not read the first 1 MiB: {e}"

    data = head.stdout
    if head.returncode != 0 or len(data) != 1024 * 1024:
        return False, f"could not read the first 1 MiB: {head.stderr.decode(errors='replace').strip()}"
    if data.count(0x00) != len(data) and data.count(0xFF) != len(data):
        return False, "the first 1 MiB contains data"
    return True, None


@app.get("/api/actions/test-emmc")
def test_emmc_storage():
    """Mounts the internal eMMC and runs a read/write speed test."""
    results = {
        "device": None,
        "fstype": None,
        "formatted": False,
        "mount_point": None,
        "already_mounted": False,
        "mount_ok": False,
        "write_ok": False,
        "read_ok": False,
        "write_speed": "",
        "read_speed": ""
    }

    mounted_by_us = False
    mount_point = None
    test_file = None

    try:
        disk, partitions, layout_err = _emmc_layout()
        if disk is None:
            return {
                "status": "error",
                "message": f"Internal eMMC ({EMMC_DEVICE}) not found.",
                "details": layout_err,
                "data": results
            }

        if partitions:
            target = _emmc_select_partition(partitions)
        elif disk.get("fstype"):
            target = disk
        else:
            blank, reason = _emmc_blank_check(EMMC_DEVICE)
            if not blank:
                return {
                    "status": "error",
                    "message": (
                        f"The eMMC has no partitions and no recognised filesystem, but the disk is not "
                        f"blank either ({reason}). Not formatted, to avoid data loss."
                    ),
                    "data": results
                }

            code, _, err = run_cmd(["sudo", "mkfs.ext4", "-F", EMMC_DEVICE], timeout=EMMC_MKFS_TIMEOUT)
            if code != 0:
                return {
                    "status": "error",
                    "message": "The eMMC could not be formatted.",
                    "details": err,
                    "data": results
                }
            results["formatted"] = True
            target = {"path": EMMC_DEVICE, "fstype": "ext4", "mountpoint": None}

        device = target.get("path") or f"/dev/{target.get('name')}"
        results["device"] = device
        results["fstype"] = target.get("fstype")

        if target.get("mountpoint"):
            mount_point = target["mountpoint"]
            results["already_mounted"] = True
        else:
            mount_point = EMMC_MOUNT_POINT
            os.makedirs(mount_point, exist_ok=True)

            if os.path.ismount(mount_point):
                return {
                    "status": "error",
                    "message": f"{mount_point} is in use by another device; {device} could not be mounted.",
                    "data": results
                }

            code, _, err = run_cmd(["sudo", "mount", device, mount_point], timeout=BLOCK_CMD_TIMEOUT)
            if code != 0:
                return {
                    "status": "error",
                    "message": "Could not mount the internal eMMC (mount error).",
                    "details": err,
                    "data": results
                }
            mounted_by_us = True

        results["mount_ok"] = True
        results["mount_point"] = mount_point
        test_file = os.path.join(mount_point, "emmc_testfile")

        code, _, err = run_cmd(
            ["sudo", "dd", "if=/dev/zero", f"of={test_file}", "bs=10M", "count=10", "oflag=direct"],
            timeout=DD_TIMEOUT
        )
        if code != 0:
            return {"status": "error", "message": "eMMC file write FAILED.", "details": err, "data": results}
        results["write_ok"] = True
        results["write_speed"] = _dd_speed(err)

        code, _, err = run_cmd(
            ["sudo", "dd", f"if={test_file}", "of=/dev/null", "bs=1M", "iflag=direct"],
            timeout=DD_TIMEOUT
        )
        if code != 0:
            return {"status": "error", "message": "eMMC file read FAILED.", "details": err, "data": results}
        results["read_ok"] = True
        results["read_speed"] = _dd_speed(err)

        return {
            "status": "success",
            "message": f"Internal eMMC verification test PASSED ({device}).",
            "data": results
        }

    except Exception as e:
        return {"status": "error", "message": f"Critical error during eMMC test: {str(e)}", "data": results}

    finally:
        if test_file and os.path.exists(test_file):
            run_cmd(["sudo", "rm", "-f", test_file], timeout=BLOCK_CMD_TIMEOUT)
        if mounted_by_us:
            run_cmd(["sudo", "umount", mount_point], timeout=BLOCK_CMD_TIMEOUT)

@app.get("/api/actions/test-usb-gadget")
def test_usb_gadget():
    """Tests that usb0 has a PC link and the expected IP address."""
    interface = "usb0"
    target_ip = "192.168.7.2"

    results = {
        "interface_exists": False,
        "is_up": False,
        "ip_defined": False,
        "operstate": None,
        "carrier": None,
        "ip_addresses": [],
        "raw_output": ""
    }

    try:
        if os.path.exists(f"/sys/class/net/{interface}"):
            results["interface_exists"] = True

            _, out, _ = run_cmd(["ip", "addr", "show", interface])
            results["raw_output"] = out

            link = get_link_state(interface)
            results["operstate"] = link["operstate"]
            results["carrier"] = link["carrier"]
            results["is_up"] = link["is_up"]

            results["ip_addresses"] = get_ipv4_addresses(interface)
            results["ip_defined"] = target_ip in [a.split("/")[0] for a in results["ip_addresses"]]

        if results["is_up"] and results["ip_defined"]:
            return {
                "status": "success",
                "message": f"USB Gadget test PASSED. {interface} is up and IP {target_ip} is configured.",
                "data": results
            }
        elif results["interface_exists"]:
            error_msg = f"USB Gadget interface exists but "
            if not results["is_up"]:
                error_msg += "is not UP (the PC link may be disconnected). "
            if not results["ip_defined"]:
                error_msg += f"IP address {target_ip} is not configured."

            return {
                "status": "warning",
                "message": error_msg.strip(),
                "data": results
            }
        else:
            return {
                "status": "error",
                "message": f"USB Gadget interface ({interface}) not found. The drivers or the gadget module are not active.",
                "data": results
            }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Critical error during USB Gadget test: {str(e)}",
            "data": results
        }

@app.get("/api/actions/test-dsi")
def test_dsi_display():
    """Tests the DSI interface and whether a panel is connected."""
    drm_path = "/sys/class/drm"

    results = {
        "dsi_interface_found": False,
        "interface_name": None,
        "is_connected": False,
        "available_modes": []
    }

    try:
        if os.path.exists(drm_path):
            for interface in os.listdir(drm_path):
                if "DSI" in interface.upper():
                    results["dsi_interface_found"] = True
                    results["interface_name"] = interface

                    status_file = os.path.join(drm_path, interface, "status")
                    if os.path.exists(status_file):
                        with open(status_file, "r") as f:
                            if f.read().strip() == "connected":
                                results["is_connected"] = True

                    modes_file = os.path.join(drm_path, interface, "modes")
                    if os.path.exists(modes_file):
                        with open(modes_file, "r") as f:
                            modes = [line.strip() for line in f.readlines() if line.strip()]
                            results["available_modes"] = modes

                    break

        if results["is_connected"]:
            return {
                "status": "success",
                "message": f"DSI display connection PASSED. Panel detected on {results['interface_name']}.",
                "data": results
            }
        elif results["dsi_interface_found"]:
            return {
                "status": "warning",
                "message": f"DSI interface ({results['interface_name']}) exists but no display is connected (or it has no power).",
                "data": results
            }
        else:
            return {
                "status": "error",
                "message": "No active DSI interface found. The hardware may be off or the driver not loaded.",
                "data": results
            }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Critical error during DSI test: {str(e)}",
            "data": results
        }

HDMI_BRIDGE_CHIPS = ("sii9022", "sii902x", "tfp410", "adv7511", "adv7513", "lt8912", "it66121")

EDID_HEADER = bytes([0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x00])


def _find_hdmi_bridge():
    """Finds the HDMI transmitter chip among the I2C devices."""
    for path in sorted(glob.glob("/sys/bus/i2c/devices/*-*")):
        name = (_read_sysfs_text(f"{path}/name") or "").lower()
        if name not in HDMI_BRIDGE_CHIPS:
            continue

        driver_link = f"{path}/driver"
        driver = None
        if os.path.islink(driver_link):
            driver = os.path.basename(os.path.realpath(driver_link))

        client = os.path.basename(path)
        bus, _, addr = client.partition("-")
        return {
            "chip": name,
            "i2c_client": client,
            "bus": int(bus) if bus.isdigit() else None,
            "address": f"0x{int(addr, 16):02X}" if addr else None,
            "driver": driver,
            "driver_bound": driver is not None
        }
    return None


def _parse_edid(data):
    """Parses an EDID block: signature, checksum, vendor, name and preferred mode."""
    info = {
        "length": len(data),
        "header_ok": False,
        "checksum_ok": False,
        "manufacturer": None,
        "product_code": None,
        "edid_version": None,
        "monitor_name": None,
        "preferred_mode": None
    }

    if len(data) < 128:
        return info

    info["header_ok"] = data[:8] == EDID_HEADER
    info["checksum_ok"] = (sum(data[:128]) & 0xFF) == 0

    packed = (data[8] << 8) | data[9]
    letters = [(packed >> 10) & 0x1F, (packed >> 5) & 0x1F, packed & 0x1F]
    if all(1 <= letter <= 26 for letter in letters):
        info["manufacturer"] = "".join(chr(ord("A") + letter - 1) for letter in letters)

    info["product_code"] = f"0x{(data[11] << 8) | data[10]:04X}"
    info["edid_version"] = f"{data[18]}.{data[19]}"

    for offset in (54, 72, 90, 108):
        block = data[offset:offset + 18]
        if len(block) < 18:
            break

        if block[0] == 0 and block[1] == 0:
            if block[3] == 0xFC and info["monitor_name"] is None:
                name = block[5:18].split(b"\x0a")[0].decode("ascii", "ignore").strip()
                if name:
                    info["monitor_name"] = name
        elif info["preferred_mode"] is None:
            h_active = block[2] | ((block[4] & 0xF0) << 4)
            v_active = block[5] | ((block[7] & 0xF0) << 4)
            if h_active and v_active:
                info["preferred_mode"] = f"{h_active}x{v_active}"
                info["pixel_clock_hz"] = ((block[1] << 8) | block[0]) * 10000

    return info


@app.get("/api/actions/test-hdmi")
def test_hdmi_output():
    """Tests the HDMI chain: transmitter chip, connector, monitor and EDID."""
    drm_path = "/sys/class/drm"

    results = {
        "connector": None,
        "connector_found": False,
        "status": None,
        "enabled": None,
        "dpms": None,
        "bridge": None,
        "bridge_ok": False,
        "hpd_irq_count": None,
        "is_connected": False,
        "edid_present": False,
        "edid_valid": False,
        "edid": None,
        "available_modes": [],
        "all_connectors": []
    }

    try:
        if not os.path.isdir(drm_path):
            return {
                "status": "error",
                "message": (
                    "HDMI test FAILED: /sys/class/drm does not exist. The DRM subsystem "
                    "is not loaded and the display driver (tidss) is not running."
                ),
                "data": results
            }

        results["all_connectors"] = sorted(
            os.path.basename(p) for p in glob.glob(f"{drm_path}/card*-*")
        )

        connector = None
        for name in results["all_connectors"]:
            if "HDMI" in name.upper():
                connector = name
                break

        bridge = _find_hdmi_bridge()
        results["bridge"] = bridge
        results["bridge_ok"] = bool(bridge and bridge["driver_bound"])

        if bridge and bridge["i2c_client"]:
            results["hpd_irq_count"] = _irq_count_by_name(bridge["i2c_client"])

        if not connector:
            return {
                "status": "error",
                "message": (
                    "HDMI test FAILED: no HDMI connector on the system. "
                    f"Connectors found: {', '.join(results['all_connectors']) or 'none'}. "
                    "The DSS/HDMI bridge is not defined in the device tree or the driver is not loaded."
                ),
                "data": results
            }

        results["connector"] = connector
        results["connector_found"] = True
        connector_dir = f"{drm_path}/{connector}"

        _write_sysfs(f"{connector_dir}/status", "detect")

        results["status"] = _read_sysfs_text(f"{connector_dir}/status")
        results["enabled"] = _read_sysfs_text(f"{connector_dir}/enabled")
        results["dpms"] = _read_sysfs_text(f"{connector_dir}/dpms")
        results["is_connected"] = results["status"] == "connected"

        modes = _read_sysfs_text(f"{connector_dir}/modes")
        results["available_modes"] = [m for m in (modes or "").splitlines() if m.strip()]

        try:
            with open(f"{connector_dir}/edid", "rb") as f:
                edid = f.read()
        except Exception:
            edid = b""

        if edid:
            results["edid_present"] = True
            parsed = _parse_edid(edid)
            results["edid"] = parsed
            results["edid_valid"] = parsed["header_ok"] and parsed["checksum_ok"]

        if not results["bridge_ok"]:
            detail = "chip not found on I2C at all" if not bridge else (
                f"chip ({bridge['chip']}) present but its driver is not bound"
            )
            return {
                "status": "error",
                "message": (
                    f"HDMI test FAILED: the HDMI transmitter chip could not be verified ({detail}). "
                    f"Connector {connector} is registered but the chip is unreachable; "
                    f"the chip may be unsoldered, unpowered or the I2C line may be broken."
                ),
                "data": results
            }

        bridge_label = f"{bridge['chip']} @ I2C{bridge['bus']} {bridge['address']}"

        if not results["is_connected"]:
            return {
                "status": "warning",
                "message": (
                    f"HDMI transmitter chip is WORKING ({bridge_label}) and connector {connector} "
                    f"is registered, but no monitor is attached (HPD: {results['status']}). "
                    f"Connect a cable/monitor and run the test again."
                ),
                "data": results
            }

        if not results["edid_present"]:
            return {
                "status": "warning",
                "message": (
                    f"{connector} SAW a monitor (HPD active) but the EDID could not be read. "
                    f"The DDC (I2C) line may be faulty or the monitor does not provide an EDID."
                ),
                "data": results
            }

        if not results["edid_valid"]:
            return {
                "status": "warning",
                "message": (
                    f"EDID was read over {connector} but the block is invalid "
                    f"(header {results['edid']['header_ok']}, checksum "
                    f"{results['edid']['checksum_ok']}). There may be signal corruption on the DDC line."
                ),
                "data": results
            }

        edid_info = results["edid"]
        monitor = edid_info["monitor_name"] or edid_info["manufacturer"] or "unknown monitor"
        return {
            "status": "success",
            "message": (
                f"HDMI test PASSED. Monitor connected to connector {connector} via "
                f"{bridge_label}: {monitor} (EDID {edid_info['edid_version']}, "
                f"preferred mode {edid_info['preferred_mode']}). "
                f"It allows {len(results['available_modes'])} resolution modes."
            ),
            "data": results
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Critical error during HDMI test: {str(e)}",
            "data": results
        }

@app.get("/api/actions/test-m2")
def test_m2_slot():
    """Tests the M.2 slot by looking for a PCIe device in lspci."""
    results = {
        "lspci_ok": False,
        "bridge_found": False,
        "bridge_line": None,
        "device_found": False,
        "device_line": None,
        "device_slot": None,
        "device_class": None,
        "device_ids": None,
        "link_speed": None,
        "link_width": None,
        "raw_output": ""
    }

    try:
        process = subprocess.run(["lspci"], capture_output=True, text=True)

        if process.returncode != 0:
            return {
                "status": "error",
                "message": "The lspci command could not be run (pciutils may not be installed).",
                "details": process.stderr.strip(),
                "data": results
            }

        results["lspci_ok"] = True
        results["raw_output"] = process.stdout.strip()

        lines = [line.strip() for line in process.stdout.splitlines() if line.strip()]

        if len(lines) >= 1:
            results["bridge_found"] = True
            results["bridge_line"] = lines[0]

        if len(lines) >= 2:
            device_line = lines[1]
            results["device_found"] = True
            results["device_line"] = device_line

            parts = device_line.split(" ", 1)
            results["device_slot"] = parts[0]
            if len(parts) > 1 and ":" in parts[1]:
                results["device_class"] = parts[1].split(":")[0].strip()

            sysfs_path = f"/sys/bus/pci/devices/0000:{results['device_slot']}"
            try:
                with open(f"{sysfs_path}/vendor", "r") as f:
                    vendor_id = f.read().strip().replace("0x", "")
                with open(f"{sysfs_path}/device", "r") as f:
                    product_id = f.read().strip().replace("0x", "")
                results["device_ids"] = f"{vendor_id}:{product_id}"
            except Exception:
                pass

            for key, filename in (("link_speed", "current_link_speed"), ("link_width", "current_link_width")):
                try:
                    with open(f"{sysfs_path}/{filename}", "r") as f:
                        results[key] = f.read().strip()
                except Exception:
                    pass

        if results["device_found"]:
            return {
                "status": "success",
                "message": (
                    f"M.2 slot test PASSED. Device detected at {results['device_slot']} "
                    f"({results['device_class'] or 'unknown class'})."
                ),
                "data": results
            }
        elif results["bridge_found"]:
            return {
                "status": "error",
                "message": "No device detected in the M.2 slot. Only the PCI bridge is visible; the card may not be inserted, may not be fully seated, or the PCIe link is not working.",
                "data": results
            }
        else:
            return {
                "status": "error",
                "message": "lspci output is empty. The PCI controller is not active or its driver is not loaded.",
                "data": results
            }

    except FileNotFoundError:
        return {
            "status": "error",
            "message": "The lspci command was not found. It must be installed with 'sudo apt install pciutils'.",
            "data": results
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Critical error during M.2 slot test: {str(e)}",
            "data": results
        }

SOC_INTERNAL_RTC_DRIVERS = ("rtc-ti-k3",)

def _select_rtc_device(devices):
    """Picks the external RTC chip if present, otherwise the first RTC."""
    for name in devices:
        try:
            with open(f"/sys/class/rtc/{name}/name", 'r') as f:
                driver = f.read().strip()
        except Exception:
            continue
        if not driver.startswith(SOC_INTERNAL_RTC_DRIVERS):
            return name
    return devices[0]

def _read_rtc_sysfs(rtc_name):
    """Reads an RTC's sysfs attributes."""
    base = f"/sys/class/rtc/{rtc_name}"
    info = {
        "device": f"/dev/{rtc_name}",
        "driver_name": None,
        "utc_date": None,
        "utc_time": None,
        "since_epoch": None,
        "hctosys": None
    }

    def read_attr(attr):
        """Reads one sysfs attribute; None on error."""
        try:
            with open(f"{base}/{attr}", 'r') as f:
                return f.read().strip()
        except Exception:
            return None

    info["driver_name"] = read_attr("name")
    info["utc_date"] = read_attr("date")
    info["utc_time"] = read_attr("time")
    info["hctosys"] = read_attr("hctosys")

    epoch = read_attr("since_epoch")
    if epoch and epoch.isdigit():
        info["since_epoch"] = int(epoch)

    return info

@app.get("/api/actions/test-rtc")
def test_rtc_clock(device: str = None):
    """Checks that the RTC can be read, is ticking and matches the system time."""
    tick_wait_seconds = 2

    results = {
        "rtc_devices": [],
        "device": None,
        "driver_name": None,
        "is_external_chip": False,
        "device_node_exists": False,
        "read_ok": False,
        "rtc_utc_time": None,
        "is_ticking": False,
        "first_read_epoch": None,
        "second_read_epoch": None,
        "elapsed_seconds": None,
        "system_time_epoch": None,
        "drift_seconds": None,
        "used_for_system_time": False,
        "hwclock_output": None
    }

    try:
        sysfs_root = "/sys/class/rtc"
        if os.path.isdir(sysfs_root):
            results["rtc_devices"] = sorted(os.listdir(sysfs_root))

        if not results["rtc_devices"]:
            return {
                "status": "error",
                "message": "No RTC device found on the system. The RTC driver is not loaded or not defined in the device tree.",
                "data": results
            }

        if device:
            if device not in results["rtc_devices"]:
                return {
                    "status": "error",
                    "message": (
                        f"There is no RTC device named '{device}'. "
                        f"Devices on the system: {', '.join(results['rtc_devices'])}"
                    ),
                    "data": results
                }
            rtc_name = device
        else:
            rtc_name = _select_rtc_device(results["rtc_devices"])

        first = _read_rtc_sysfs(rtc_name)

        results["device"] = first["device"]
        results["driver_name"] = first["driver_name"]
        results["is_external_chip"] = not (first["driver_name"] or "").startswith(SOC_INTERNAL_RTC_DRIVERS)
        results["device_node_exists"] = os.path.exists(first["device"])
        results["used_for_system_time"] = first["hctosys"] == "1"

        if first["utc_date"] and first["utc_time"]:
            results["rtc_utc_time"] = f"{first['utc_date']} {first['utc_time']} UTC"
            results["read_ok"] = True

        try:
            hw = subprocess.run(
                ["sudo", "hwclock", "-r", "--rtc", first["device"]],
                capture_output=True, text=True
            )
            if hw.returncode == 0 and hw.stdout.strip():
                results["hwclock_output"] = hw.stdout.strip()
                results["read_ok"] = True
            elif hw.stderr.strip():
                results["hwclock_output"] = hw.stderr.strip()
        except FileNotFoundError:
            pass

        if not results["read_ok"]:
            return {
                "status": "error",
                "message": f"RTC device ({first['device']}) exists but the clock could not be read. The chip may not be communicating (I2C/SPI line).",
                "details": results["hwclock_output"],
                "data": results
            }

        if first["since_epoch"] is not None:
            results["first_read_epoch"] = first["since_epoch"]
            time.sleep(tick_wait_seconds)
            second = _read_rtc_sysfs(rtc_name)
            results["second_read_epoch"] = second["since_epoch"]

            if second["since_epoch"] is not None:
                elapsed = second["since_epoch"] - first["since_epoch"]
                results["elapsed_seconds"] = elapsed
                results["is_ticking"] = elapsed >= 1

                results["system_time_epoch"] = int(time.time())
                results["drift_seconds"] = results["system_time_epoch"] - second["since_epoch"]
                results["rtc_utc_time"] = f"{second['utc_date']} {second['utc_time']} UTC"

        if results["is_ticking"]:
            drift = results["drift_seconds"]
            if drift is not None and abs(drift) > 60:
                return {
                    "status": "warning",
                    "message": (
                        f"RTC ({results['driver_name']}) is running and counting but has drifted "
                        f"{drift} seconds from the system clock. The battery (coin cell) may be dead or the clock was never set. "
                        f"To fix: sudo hwclock -w"
                    ),
                    "data": results
                }

            return {
                "status": "success",
                "message": (
                    f"RTC test PASSED. {results['device']} ({results['driver_name']}) was read, "
                    f"the clock is advancing. RTC time: {results['rtc_utc_time']}"
                ),
                "data": results
            }

        if results["first_read_epoch"] is None:
            return {
                "status": "warning",
                "message": (
                    f"RTC ({results['device']}) was read but since 'since_epoch' is not supported, "
                    f"it could not be verified that the clock advances. Value read: {results['rtc_utc_time'] or results['hwclock_output']}"
                ),
                "data": results
            }

        return {
            "status": "error",
            "message": (
                f"RTC test FAILED. {results['device']} can be read but the clock is NOT ADVANCING "
                f"({results['elapsed_seconds']} seconds in {tick_wait_seconds} seconds). "
                f"The crystal oscillator is not running or the chip is held in reset."
            ),
            "data": results
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Critical error during RTC test: {str(e)}",
            "data": results
        }
EEPROM_DRIVER_GLOB = "/sys/bus/i2c/drivers/at24/*/eeprom"

EEPROM_I2C_ADDRESS = 0x51
EEPROM_PREFERRED_BUS = 2

EEPROM_SCRATCH_LENGTH = 16

EEPROM_WRITE_CYCLE_SECONDS = 0.02

EEPROM_BLANK_BYTE = 0xFF


def _eeprom_find_devices():
    """Lists the EEPROMs bound to the at24 driver."""
    devices = []
    for eeprom_path in sorted(glob.glob(EEPROM_DRIVER_GLOB)):
        device_dir = os.path.dirname(eeprom_path)
        device_id = os.path.basename(device_dir)

        bus = None
        address = None
        if "-" in device_id:
            bus_part, addr_part = device_id.split("-", 1)
            if bus_part.isdigit():
                bus = int(bus_part)
            try:
                address = int(addr_part, 16)
            except ValueError:
                address = None

        chip_name = None
        try:
            with open(f"{device_dir}/name", 'r') as f:
                chip_name = f.read().strip()
        except Exception:
            pass

        nvmem_paths = glob.glob(f"{device_dir}/*/nvmem")

        devices.append({
            "device_id": device_id,
            "sysfs_path": eeprom_path,
            "nvmem_path": nvmem_paths[0] if nvmem_paths else None,
            "i2c_bus": bus,
            "i2c_address": f"0x{address:02X}" if address is not None else None,
            "_address_int": address,
            "chip_name": chip_name
        })
    return devices


def _eeprom_select_device(devices):
    """Picks the board EEPROM at address 0x51, preferring I2C-2."""
    candidates = [d for d in devices if d["_address_int"] == EEPROM_I2C_ADDRESS]
    candidates.sort(key=lambda d: d["i2c_bus"] != EEPROM_PREFERRED_BUS)
    return candidates[0] if candidates else None


def _eeprom_i2c_ack(bus, address):
    """Checks whether a chip ACKs on the I2C bus."""
    fd = None
    try:
        fd = _i2c_open(bus, address)
        os.read(fd, 1)
        return True, None
    except Exception as e:
        return False, str(e)
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except Exception:
                pass


def _eeprom_read(path, offset=0, length=None):
    """Reads bytes from an EEPROM sysfs file. Returns (data, error)."""
    try:
        with open(path, 'rb') as f:
            f.seek(offset)
            data = f.read() if length is None else f.read(length)
        return data, None
    except Exception as e:
        return None, str(e)


def _eeprom_write(path, offset, data):
    """Writes bytes to an EEPROM sysfs file. Returns (ok, error)."""
    try:
        with open(path, 'r+b') as f:
            f.seek(offset)
            written = f.write(data)
            f.flush()
        if written != len(data):
            return False, f"wrote {written} bytes instead of {len(data)}"
        time.sleep(EEPROM_WRITE_CYCLE_SECONDS)
        return True, None
    except Exception as e:
        return False, str(e)


def _eeprom_first_diff(expected, actual):
    """Returns the index of the first differing byte, or None."""
    for i in range(min(len(expected), len(actual))):
        if expected[i] != actual[i]:
            return i
    if len(expected) != len(actual):
        return min(len(expected), len(actual))
    return None


@app.get("/api/actions/test-eeprom")
def test_eeprom(write_test: bool = True, offset: int = None, force: bool = False):
    """Tests the board EEPROM with stable reads and a restored write/read-back cycle."""
    results = {
        "devices_found": [],
        "device_id": None,
        "chip_name": None,
        "sysfs_path": None,
        "nvmem_path": None,
        "i2c_bus": None,
        "i2c_address": None,
        "i2c_ack": False,
        "size_bytes": None,
        "read_ok": False,
        "read_stable": False,
        "blank_bytes": None,
        "is_blank": None,
        "content_preview_hex": None,
        "write_test_requested": write_test,
        "write_test_performed": False,
        "write_offset": None,
        "write_length": None,
        "write_ok": False,
        "verify_ok": False,
        "restore_ok": False,
        "first_mismatch_offset": None,
        "write_protected": False,
        "error_detail": None
    }

    try:
        devices = _eeprom_find_devices()
        results["devices_found"] = [d["device_id"] for d in devices]
        device = _eeprom_select_device(devices)

        if device is None:
            for bus in _i2c_buses():
                ack, _ = _eeprom_i2c_ack(bus, EEPROM_I2C_ADDRESS)
                if ack:
                    results["i2c_bus"] = bus
                    results["i2c_address"] = f"0x{EEPROM_I2C_ADDRESS:02X}"
                    results["i2c_ack"] = True
                    return {
                        "status": "warning",
                        "message": (
                            f"EEPROM chip responds on I2C-{bus} at address 0x51 but is "
                            f"not bound to the kernel 'at24' driver. Check that the eeprom@51 "
                            f"node is defined in the device tree (content cannot be read)."
                        ),
                        "data": results
                    }
            return {
                "status": "error",
                "message": (
                    "EEPROM not found. No 0x51 device is bound to the 'at24' driver and no "
                    "I2C bus got an ACK from address 0x51. The chip may be unsoldered, unpowered "
                    "or the I2C line may be broken."
                ),
                "data": results
            }

        results["device_id"] = device["device_id"]
        results["chip_name"] = device["chip_name"]
        results["sysfs_path"] = device["sysfs_path"]
        results["nvmem_path"] = device["nvmem_path"]
        results["i2c_bus"] = device["i2c_bus"]
        results["i2c_address"] = device["i2c_address"]

        if device["i2c_bus"] is not None and device["_address_int"] is not None:
            ack, _ = _eeprom_i2c_ack(device["i2c_bus"], device["_address_int"])
            results["i2c_ack"] = ack

        content, err = _eeprom_read(device["sysfs_path"])
        if content is None:
            results["error_detail"] = err
            return {
                "status": "error",
                "message": (
                    f"EEPROM ({device['device_id']}) could not be read through sysfs: {err}. "
                    f"The chip may not be responding on the I2C bus."
                ),
                "data": results
            }

        results["read_ok"] = True
        results["size_bytes"] = len(content)
        results["blank_bytes"] = content.count(EEPROM_BLANK_BYTE)
        results["is_blank"] = results["blank_bytes"] == len(content)
        results["content_preview_hex"] = content[:32].hex()

        if len(content) == 0:
            return {
                "status": "error",
                "message": (
                    f"EEPROM ({device['device_id']}) was opened but 0 bytes were read. "
                    f"The chip responds to its address but returns no data."
                ),
                "data": results
            }

        second_read, err = _eeprom_read(device["sysfs_path"])
        results["read_stable"] = second_read == content
        if not results["read_stable"]:
            results["error_detail"] = err
            results["first_mismatch_offset"] = (
                _eeprom_first_diff(content, second_read) if second_read else None
            )
            return {
                "status": "error",
                "message": (
                    f"EEPROM was read twice but the results DIFFER (first difference at byte "
                    f"{results['first_mismatch_offset']}). There is noise on the I2C bus; "
                    f"the pull-up resistors or solder joints are suspect."
                ),
                "data": results
            }

        if write_test:
            length = min(EEPROM_SCRATCH_LENGTH, len(content))
            target = len(content) - length if offset is None else offset

            if target < 0 or target + length > len(content):
                return {
                    "status": "error",
                    "message": (
                        f"Invalid offset={offset}. The chip is {len(content)} bytes and the write test "
                        f"uses {length} bytes; offset must be between 0 and {len(content) - length}."
                    ),
                    "data": results
                }

            results["write_offset"] = target
            results["write_length"] = length
            original = content[target:target + length]

            if any(b != EEPROM_BLANK_BYTE for b in original) and not force:
                return {
                    "status": "warning",
                    "message": (
                        f"EEPROM read test PASSED ({device['chip_name'] or 'EEPROM'}, "
                        f"{len(content)} bytes) but the write test was SKIPPED: there is data "
                        f"from byte {target} on, it was not overwritten. For the write test pass "
                        f"?force=true or a blank ?offset=N."
                    ),
                    "data": results
                }

            seed = int(time.time()) & 0xFF
            pattern = bytes([(seed + i * 0x11 + 0x5A) & 0xFF for i in range(length)])
            if pattern == original:
                pattern = bytes([b ^ 0x5A for b in pattern])

            results["write_test_performed"] = True
            ok, err = _eeprom_write(device["sysfs_path"], target, pattern)
            results["write_ok"] = ok

            if not ok:
                results["error_detail"] = err
                results["write_protected"] = True
                return {
                    "status": "warning",
                    "message": (
                        f"EEPROM is readable ({len(content)} bytes) but CANNOT BE WRITTEN: {err}. "
                        f"The WP (write protect) pin may be pulled to VCC; the read side is fine."
                    ),
                    "data": results
                }

            readback, err = _eeprom_read(device["sysfs_path"], target, length)
            if readback is None:
                results["error_detail"] = err
                return {
                    "status": "error",
                    "message": f"EEPROM was written but the read-back failed: {err}",
                    "data": results
                }

            results["verify_ok"] = readback == pattern
            if not results["verify_ok"]:
                results["first_mismatch_offset"] = target + (_eeprom_first_diff(pattern, readback) or 0)

                if readback == original:
                    results["write_protected"] = True
                    results["restore_ok"] = True
                    return {
                        "status": "warning",
                        "message": (
                            f"EEPROM is readable but the write had no effect: the pattern written "
                            f"at byte {target} read back with the content unchanged. The WP pin is active or "
                            f"the chip does not complete the write cycle. The read side is fine."
                        ),
                        "data": results
                    }

            restored, restore_err = _eeprom_write(device["sysfs_path"], target, original)
            if restored:
                check, _ = _eeprom_read(device["sysfs_path"], target, length)
                results["restore_ok"] = check == original
            else:
                results["error_detail"] = restore_err

            if not results["verify_ok"]:
                return {
                    "status": "error",
                    "message": (
                        f"EEPROM write test FAILED. The data written at byte {target} did not "
                        f"match on read-back (first difference at byte {results['first_mismatch_offset']}). "
                        f"The cells are damaged or the I2C write cycle is faulty. "
                        f"Restoring old content: {'succeeded' if results['restore_ok'] else 'FAILED'}."
                    ),
                    "data": results
                }

            if not results["restore_ok"]:
                return {
                    "status": "warning",
                    "message": (
                        f"EEPROM write/read test passed but the OLD CONTENT at byte {target} "
                        f"COULD NOT BE RESTORED. This area may have been left with the test pattern."
                    ),
                    "data": results
                }

        chip = device["chip_name"] or "EEPROM"
        content_state = "content is blank (board ID not written yet)" if results["is_blank"] else \
            f"{len(content) - results['blank_bytes']} bytes programmed"

        if results["write_test_performed"]:
            return {
                "status": "success",
                "message": (
                    f"EEPROM test PASSED. {chip} (I2C-{results['i2c_bus']} / "
                    f"{results['i2c_address']}), {len(content)} bytes read, "
                    f"{results['write_length']} bytes written at byte {results['write_offset']} were verified "
                    f"and the old content was restored. State: {content_state}."
                ),
                "data": results
            }

        return {
            "status": "success",
            "message": (
                f"EEPROM read test PASSED. {chip} (I2C-{results['i2c_bus']} / "
                f"{results['i2c_address']}), {len(content)} bytes read consistently "
                f"(write test not requested). State: {content_state}."
            ),
            "data": results
        }

    except Exception as e:
        results["error_detail"] = str(e)
        return {
            "status": "error",
            "message": f"Critical error during EEPROM test: {str(e)}",
            "data": results
        }
