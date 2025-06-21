#!/usr/bin/env python3
"""
Caller Agent CLI

Command-line interface for running intelligent caller agents against the bridge.
Allows testing different scenarios and personalities interactively.
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from caller_agent import (
    CallerAgent,
    CallerGoal,
    CallerPersonality,
    CallerScenario,
    PersonalityType,
    ScenarioType,
    create_angry_complaint_caller,
    create_confused_elderly_caller,
    create_difficult_card_replacement_caller,
)

from opusagent.config.logging_config import configure_logging

logger = configure_logging("caller_cli")


class CallerCLI:
    """Command-line interface for caller agent testing."""

    def __init__(self):
        self.bridge_url = "ws://localhost:8000/ws/telephony"
        self.results = []

    def parse_args(self) -> argparse.Namespace:
        """Parse command-line arguments."""
        parser = argparse.ArgumentParser(
            description="Run intelligent caller agents for testing",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Run a difficult card replacement caller
  python caller_cli.py --scenario difficult_card_replacement
  
  # Run custom scenario
  python caller_cli.py --personality angry --scenario card_replacement --goal "Replace stolen card"
  
  # Run batch test
  python caller_cli.py --batch scenarios.json
  
  # Interactive mode
  python caller_cli.py --interactive
            """,
        )

        parser.add_argument(
            "--bridge-url",
            default="ws://localhost:8000/ws/telephony",
            help="WebSocket URL for the bridge (default: %(default)s)",
        )

        parser.add_argument(
            "--scenario",
            choices=[
                "difficult_card_replacement",
                "confused_elderly",
                "angry_complaint",
                "custom",
            ],
            help="Predefined scenario to run",
        )

        parser.add_argument(
            "--personality",
            choices=[p.value for p in PersonalityType],
            help="Personality type for custom scenario",
        )

        parser.add_argument(
            "--scenario-type",
            choices=[s.value for s in ScenarioType],
            help="Scenario type for custom scenario",
        )

        parser.add_argument("--goal", help="Primary goal for custom scenario")

        parser.add_argument(
            "--caller-name",
            default="TestCaller",
            help="Name for the caller (default: %(default)s)",
        )

        parser.add_argument(
            "--caller-phone",
            default="+15551234567",
            help="Phone number for the caller (default: %(default)s)",
        )

        parser.add_argument(
            "--timeout",
            type=float,
            default=60.0,
            help="Call timeout in seconds (default: %(default)s)",
        )

        parser.add_argument("--batch", help="JSON file with batch scenarios to run")

        parser.add_argument(
            "--interactive", action="store_true", help="Run in interactive mode"
        )

        parser.add_argument("--output", help="Output file for results (JSON format)")

        parser.add_argument(
            "--verbose", "-v", action="store_true", help="Enable verbose logging"
        )

        return parser.parse_args()

    async def run_predefined_scenario(
        self, scenario_name: str, bridge_url: str, timeout: float
    ) -> Dict[str, Any]:
        """Run a predefined scenario."""
        logger.info(f"Running predefined scenario: {scenario_name}")

        scenario_map = {
            "difficult_card_replacement": create_difficult_card_replacement_caller,
            "confused_elderly": create_confused_elderly_caller,
            "angry_complaint": create_angry_complaint_caller,
        }

        if scenario_name not in scenario_map:
            raise ValueError(f"Unknown scenario: {scenario_name}")

        caller_factory = scenario_map[scenario_name]

        async with caller_factory(bridge_url) as caller:
            success = await caller.start_call(timeout=timeout)

            return {
                "scenario": scenario_name,
                "caller_name": caller.caller_name,
                "success": success,
                "conversation_turns": caller.conversation_turns,
                "goals_achieved": caller.goals_achieved,
                "personality": caller.personality.type.value,
                "scenario_type": caller.scenario.type.value,
            }

    async def run_custom_scenario(
        self,
        personality_type: str,
        scenario_type: str,
        goal: str,
        caller_name: str,
        caller_phone: str,
        bridge_url: str,
        timeout: float,
    ) -> Dict[str, Any]:
        """Run a custom scenario."""
        logger.info(f"Running custom scenario: {personality_type} {scenario_type}")

        # Create personality
        personality = self._create_personality(personality_type)

        # Create goal
        caller_goal = CallerGoal(
            primary_goal=goal,
            secondary_goals=[],
            success_criteria=["goal completed"],
            failure_conditions=["call failed"],
            max_conversation_turns=20,
        )

        # Create scenario
        scenario = CallerScenario(
            scenario_type=ScenarioType(scenario_type), goal=caller_goal, context={}
        )

        # Create caller
        caller = CallerAgent(
            bridge_url=bridge_url,
            personality=personality,
            scenario=scenario,
            caller_name=caller_name,
            caller_phone=caller_phone,
        )

        async with caller:
            success = await caller.start_call(timeout=timeout)

            return {
                "scenario": "custom",
                "caller_name": caller_name,
                "success": success,
                "conversation_turns": caller.conversation_turns,
                "goals_achieved": caller.goals_achieved,
                "personality": personality_type,
                "scenario_type": scenario_type,
                "goal": goal,
            }

    def _create_personality(self, personality_type: str) -> CallerPersonality:
        """Create a personality based on type."""
        personality_configs = {
            "normal": {
                "traits": ["polite", "cooperative", "clear"],
                "communication_style": "Normal and polite",
                "patience_level": 7,
                "tech_comfort": 6,
                "tendency_to_interrupt": 0.2,
                "provides_clear_info": 0.8,
            },
            "difficult": {
                "traits": ["stubborn", "argumentative", "suspicious"],
                "communication_style": "Confrontational and questioning",
                "patience_level": 3,
                "tech_comfort": 5,
                "tendency_to_interrupt": 0.7,
                "provides_clear_info": 0.4,
            },
            "confused": {
                "traits": ["uncertain", "needs clarification", "slow"],
                "communication_style": "Confused and asking for help",
                "patience_level": 6,
                "tech_comfort": 3,
                "tendency_to_interrupt": 0.1,
                "provides_clear_info": 0.3,
            },
            "angry": {
                "traits": ["frustrated", "demanding", "impatient"],
                "communication_style": "Aggressive and urgent",
                "patience_level": 2,
                "tech_comfort": 6,
                "tendency_to_interrupt": 0.9,
                "provides_clear_info": 0.6,
            },
            "elderly": {
                "traits": ["polite", "slow", "tech-uncomfortable"],
                "communication_style": "Polite but needs help",
                "patience_level": 8,
                "tech_comfort": 2,
                "tendency_to_interrupt": 0.1,
                "provides_clear_info": 0.5,
            },
        }

        config = personality_configs.get(
            personality_type, personality_configs["normal"]
        )

        return CallerPersonality(
            type=PersonalityType(personality_type),
            traits=config["traits"],
            communication_style=config["communication_style"],
            patience_level=config["patience_level"],
            tech_comfort=config["tech_comfort"],
            tendency_to_interrupt=config["tendency_to_interrupt"],
            provides_clear_info=config["provides_clear_info"],
        )

    async def run_batch_scenarios(
        self, batch_file: str, bridge_url: str
    ) -> List[Dict[str, Any]]:
        """Run batch scenarios from JSON file."""
        logger.info(f"Running batch scenarios from: {batch_file}")

        with open(batch_file, "r") as f:
            batch_config = json.load(f)

        results = []

        for i, scenario in enumerate(batch_config.get("scenarios", [])):
            logger.info(
                f"Running scenario {i+1}/{len(batch_config['scenarios'])}: {scenario.get('name', 'Unnamed')}"
            )

            try:
                if scenario.get("type") == "predefined":
                    result = await self.run_predefined_scenario(
                        scenario["scenario"], bridge_url, scenario.get("timeout", 60.0)
                    )
                else:
                    result = await self.run_custom_scenario(
                        scenario["personality"],
                        scenario["scenario_type"],
                        scenario["goal"],
                        scenario.get("caller_name", f"BatchCaller{i+1}"),
                        scenario.get("caller_phone", f"+155512345{i:02d}"),
                        bridge_url,
                        scenario.get("timeout", 60.0),
                    )

                result["batch_index"] = i
                result["scenario_name"] = scenario.get("name", f"Scenario {i+1}")
                results.append(result)

                # Log result
                status = "✅ SUCCESS" if result["success"] else "❌ FAILED"
                logger.info(
                    f"  {status} - {result['conversation_turns']} turns, {len(result['goals_achieved'])} goals achieved"
                )

                # Wait between scenarios
                await asyncio.sleep(2.0)

            except Exception as e:
                logger.error(f"  ❌ ERROR: {e}")
                results.append(
                    {
                        "batch_index": i,
                        "scenario_name": scenario.get("name", f"Scenario {i+1}"),
                        "success": False,
                        "error": str(e),
                    }
                )

        return results

    async def interactive_mode(self, bridge_url: str):
        """Run in interactive mode."""
        logger.info("Starting interactive mode")

        while True:
            print("\n" + "=" * 50)
            print("Caller Agent Interactive Mode")
            print("=" * 50)
            print("1. Difficult Card Replacement")
            print("2. Confused Elderly Caller")
            print("3. Angry Complaint")
            print("4. Custom Scenario")
            print("5. Batch Test")
            print("6. Exit")

            try:
                choice = input("\nSelect option (1-6): ").strip()

                if choice == "1":
                    result = await self.run_predefined_scenario(
                        "difficult_card_replacement", bridge_url, 60.0
                    )
                    self._print_result(result)

                elif choice == "2":
                    result = await self.run_predefined_scenario(
                        "confused_elderly", bridge_url, 60.0
                    )
                    self._print_result(result)

                elif choice == "3":
                    result = await self.run_predefined_scenario(
                        "angry_complaint", bridge_url, 60.0
                    )
                    self._print_result(result)

                elif choice == "4":
                    await self._interactive_custom_scenario(bridge_url)

                elif choice == "5":
                    batch_file = input("Enter batch file path: ").strip()
                    if Path(batch_file).exists():
                        results = await self.run_batch_scenarios(batch_file, bridge_url)
                        self._print_batch_results(results)
                    else:
                        print(f"File not found: {batch_file}")

                elif choice == "6":
                    print("Goodbye!")
                    break

                else:
                    print("Invalid choice. Please select 1-6.")

            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                logger.error(f"Error in interactive mode: {e}")

    async def _interactive_custom_scenario(self, bridge_url: str):
        """Interactive custom scenario creation."""
        print("\nCustom Scenario Setup")
        print("-" * 20)

        # Get inputs
        personality_options = [p.value for p in PersonalityType]
        print(f"Personality types: {', '.join(personality_options)}")
        personality = input("Enter personality type: ").strip()

        scenario_options = [s.value for s in ScenarioType]
        print(f"Scenario types: {', '.join(scenario_options)}")
        scenario_type = input("Enter scenario type: ").strip()

        goal = input("Enter primary goal: ").strip()
        caller_name = input("Enter caller name (optional): ").strip() or "CustomCaller"

        if (
            personality in personality_options
            and scenario_type in scenario_options
            and goal
        ):
            try:
                result = await self.run_custom_scenario(
                    personality,
                    scenario_type,
                    goal,
                    caller_name,
                    "+15551234567",
                    bridge_url,
                    60.0,
                )
                self._print_result(result)
            except Exception as e:
                print(f"Error running custom scenario: {e}")
        else:
            print("Invalid inputs. Please try again.")

    def _print_result(self, result: Dict[str, Any]):
        """Print a single result."""
        print(f"\nResult:")
        print(f"  Scenario: {result['scenario']}")
        print(f"  Success: {'✅' if result['success'] else '❌'}")
        print(f"  Conversation turns: {result['conversation_turns']}")
        print(f"  Goals achieved: {len(result['goals_achieved'])}")
        if result["goals_achieved"]:
            print(f"  Goals: {', '.join(result['goals_achieved'])}")

    def _print_batch_results(self, results: List[Dict[str, Any]]):
        """Print batch results summary."""
        print(f"\nBatch Results Summary:")
        print(f"Total scenarios: {len(results)}")

        successful = sum(1 for r in results if r.get("success", False))
        print(
            f"Successful: {successful}/{len(results)} ({successful/len(results)*100:.1f}%)"
        )

        print("\nDetailed Results:")
        for result in results:
            status = "✅" if result.get("success", False) else "❌"
            name = result.get("scenario_name", "Unknown")
            turns = result.get("conversation_turns", 0)
            goals = len(result.get("goals_achieved", []))
            print(f"  {status} {name}: {turns} turns, {goals} goals")

    def save_results(self, results: List[Dict[str, Any]], output_file: str):
        """Save results to JSON file."""
        output_data = {
            "timestamp": datetime.now().isoformat(),
            "total_scenarios": len(results),
            "successful_scenarios": sum(1 for r in results if r.get("success", False)),
            "results": results,
        }

        with open(output_file, "w") as f:
            json.dump(output_data, f, indent=2)

        logger.info(f"Results saved to: {output_file}")

    async def run(self):
        """Main entry point."""
        args = self.parse_args()

        if args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)

        self.bridge_url = args.bridge_url

        try:
            results = []

            if args.interactive:
                await self.interactive_mode(args.bridge_url)

            elif args.batch:
                results = await self.run_batch_scenarios(args.batch, args.bridge_url)
                self._print_batch_results(results)

            elif args.scenario:
                if args.scenario == "custom":
                    if not all([args.personality, args.scenario_type, args.goal]):
                        logger.error(
                            "Custom scenario requires --personality, --scenario-type, and --goal"
                        )
                        return 1

                    result = await self.run_custom_scenario(
                        args.personality,
                        args.scenario_type,
                        args.goal,
                        args.caller_name,
                        args.caller_phone,
                        args.bridge_url,
                        args.timeout,
                    )
                else:
                    result = await self.run_predefined_scenario(
                        args.scenario, args.bridge_url, args.timeout
                    )

                results = [result]
                self._print_result(result)

            else:
                logger.error("Must specify --scenario, --batch, or --interactive")
                return 1

            # Save results if requested
            if args.output and results:
                self.save_results(results, args.output)

            return 0

        except Exception as e:
            logger.error(f"Fatal error: {e}")
            return 1


async def main():
    """Main entry point."""
    from datetime import datetime

    cli = CallerCLI()
    exit_code = await cli.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
