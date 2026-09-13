# MindstormLLM

LEGO Mindstorms 51515 (Robot Inventor) controlled by an LLM over Bluetooth Low Energy.

The robot runs a **sense-think-act** loop: sensor data is read from the hub, sent to an LLM (Claude or local Ollama model) which decides what the robot should do, and commands are sent back wirelessly via BLE.

Includes a visual **Profile Builder** (web UI) for configuration and profile creation without coding.

## Architecture

```
┌──────────────┐     BLE/UART      ┌───────────────┐    API     ┌─────────────┐
│  LEGO Hub    │◄──────────────────►│  Python host  │◄──────────►│ LLM         │
│  (Pybricks)  │  JSON commands     │  (Mac/Linux)  │  Messages  │ Claude /    │
│              │  Sensor data       │               │            │ Ollama      │
│  agent.py    │                    │  controller   │            │             │
│  MicroPython │                    │  brain/reason │            │  JSON cmds  │
└──────────────┘                    └───┬───────────┘            └─────────────┘
                                        │
                                   ┌────▼────────┐
                                   │  Web UI     │
                                   │  :8080      │
                                   │  Profile    │
                                   │  Builder    │
                                   └─────────────┘
```

### Sense-Think-Act Loop

1. **Sense**: The hub reads IMU, motors, distance, color, battery. Sent as compact JSON.
2. **Think**: The LLM receives sensor data + system prompt (profile) and returns JSON commands.
3. **Act**: Commands are sent to the hub which controls motors, display, sound.

An independent **safety loop** runs in parallel and overrides LLM commands when obstacles are detected.

## Hardware

