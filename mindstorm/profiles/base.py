"""Abstract base profile for robot behaviors."""
from __future__ import annotations
from abc import ABC, abstractmethod
from mindstorm.hub.commands import Command, MotorPairCommand, MotorSpeedCommand
from mindstorm.config import load_robot_config, get_port_config, get_driving_pairs, build_hardware_prompt


class BaseProfile(ABC):
    """Each profile defines a robot personality, port config, and LLM system prompt."""

    def __init__(self):
        self._config = load_robot_config()
        self._pairs = get_driving_pairs(self._config)
        safety = self._config.get("safety", {})
        self._max_speed = safety.get("max_speed", 500)
        self._default_speed = safety.get("default_speed", 200)

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """System prompt sent to the LLM defining this robot's behavior."""

    def get_port_config(self) -> dict[str, str]:
        """Map ports to device names: {'A': 'motor_left', 'B': 'motor_right', ...}"""
        return get_port_config(self._config)

    def get_default_commands(self) -> list[Command]:
        """Commands to execute when LLM is unavailable."""
        return []

    def validate_commands(self, commands: list[Command]) -> list[Command]:
        """Clamp motor speeds to max_speed."""
        validated = []
        for cmd in commands:
            if isinstance(cmd, MotorPairCommand):
                cmd = MotorPairCommand(
                    cmd.left_port, cmd.right_port,
                    max(-self.max_speed, min(self.max_speed, cmd.speed_left)),
                    max(-self.max_speed, min(self.max_speed, cmd.speed_right)),
                )
            elif isinstance(cmd, MotorSpeedCommand):
                cmd = MotorSpeedCommand(
                    cmd.port,
                    max(-self.max_speed, min(self.max_speed, cmd.speed)),
                )
            validated.append(cmd)
        return validated

    def _build_motor_example(self) -> str:
        """Build motor_pair JSON example for LLM prompt."""
        examples = []
        for left, right in self._pairs:
            examples.append(
                f'    {{"type": "motor_pair", "left": "{left}", "right": "{right}", '
                f'"speed_left": {self._default_speed}, "speed_right": {self._default_speed}}},'
            )
        return "\n".join(examples) + "\n" if examples else ""

    @property
    def sensor_poll_ms(self) -> int:
        return 100

    @property
    def llm_call_ms(self) -> int:
        return 500

    @property
    def max_speed(self) -> int:
        return self._max_speed
