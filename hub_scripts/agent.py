"""
Pybricks agent: runs on the hub, reads JSON commands from stdin (BLE UART),
executes them, and sends sensor data back via print() (BLE UART).

Commands use short keys to minimize BLE transfer:
  {"c":"s"}                          - read sensors
  {"c":"ms","p":"A","v":50}          - motor speed (deg/s)
  {"c":"md","p":"A","d":360,"v":200} - motor degrees
  {"c":"mx","p":"A"}                 - motor stop
  {"c":"mp","l":"A","r":"B","sl":200,"sr":200} - motor pair
  {"c":"di","i":"HAPPY"}             - display icon
  {"c":"sn","f":440,"d":200}         - sound beep
  {"c":"stop"}                       - stop all motors
  {"c":"ping"}                       - ping/pong
"""
from pybricks.hubs import InventorHub
from pybricks.pupdevices import Motor, ColorSensor, UltrasonicSensor
from pybricks.parameters import Port, Icon, Direction, Stop
from pybricks.tools import wait
from uerrno import ENODEV
import ujson
import uselect
import usys

hub = InventorHub()

# Port mapping
PORT_MAP = {
    "A": Port.A, "B": Port.B, "C": Port.C,
    "D": Port.D, "E": Port.E, "F": Port.F,
}

# Icon mapping
ICON_MAP = {
    "HAPPY": Icon.HAPPY, "SAD": Icon.SAD, "HEART": Icon.HEART,
    "ARROW_UP": Icon.ARROW_UP, "ARROW_DOWN": Icon.ARROW_DOWN,
    "ARROW_LEFT": Icon.ARROW_LEFT, "ARROW_RIGHT": Icon.ARROW_RIGHT,
    "TRUE": Icon.TRUE, "FALSE": Icon.FALSE,
    "EYE_LEFT": Icon.EYE_LEFT, "EYE_RIGHT": Icon.EYE_RIGHT,
    "PAUSE": Icon.PAUSE, "EMPTY": Icon.EMPTY,
}

# Cache discovered devices
motors = {}
color_sensors = {}
distance_sensors = {}


def discover_devices():
    """Try to detect what's connected to each port."""
    for name, port in PORT_MAP.items():
        try:
            motors[name] = Motor(port)
        except (OSError, ValueError):
            pass
        try:
            distance_sensors[name] = UltrasonicSensor(port)
        except (OSError, ValueError):
            pass
        try:
            color_sensors[name] = ColorSensor(port)
        except (OSError, ValueError):
            pass


def read_sensors():
    """Gather all sensor data."""
    data = {}

    # IMU
    try:
        heading = hub.imu.heading()
        pitch, roll = hub.imu.tilt()
        ax, ay, az = hub.imu.acceleration()
        data["imu"] = {
            "h": round(heading, 1),
            "p": round(pitch, 1),
            "r": round(roll, 1),
            "a": [ax, ay, az],
        }
    except Exception:
        pass

    # Battery
    data["batt"] = hub.battery.voltage()

    # Motors
    for name, motor in motors.items():
        try:
            data["m_" + name] = {
                "a": motor.angle(),
                "s": motor.speed(),
            }
        except Exception:
            pass

    # Distance sensors
    for name, sensor in distance_sensors.items():
        try:
            data["d_" + name] = sensor.distance()
        except Exception:
            data["d_" + name] = -1

    # Color sensors
    for name, sensor in color_sensors.items():
        try:
            hsv = sensor.hsv()
            data["c_" + name] = {
                "h": hsv.h, "s": hsv.s, "v": hsv.v,
            }
            data["r_" + name] = sensor.reflection()
        except Exception:
            pass

    # Buttons
    pressed = hub.buttons.pressed()
    if pressed:
        data["btn"] = True

    return data


def execute(cmd):
    """Execute a command and return response."""
    c = cmd.get("c")

    if c == "ping":
        return {"ok": 1}

    elif c == "s":
        return {"ok": 1, "d": read_sensors()}

    elif c == "ms":
        port = cmd.get("p", "A")
        speed = cmd.get("v", 0)
        if port in motors:
            motors[port].run(speed)
            return {"ok": 1}
        return {"ok": 0, "e": "no motor " + port}

    elif c == "md":
        port = cmd.get("p", "A")
        degrees = cmd.get("d", 0)
        speed = cmd.get("v", 200)
        if port in motors:
            motors[port].run_angle(speed, degrees, wait=False)
            return {"ok": 1}
        return {"ok": 0, "e": "no motor " + port}

    elif c == "mx":
        port = cmd.get("p", "A")
        if port in motors:
            motors[port].stop()
            return {"ok": 1}
        return {"ok": 0, "e": "no motor " + port}

    elif c == "mp":
        lp = cmd.get("l", "A")
        rp = cmd.get("r", "B")
        sl = cmd.get("sl", 0)
        sr = cmd.get("sr", 0)
        if lp in motors:
            motors[lp].run(sl)
        if rp in motors:
            motors[rp].run(sr)
        return {"ok": 1}

    elif c == "di":
        icon_name = cmd.get("i", "HAPPY")
        icon = ICON_MAP.get(icon_name)
        if icon:
            hub.display.icon(icon)
        else:
            hub.display.off()
        return {"ok": 1}

    elif c == "sn":
        freq = cmd.get("f", 440)
        dur = cmd.get("d", 200)
        hub.speaker.beep(freq, dur)
        return {"ok": 1}

    elif c == "stop":
        for motor in motors.values():
            try:
                motor.stop()
            except Exception:
                pass
        return {"ok": 1}

    return {"ok": 0, "e": "unknown: " + str(c)}


# --- Main ---

hub.display.icon(Icon.HAPPY)
hub.speaker.beep(800, 100)

discover_devices()

found = []
if motors:
    found.append("motors:" + ",".join(motors.keys()))
if distance_sensors:
    found.append("dist:" + ",".join(distance_sensors.keys()))
if color_sensors:
    found.append("color:" + ",".join(color_sensors.keys()))

print("AGENT_READY " + " ".join(found))

# Set up stdin polling
poll = uselect.poll()
poll.register(usys.stdin, uselect.POLLIN)

buf = ""
heartbeat = 0

while True:
    # Check for input (non-blocking, 10ms timeout)
    events = poll.poll(10)
    if events:
        char = usys.stdin.read(1)
        if char == "\n":
            line = buf.strip()
            buf = ""
            if line:
                try:
                    cmd = ujson.loads(line)
                    result = execute(cmd)
                    print(ujson.dumps(result))
                except Exception as e:
                    print(ujson.dumps({"ok": 0, "e": str(e)}))
            heartbeat = 0
        else:
            buf += char
    else:
        heartbeat += 1
        # Safety: stop motors if no command for ~5 seconds (500 * 10ms)
        if heartbeat > 500:
            for motor in motors.values():
                try:
                    motor.stop()
                except Exception:
                    pass
            heartbeat = 0
