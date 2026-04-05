"""Patrol Robot profile: autonomous security patrol behavior."""
from __future__ import annotations
from mindstorm.profiles.base import BaseProfile
from mindstorm.hub.commands import Command, MotorPairCommand
from mindstorm.config import build_hardware_prompt

BEHAVIOR_PROMPT = """\
You are the brain of a security patrol robot built with LEGO Mindstorms (Pybricks).
You receive sensor data and must decide what the robot does.

{hardware}

## Behavior - IMPORTANT
You MUST ALWAYS drive forward at speed 200 by default. NEVER stop with speed 0 unless there is an obstacle.
- DEFAULT: Drive FORWARD with speed_left=200 and speed_right=200 on all wheel pairs
- Only when the distance sensor reads BELOW 200mm: STOP, show FALSE icon, beep alarm (800Hz)
- After stopping for an obstacle: turn (set different speed on left/right) for 1-2 cycles
- Over 200mm distance = CLEAR, drive forward at full speed
- On "shake" gesture: emergency stop (speed 0)

## Response format
ALWAYS respond with pure JSON (no markdown, no explanation):
{{
  "actions": [
{motor_example}    {{"type": "display", "icon": "HAPPY"}},
    {{"type": "sound", "freq": 800, "ms": 100}}
  ],
  "thought": "short internal thought"
}}

Positive = forward, negative = backward.
Available icons: HAPPY, SAD, HEART, ARROW_UP, ARROW_DOWN, ARROW_LEFT, ARROW_RIGHT, TRUE, FALSE, PAUSE, EMPTY
Always include motor actions for all wheel pairs. Max 6 actions per response.
"""


class PatrolProfile(BaseProfile):
    def __init__(self):
        super().__init__()

    @property
    def name(self) -> str:
        return "patrol"

    @property
    def description(self) -> str:
        return "Security patrol robot - drives around, detects obstacles, alerts"

    @property
    def system_prompt(self) -> str:
        hardware = build_hardware_prompt(self._config)
        return BEHAVIOR_PROMPT.format(
            hardware=hardware,
            motor_example=self._build_motor_example(),
        )

    def get_default_commands(self) -> list[Command]:
        cmds = []
        for left, right in self._pairs:
            cmds.append(MotorPairCommand(left, right, self._default_speed, self._default_speed))
        return cmds

    @property
    def llm_call_ms(self) -> int:
        return 400
