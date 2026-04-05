"""Hub state model: represents all sensor data at a point in time."""
from __future__ import annotations
from dataclasses import dataclass, field
import time


@dataclass
class MotorState:
    port: str
    position: int = 0
    speed: int = 0
    stalled: bool = False


@dataclass
class ColorReading:
    port: str
    r: int = 0
    g: int = 0
    b: int = 0
    reflected: int = 0


@dataclass
class DistanceReading:
    port: str
    distance_mm: int = -1  # -1 = nothing detected


@dataclass
class IMUReading:
    accelerometer: tuple[int, int, int] = (0, 0, 0)
    gyroscope: tuple[int, int, int] = (0, 0, 0)
    yaw_pitch_roll: tuple[int, int, int] = (0, 0, 0)
    gesture: str | None = None
    orientation: int = 0


@dataclass
class HubState:
    """Complete snapshot of the robot's state."""
    timestamp: float = field(default_factory=time.time)
    imu: IMUReading = field(default_factory=IMUReading)
    motors: dict[str, MotorState] = field(default_factory=dict)
    color_sensors: dict[str, ColorReading] = field(default_factory=dict)
    distance_sensors: dict[str, DistanceReading] = field(default_factory=dict)
    battery_pct: int = 100
    orientation: str = "up"

    def update_from_pybricks(self, data: dict) -> None:
        """Update state from Pybricks agent sensor data (compact keys)."""
        self.timestamp = time.time()

        if "imu" in data:
            imu = data["imu"]
            accel = tuple(imu.get("a", [0, 0, 0]))
            self.imu = IMUReading(
                accelerometer=accel,
                yaw_pitch_roll=(imu.get("h", 0), imu.get("p", 0), imu.get("r", 0)),
            )

        if "batt" in data:
            # Convert mV to percentage (6000mV=0%, 8300mV=100%)
            mv = data["batt"]
            self.battery_pct = max(0, min(100, int((mv - 6000) / 23)))

        # Motors: keys like "m_A", "m_B"
        for key, val in data.items():
            if key.startswith("m_"):
                port = key[2:]
                self.motors[port] = MotorState(
                    port=port,
                    position=val.get("a", 0),
                    speed=val.get("s", 0),
                )

        # Distance sensors: keys like "d_C"
        for key, val in data.items():
            if key.startswith("d_"):
                port = key[2:]
                self.distance_sensors[port] = DistanceReading(
                    port=port,
                    distance_mm=val if isinstance(val, int) else -1,
                )

        # Color sensors: keys like "c_D"
        for key, val in data.items():
            if key.startswith("c_"):
                port = key[2:]
                self.color_sensors[port] = ColorReading(
                    port=port,
                    r=val.get("h", 0),  # HSV from Pybricks
                    g=val.get("s", 0),
                    b=val.get("v", 0),
                    reflected=data.get("r_" + port, 0),
                )

    def summary(self, ports_config: dict[str, str] | None = None) -> str:
        """Generate a concise text summary for the LLM."""
        lines = []
        y, p, r = self.imu.yaw_pitch_roll
        lines.append(f"IMU: yaw={y} pitch={p} roll={r}")
        if self.imu.gesture:
            lines.append(f"Gesture: {self.imu.gesture}")

        for port, motor in self.motors.items():
            label = ports_config.get(port, port) if ports_config else port
            lines.append(f"Motor {label}({port}): pos={motor.position} speed={motor.speed}")

        for port, dist in self.distance_sensors.items():
            label = ports_config.get(port, port) if ports_config else port
            d = dist.distance_mm
            lines.append(f"Distance {label}({port}): {d}mm" if d >= 0 else f"Distance {label}({port}): none")

        for port, color in self.color_sensors.items():
            label = ports_config.get(port, port) if ports_config else port
            lines.append(f"Color {label}({port}): r={color.r} g={color.g} b={color.b}")

        lines.append(f"Battery: {self.battery_pct}%")
        return "\n".join(lines)
