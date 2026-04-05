"""Command definitions sent to the Pybricks hub agent (compact keys for BLE)."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class MotorSpeedCommand:
    port: str
    speed: int  # deg/s

    def to_dict(self) -> dict:
        return {"c": "ms", "p": self.port, "v": self.speed}


@dataclass
class MotorDegreesCommand:
    port: str
    degrees: int
    speed: int = 200

    def to_dict(self) -> dict:
        return {"c": "md", "p": self.port, "d": self.degrees, "v": self.speed}


@dataclass
class MotorStopCommand:
    port: str

    def to_dict(self) -> dict:
        return {"c": "mx", "p": self.port}


@dataclass
class MotorPairCommand:
    left_port: str
    right_port: str
    speed_left: int
    speed_right: int

    def to_dict(self) -> dict:
        return {"c": "mp", "l": self.left_port, "r": self.right_port,
                "sl": self.speed_left, "sr": self.speed_right}


@dataclass
class DisplayCommand:
    icon: str = "HAPPY"

    def to_dict(self) -> dict:
        return {"c": "di", "i": self.icon}


@dataclass
class SoundCommand:
    frequency: int = 440
    duration_ms: int = 200

    def to_dict(self) -> dict:
        return {"c": "sn", "f": self.frequency, "d": self.duration_ms}


@dataclass
class StopAllCommand:
    def to_dict(self) -> dict:
        return {"c": "stop"}


Command = (MotorSpeedCommand | MotorDegreesCommand | MotorStopCommand |
           MotorPairCommand | DisplayCommand | SoundCommand | StopAllCommand)
