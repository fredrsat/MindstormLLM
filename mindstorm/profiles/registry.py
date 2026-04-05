"""Profile registry: discover and load behavior profiles by name."""
from __future__ import annotations
from pathlib import Path
import yaml
from mindstorm.profiles.base import BaseProfile
from mindstorm.profiles.patrol import PatrolProfile
from mindstorm.profiles.dog import DogProfile

BUILTIN: dict[str, type[BaseProfile]] = {
    "patrol": PatrolProfile,
    "dog": DogProfile,
}

CUSTOM_DIR = Path(__file__).parent.parent.parent / "config" / "profiles"


def _load_custom(name: str) -> BaseProfile | None:
    """Try to load a custom profile YAML."""
    path = CUSTOM_DIR / f"{name}.yaml"
    if not path.exists():
        return None
    with open(path) as f:
        data = yaml.safe_load(f)
    from mindstorm.profiles.custom import CustomProfile
    return CustomProfile(data)


def get_profile(name: str) -> BaseProfile:
    # Built-in profiles first
    cls = BUILTIN.get(name)
    if cls is not None:
        return cls()

    # Try custom YAML profile
    custom = _load_custom(name)
    if custom is not None:
        return custom

    available = list(BUILTIN.keys()) + [
        p.stem for p in CUSTOM_DIR.glob("*.yaml")
    ] if CUSTOM_DIR.exists() else list(BUILTIN.keys())
    raise ValueError(f"Unknown profile '{name}'. Available: {', '.join(available)}")


def list_profiles() -> list[tuple[str, str]]:
    profiles = [(name, cls().description) for name, cls in BUILTIN.items()]
    if CUSTOM_DIR.exists():
        for path in sorted(CUSTOM_DIR.glob("*.yaml")):
            with open(path) as f:
                data = yaml.safe_load(f)
            profiles.append((path.stem, data.get("description", "")))
    return profiles