- **LEGO Mindstorms 51515** (Robot Inventor) with Large Intelligent Hub
- **Firmware**: [Pybricks](https://pybricks.com/) v3.6.1 (replaces stock LEGO firmware)
- Motors, distance sensor, color sensor, light sensor as needed
- Ports and setup are configured in `config/robot.yaml` or via web UI

## Prerequisites

- Python 3.11+
- macOS or Linux with Bluetooth Low Energy
- Pybricks firmware flashed on the hub
- **One of**:
  - Anthropic API key (for Claude Haiku / Sonnet)
  - [Ollama](https://ollama.com/) installed locally (for Gemma, Llama, etc.)

## Installation

```bash
# Clone the project
git clone <repo-url>
cd MindstormLLM

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .

# Copy and edit config
cp config/robot.yaml.example config/robot.yaml
# Edit config/robot.yaml to match your port setup

# For Anthropic: set up API key
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env

# For Ollama: install and pull a model
ollama pull gemma4
```

## Flash Pybricks Firmware

The hub must have Pybricks firmware to work with this project.

```bash
# Install dfu-util (macOS)
brew install dfu-util libusb

# Put the hub in DFU mode:
# 1. Turn off the hub
# 2. Hold the Bluetooth button
# 3. Connect USB while holding the button
# 4. The hub blinks pink/purple = DFU mode

# Flash Pybricks
pybricksdev flash pybricks-primehub-v3.6.1.zip
```

## Usage

### Web UI (Profile Builder)

```bash
python web/app.py
# Open http://localhost:8080
```

From the web UI you can:
- Configure ports (which sensors/motors on which ports)
- Set up driving configuration (4WD, 2WD, reversed motors)
- Choose LLM provider (Anthropic or Ollama) and model
- Adjust speed and safety values
- Create new profiles from templates or from scratch
- Start and stop the robot

### CLI

```bash
# Scan for hubs
python -m mindstorm scan

# Start robot with a profile
python -m mindstorm run patrol
python -m mindstorm run dog

# List available profiles
python -m mindstorm profiles

# Verbose logging
python -m mindstorm run patrol -v
```

## Configuration

All hardware configuration lives in `config/robot.yaml`:

```yaml
ports:
  A:
    type: motor
    role: Left front motor (driving)
  B:
    type: motor
    role: Right front motor (driving)
  E:
    type: distance
    role: Distance sensor (front)

driving:
  front_left: A
  front_right: B
  rear_left: C        # Omit for 2WD
  rear_right: D
  reversed: [A, C]    # Motors mounted in reverse direction

safety:
  max_speed: 500       # deg/s
  default_speed: 200
  min_battery_pct: 10

llm:
  provider: ollama     # or "anthropic"
  model: gemma4
  url: http://localhost:11434
  max_tokens: 300
  temperature: 0.3
```

Configuration can be edited directly in YAML or via the web UI.

## Profiles

### Built-in Profiles

| Profile | Description |
|---------|-------------|
| `patrol` | Security patrol — drives around, detects obstacles, alerts |
| `dog` | Robot puppy — playful, curious, reacts to touch and movement |

### Custom Profiles

Create profiles via the web UI (Profile Builder) or create YAML files in `config/profiles/`:

```yaml
name: explorer
description: Explorer — systematically maps the surroundings
behavior: |
  You are a systematic explorer robot.
  - Drive forward until you find an obstacle
  - Turn 90 degrees and continue
  - Show ARROW_UP when driving forward
```

Profiles automatically inherit hardware setup from `robot.yaml`.

### Creating a Profile in Python

For more control, create a class that inherits from `BaseProfile`:

```python
from mindstorm.profiles.base import BaseProfile
from mindstorm.hub.commands import Command, MotorPairCommand
from mindstorm.config import build_hardware_prompt

class MyProfile(BaseProfile):
    @property
    def name(self) -> str:
        return "my_robot"

    @property
    def description(self) -> str:
        return "My custom robot"

    @property
    def system_prompt(self) -> str:
        hardware = build_hardware_prompt(self._config)
        return f"You are a robot.\n\n{hardware}\n\n..."

    def get_default_commands(self) -> list[Command]:
        cmds = []
        for left, right in self._pairs:
            cmds.append(MotorPairCommand(left, right, 200, 200))
        return cmds
```

Register it in `mindstorm/profiles/registry.py`.

## Project Structure

```
MindstormLLM/
├── mindstorm/
│   ├── __main__.py          # CLI entry point
│   ├── config.py            # YAML configuration (ports, driving, LLM)
│   ├── ble/
│   │   └── scanner.py       # BLE scanning for Pybricks hubs
│   ├── brain/
│   │   ├── client.py        # LLM clients (Anthropic + Ollama)
│   │   ├── context.py       # Rolling context window (15 message pairs)
│   │   └── reasoning.py     # Sense -> LLM -> Commands pipeline
│   ├── hub/
│   │   ├── state.py         # Hub state model (sensors, IMU, battery)
│   │   └── commands.py      # Command definitions (motor, display, sound)
│   ├── loop/
│   │   └── controller.py    # Main loop: sensor + brain + safety
│   └── profiles/
│       ├── base.py          # Abstract base profile (config, validation)
│       ├── registry.py      # Profile registry (built-in + YAML)
│       ├── patrol.py        # Security patrol
│       ├── dog.py           # Robot puppy
│       └── custom.py        # Dynamic profile from YAML
├── hub_scripts/
│   └── agent.py             # MicroPython agent running on the hub
├── web/
│   ├── app.py               # Flask web server and API
│   ├── templates/
│   │   └── index.html       # Profile Builder UI
│   └── static/
│       ├── app.js           # Frontend logic
│       └── style.css        # Dark theme styling
├── config/
│   ├── robot.yaml.example   # Example config (copy to robot.yaml)
│   └── profiles/            # Custom profiles (YAML)
├── pyproject.toml
└── .env                     # API keys (not in git)
```

## Communication Protocol

Communication between host and hub uses compact JSON over BLE UART to minimize bandwidth.

### Commands (host -> hub)

| Command | JSON | Description |
|---------|------|-------------|
| Read sensors | `{"c":"s"}` | Read all sensors |
| Motor speed | `{"c":"ms","p":"A","v":200}` | Run motor at deg/s |
| Motor degrees | `{"c":"md","p":"A","d":360,"v":200}` | Run N degrees |
| Motor stop | `{"c":"mx","p":"A"}` | Stop motor |
| Motor pair | `{"c":"mp","l":"A","r":"B","sl":200,"sr":200}` | Run two motors in sync |
| Display | `{"c":"di","i":"HAPPY"}` | Show icon on LED matrix |
| Sound | `{"c":"sn","f":440,"d":200}` | Play tone (Hz, ms) |
| Stop all | `{"c":"stop"}` | Emergency stop all motors |
| Ping | `{"c":"ping"}` | Connection test |

### Sensor Data (hub -> host)

```json
{
  "imu": {"h": 45.2, "p": 1.0, "r": -0.5, "a": [10, -5, 980]},
  "batt": 7200,
  "m_A": {"a": 1234, "s": 200},
  "d_E": 150,
  "c_F": {"h": 120, "s": 80, "v": 90}
}
```

### Available Icons

`HAPPY`, `SAD`, `HEART`, `ARROW_UP`, `ARROW_DOWN`, `ARROW_LEFT`, `ARROW_RIGHT`, `TRUE`, `FALSE`, `PAUSE`, `EMPTY`

## Safety

- **Distance safety**: Independent safety loop (10Hz) that overrides LLM on obstacles:
  - < 300mm: Multi-phase avoidance maneuver (reverse, then spin until clear)
- **Battery monitoring**: Automatically stops at < 10% battery
- **Shake detection**: Shaking the hub = emergency stop
- **Heartbeat**: Hub automatically stops motors after ~5 seconds without commands
- **Speed limits**: All profiles have max speed clamped in `BaseProfile`
- **Ctrl+C**: Sends stop command and cleanly stops the hub program

## LLM Support

| Provider | Model | Description |
|----------|-------|-------------|
| Anthropic | `claude-haiku-4-5-20251001` | Fast, cheap, good at JSON |
| Anthropic | `claude-sonnet-4-6` | Smarter, slightly slower |
| Ollama | `gemma4` | Free, local, no API key needed |
| Ollama | Any model | `ollama list` for available models |

Switch provider in `config/robot.yaml` or via the web UI.

## Technical Details

- **Context window**: Rolling 15 message pairs (30 messages)
- **BLE communication**: Via `pybricksdev` Python API (`PybricksHubBLE`)
- **Sensor polling**: 100ms (configurable per profile)
- **LLM cycle**: 400-600ms (configurable per profile)
- **Safety loop**: 100ms (distance), 50ms (battery/gesture)
- **Hub agent**: MicroPython with 10ms stdin polling and 5s heartbeat timeout

## License

MIT
