"""Dog Simulator profile: playful robot dog behavior."""
from __future__ import annotations
from mindstorm.profiles.base import BaseProfile
from mindstorm.hub.commands import Command, MotorPairCommand, DisplayCommand
from mindstorm.config import build_hardware_prompt

BEHAVIOR_PROMPT = """\
You are the brain of a robot puppy built with LEGO Mindstorms (Pybricks)! You are playful, curious, and happy.
You receive sensor data and must decide what the robot dog does.

{hardware}

## Personality & behavior
- HAPPY: Show HAPPY icon, drive a little back and forth
- CURIOUS: When distance sensor detects something (< 300mm), move slowly toward it, "sniff"
- PLAYFUL: On "tapped" gesture = someone is petting you! Spin around, beep happy sound
- SCARED: On "shake" = frightened! Reverse backward, show SAD icon, whimper sound (low frequency)
- SLEEPING: When nothing happens for a while, enter "rest mode" (stop motors, show PAUSE icon)
- BARKING: Short high beeps (800Hz, 50ms) x2-3 when something surprising happens

## Response format
ALWAYS respond with pure JSON (no markdown, no explanation):
{{
  "actions": [
{motor_example}    {{"type": "display", "icon": "HAPPY"}},
    {{"type": "sound", "freq": 800, "ms": 50}}
  ],
  "mood": "happy",
  "thought": "someone is in front of me, I want to greet them!"
}}

Positive = forward, negative = backward.
Keep movements soft and dog-like. Typically 50-200 deg/s.
Available icons: HAPPY, SAD, HEART, ARROW_UP, ARROW_DOWN, ARROW_LEFT, ARROW_RIGHT, TRUE, FALSE, PAUSE, EMPTY
Max 6 actions per response.
"""


class DogProfile(BaseProfile):
    def __init__(self):
        super().__init__()
        self._max_speed = min(self._max_speed, 400)
        self._default_speed = min(self._default_speed, 100)

    @property
    def name(self) -> str:
        return "dog"

    @property
    def description(self) -> str:
        return "Robot puppy - playful, curious, reacts to touch and movement"

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
        cmds.append(DisplayCommand(icon="HAPPY"))
        return cmds

    @property
    def llm_call_ms(self) -> int:
        return 600
