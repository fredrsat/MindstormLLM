"""CLI entry point: python -m mindstorm"""
from __future__ import annotations
import argparse
import asyncio
import logging
import os
import sys
from dotenv import load_dotenv


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="MindstormLLM - LEGO Mindstorms 51515 controlled by LLM"
    )
    sub = parser.add_subparsers(dest="command")

    # --- run command ---
    run_parser = sub.add_parser("run", help="Start the robot with a profile")
    run_parser.add_argument(
        "profile",
        help="Profile to use (patrol, dog)",
    )
    run_parser.add_argument("--hub-name", help="BLE name of the hub (filter)")
    run_parser.add_argument("--verbose", "-v", action="store_true")

    # --- scan command ---
    sub.add_parser("scan", help="Scan for LEGO hubs via BLE")

    # --- profiles command ---
    sub.add_parser("profiles", help="Show available profiles")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    log_level = logging.DEBUG if getattr(args, "verbose", False) else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    if args.command == "scan":
        _cmd_scan()
    elif args.command == "profiles":
        _cmd_profiles()
    elif args.command == "run":
        _cmd_run(args)


def _cmd_scan():
    from mindstorm.ble.scanner import find_hubs

    async def do_scan():
        hubs = await find_hubs(timeout=10.0)
        if hubs:
            print(f"\nFound {len(hubs)} hub(s):")
            for h in hubs:
                print(f"  {h.name} - {h.address}")
        else:
            print("\nNo hubs found. Check that the hub is on and BLE is enabled.")

    asyncio.run(do_scan())


def _cmd_profiles():
    from mindstorm.profiles.registry import list_profiles

    print("\nAvailable profiles:\n")
    for name, desc in list_profiles():
        print(f"  {name:12s} {desc}")
    print()


def _cmd_run(args):
    from mindstorm.profiles.registry import get_profile
    from mindstorm.loop.controller import RobotController

    from mindstorm.config import load_robot_config
    config = load_robot_config()
    provider = config.get("llm", {}).get("provider", "anthropic")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if provider == "anthropic" and not api_key:
        print("Error: ANTHROPIC_API_KEY not set!")
        print("Add it to the .env file or export it as an environment variable.")
        sys.exit(1)

    profile = get_profile(args.profile)
    controller = RobotController(profile=profile, api_key=api_key)

    try:
        asyncio.run(controller.run(hub_name=args.hub_name))
    except KeyboardInterrupt:
        print("\nStopping...")


if __name__ == "__main__":
    main()
