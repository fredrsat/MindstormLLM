"""Load robot hardware configuration from YAML."""
from __future__ import annotations
from pathlib import Path
import yaml

CONFIG_PATH = Path(__file__).parent.parent / "config" / "robot.yaml"


def load_robot_config(path: Path | None = None) -> dict:
    """Load and return robot config dict."""
    p = path or CONFIG_PATH
    with open(p) as f:
        return yaml.safe_load(f)


def get_port_config(config: dict) -> dict[str, str]:
    """Build port -> role mapping from config."""
    ports = config.get("ports", {})
    return {port: info["role"] for port, info in ports.items()}


def get_driving_pairs(config: dict) -> list[tuple[str, str]]:
    """Get (left, right) motor pairs for driving."""
    d = config.get("driving", {})
    pairs = []
    fl, fr = d.get("front_left"), d.get("front_right")
    if fl and fr:
        pairs.append((fl, fr))
    rl, rr = d.get("rear_left"), d.get("rear_right")
    if rl and rr:
        pairs.append((rl, rr))
    return pairs


def get_reversed_ports(config: dict) -> set[str]:
    """Get set of motor ports that are mounted in reverse."""
    return set(config.get("driving", {}).get("reversed", []))


def build_hardware_prompt(config: dict) -> str:
    """Generate hardware description for LLM system prompt."""
    lines = ["## Hardware setup"]
    for port, info in config.get("ports", {}).items():
        lines.append(f"- Port {port}: {info['role']} ({info['type']})")
    lines.append("- IMU: Built-in gyroscope and accelerometer")

    pairs = get_driving_pairs(config)
    if len(pairs) == 2:
        (fl, fr), (rl, rr) = pairs
        lines.append(f"\n## Important: 4-wheel drive")
        lines.append(f"You MUST always send two motor_pair commands: "
                      f"one for front ({fl}+{fr}) and one for rear ({rl}+{rr}).")
    elif len(pairs) == 1:
        l, r = pairs[0]
        lines.append(f"\nDriving motors: {l} (left) and {r} (right)")

    safety = config.get("safety", {})
    max_spd = safety.get("max_speed", 500)
    lines.append(f"\nSpeed is in degrees/second (deg/s). Max {max_spd}.")
    return "\n".join(lines)
