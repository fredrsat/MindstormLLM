"""Dynamic profile loaded from YAML config."""
from __future__ import annotations
from mindstorm.profiles.base import BaseProfile
from mindstorm.hub.commands import Command, MotorPairCommand, DisplayCommand
from mindstorm.config import build_hardware_prompt


PROMPT_TEMPLATE = """\
{behavior}

{hardware}

## Response format
ALWAYS respond with pure JSON (no markdown, no explanation):
{{
  "actions": [
{motor_example}    {{"type": "display", "icon": "HAPPY"}},
    {{"type": "sound", "freq": 440, "ms": 200}}
  ],
  "thought": "short internal thought"
}}

Positive = forward, negative = backward.
Available icons: HAPPY, SAD, HEART, ARROW_UP, ARROW_DOWN, ARROW_LEFT, ARROW_RIGHT, TRUE, FALSE, PAUSE, EMPTY
Always include motor actions for all wheel pairs. Max 6 actions per response.
"""


class CustomProfile(BaseProfile):
    """Profile loaded from a YAML file in config/profiles/."""

    def __init__(self, profile_data: dict):
        super().__init__()
        self._data = profile_data

    @property
    def name(self) -> str:
        return self._data.get("name", "custom")

    @property
    def description(self) -> str:
        return self._data.get("description", "")

    @property
    def system_prompt(self) -> str:
        hardware = build_hardware_prompt(self._config)
        behavior = self._data.get("behavior", "You are a robot.")
        return PROMPT_TEMPLATE.format(
            behavior=behavior,
            hardware=hardware,
            motor_example=self._build_motor_example(),
        )

    def get_default_commands(self) -> list[Command]:
        cmds = []
        for left, right in self._pairs:
            cmds.append(MotorPairCommand(left, right, self._default_speed, self._default_speed))
        cmds.append(DisplayCommand(icon="HAPPY"))
        return cmds
