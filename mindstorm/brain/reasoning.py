"""Core reasoning loop: sensor state -> LLM -> commands."""
from __future__ import annotations
import json
import logging
from mindstorm.brain.client import Brain
from mindstorm.brain.context import Context
from mindstorm.hub.state import HubState
from mindstorm.hub.commands import (
    Command, MotorSpeedCommand, MotorStopCommand, MotorPairCommand,
    DisplayCommand, SoundCommand, StopAllCommand, MotorDegreesCommand,
)

log = logging.getLogger(__name__)


def parse_commands(response_text: str) -> list[Command]:
    """Parse LLM JSON response into typed commands."""
    try:
        data = json.loads(response_text)
    except json.JSONDecodeError:
        # Try to extract JSON from markdown code blocks
        if "```" in response_text:
            start = response_text.find("```")
            end = response_text.find("```", start + 3)
            if end > start:
                block = response_text[start + 3 : end].strip()
                if block.startswith("json"):
                    block = block[4:].strip()
                try:
                    data = json.loads(block)
                except json.JSONDecodeError:
                    log.warning("Could not parse LLM response as JSON")
                    return []
        else:
            log.warning("Could not parse LLM response: %s", response_text[:100])
            return []

    commands: list[Command] = []
    actions = data if isinstance(data, list) else data.get("actions", [data])

    for action in actions:
        cmd_type = action.get("type", action.get("cmd", ""))

        try:
            if cmd_type == "motor_speed":
                commands.append(MotorSpeedCommand(
                    port=action.get("port", "A"),
                    speed=int(action.get("speed", action.get("v", 200))),
                ))
            elif cmd_type == "motor_degrees":
                commands.append(MotorDegreesCommand(
                    port=action.get("port", "A"),
                    degrees=int(action.get("degrees", action.get("d", 360))),
                    speed=int(action.get("speed", 200)),
                ))
            elif cmd_type == "motor_stop":
                commands.append(MotorStopCommand(
                    port=action.get("port", "A"),
                ))
            elif cmd_type == "motor_pair":
                left = action.get("left", action.get("left_port", "A"))
                right = action.get("right", action.get("right_port", "B"))
                sl = action.get("speed_left", action.get("sl", action.get("speed", 200)))
                sr = action.get("speed_right", action.get("sr", action.get("speed", 200)))
                commands.append(MotorPairCommand(
                    left_port=left,
                    right_port=right,
                    speed_left=int(sl),
                    speed_right=int(sr),
                ))
            elif cmd_type == "display":
                commands.append(DisplayCommand(
                    icon=action.get("icon", action.get("image", "HAPPY")),
                ))
            elif cmd_type == "sound":
                commands.append(SoundCommand(
                    frequency=int(action.get("freq", 440)),
                    duration_ms=int(action.get("ms", 200)),
                ))
            elif cmd_type == "stop_all":
                commands.append(StopAllCommand())
        except (KeyError, ValueError, TypeError) as e:
            log.warning("Could not parse action: %s (%s)", action, e)

    return commands


async def reason(
    state: HubState,
    system_prompt: str,
    ports_config: dict[str, str],
    brain: Brain,
    context: Context,
) -> list[Command]:
    """Run one reasoning cycle: format state, call LLM, parse response."""
    state_text = state.summary(ports_config)
    context.add_user_message(state_text)

    # Compact sensor summary
    dist_parts = []
    for reading in state.distance_sensors.values():
        d = reading.distance_mm
        dist_parts.append(f"{d}mm" if d >= 0 else "---")
    dist_str = ", ".join(dist_parts) if dist_parts else "none"

    motor_speeds = []
    for port, m in state.motors.items():
        motor_speeds.append(f"{port}:{m.speed}")
    motor_str = " ".join(motor_speeds)

    log.debug("Sensors: %s", state_text)

    try:
        response = await brain.decide(
            system_prompt=system_prompt,
            messages=context.get_messages(),
        )
    except Exception as e:
        log.error("LLM call failed: %s", e)
        print(f"  LLM ERROR: {e}")
        context.remove_last()  # Remove the user message we just added
        return []

    context.add_assistant_message(response)

    # Extract thought from LLM response
    thought = ""
    try:
        data = json.loads(response)
        thought = data.get("thought", data.get("mood", ""))
    except json.JSONDecodeError:
        pass

    commands = parse_commands(response)

    # Build compact command summary
    cmd_parts = []
    for c in commands:
        d = c.to_dict()
        if d.get("c") == "mp":
            cmd_parts.append(f"motor({d['l']}+{d['r']} {d['sl']}/{d['sr']})")
        elif d.get("c") == "di":
            cmd_parts.append(f"display({d['i']})")
        elif d.get("c") == "sn":
            cmd_parts.append(f"sound({d['f']}Hz)")
        elif d.get("c") == "ms":
            cmd_parts.append(f"motor({d['p']} {d['v']})")
        else:
            cmd_parts.append(d.get("c", "?"))

    print(f"  [{dist_str}] [{motor_str}] -> {' + '.join(cmd_parts)}{f'  ({thought})' if thought else ''}")

    log.debug("LLM RAW: %s", response[:300])
    return commands
