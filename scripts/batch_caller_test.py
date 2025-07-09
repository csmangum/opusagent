#!/usr/bin/env python3
"""
Batch Caller Testing Script

Runs multiple caller agent scenarios and generates comprehensive reports.
Supports parallel execution, stress testing, and performance analysis.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import statistics

from opusagent.caller_agent import (
    CallerAgent, PersonalityType, ScenarioType, CallerPersonality,
    CallerGoal, CallerScenario,
    create_difficult_card_replacement_caller,
    create_confused_elderly_caller,
    create_angry_complaint_caller
)
from opusagent.config.logging_config import configure_logging

logger = configure_logging("batch_caller_test")


@dataclass
class TestResult:
    """Individual test result."""
    scenario_name: str
    scenario_type: str
    personality_type: str
    caller_name: str
    start_time: datetime
    end_time: datetime
    duration: float
    success: bool
    conversation_turns: int
    goals_achieved: List[str]
    goals_total: int
    error_message: Optional[str] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate goal achievement rate."""
        if self.goals_total == 0:
            return 1.0 if self.success else 0.0
        return len(self.goals_achieved) / self.goals_total
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['start_time'] = self.start_time.isoformat()
        data['end_time'] = self.end_time.isoformat()
        return data


@dataclass 
class BatchTestResults:
    """Aggregated batch test results."""
    total_tests: int
    successful_tests: int
    failed_tests: int
    total_duration: float
    average_duration: float
    results: List[TestResult]
    
    @property
    def success_rate(self) -> float:
        """Overall success rate."""
        return self.successful_tests / self.total_tests if self.total_tests > 0 else 0.0
        
    def get_stats_by_personality(self) -> Dict[str, Dict[str, float]]:
        """Get statistics grouped by personality type."""
        personality_stats = {}
        
        for result in self.results:
            personality = result.personality_type
            if personality not in personality_stats:
                personality_stats[personality] = {
                    'total': 0,
                    'successful': 0,
                    'avg_duration': 0.0,
                    'avg_turns': 0.0,
                    'avg_goals': 0.0
                }
                
            stats = personality_stats[personality]
            stats['total'] += 1
            if result.success:
                stats['successful'] += 1
            stats['avg_duration'] += result.duration
            stats['avg_turns'] += result.conversation_turns
            stats['avg_goals'] += result.success_rate
            
        # Calculate averages
        for personality, stats in personality_stats.items():
            total = stats['total']
            stats['success_rate'] = stats['successful'] / total
            stats['avg_duration'] /= total
            stats['avg_turns'] /= total
            stats['avg_goals'] /= total
            
        return personality_stats
        
    def get_stats_by_scenario(self) -> Dict[str, Dict[str, float]]:
        """Get statistics grouped by scenario type."""
        scenario_stats = {}
        
        for result in self.results:
            scenario = result.scenario_type
            if scenario not in scenario_stats:
                scenario_stats[scenario] = {
                    'total': 0,
                    'successful': 0,
                    'avg_duration': 0.0,
                    'avg_turns': 0.0,
                    'avg_goals': 0.0
                }
                
            stats = scenario_stats[scenario]
            stats['total'] += 1
            if result.success:
                stats['successful'] += 1
            stats['avg_duration'] += result.duration
            stats['avg_turns'] += result.conversation_turns
            stats['avg_goals'] += result.success_rate
            
        # Calculate averages
        for scenario, stats in scenario_stats.items():
            total = stats['total']
            stats['success_rate'] = stats['successful'] / total
            stats['avg_duration'] /= total
            stats['avg_turns'] /= total
            stats['avg_goals'] /= total
            
        return scenario_stats


class BatchCallerTester:
    """Batch testing system for caller agents."""
    
    def __init__(self, bridge_url: str = "ws://localhost:8000/ws/telephony"):
        self.bridge_url = bridge_url
        self.results: List[TestResult] = []
        
    async def run_single_test(self, scenario_config: Dict[str, Any]) -> TestResult:
        """Run a single test scenario."""
        start_time = datetime.now()
        scenario_name = scenario_config.get("name", "Unknown")
        
        logger.info(f"Starting test: {scenario_name}")
        
        try:
            if scenario_config.get("type") == "predefined":
                result = await self._run_predefined_test(scenario_config)
            else:
                result = await self._run_custom_test(scenario_config)
                
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            test_result = TestResult(
                scenario_name=scenario_name,
                scenario_type=result.get("scenario_type", "unknown"),
                personality_type=result.get("personality", "unknown"),
                caller_name=result.get("caller_name", "unknown"),
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                success=result.get("success", False),
                conversation_turns=result.get("conversation_turns", 0),
                goals_achieved=result.get("goals_achieved", []),
                goals_total=result.get("goals_total", 0)
            )
            
            logger.info(f"Test completed: {scenario_name} - {'SUCCESS' if test_result.success else 'FAILED'}")
            return test_result
            
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logger.error(f"Test failed: {scenario_name} - {e}")
            
            return TestResult(
                scenario_name=scenario_name,
                scenario_type="unknown",
                personality_type="unknown", 
                caller_name="unknown",
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                success=False,
                conversation_turns=0,
                goals_achieved=[],
                goals_total=0,
                error_message=str(e)
            )
            
    async def _run_predefined_test(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run a predefined scenario test."""
        scenario_map = {
            "difficult_card_replacement": create_difficult_card_replacement_caller,
            "confused_elderly": create_confused_elderly_caller,
            "angry_complaint": create_angry_complaint_caller,
        }
        
        scenario = config["scenario"]
        caller_factory = scenario_map[scenario]
        timeout = config.get("timeout", 60.0)
        
        async with caller_factory(self.bridge_url) as caller:
            success = await caller.start_call(timeout=timeout)
            
            return {
                "scenario_type": caller.scenario.type.value,
                "personality": caller.personality.type.value,
                "caller_name": caller.caller_name,
                "success": success,
                "conversation_turns": caller.conversation_turns,
                "goals_achieved": caller.goals_achieved,
                "goals_total": len(caller.scenario.goal.success_criteria)
            }
            
    async def _run_custom_test(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run a custom scenario test."""
        # Create personality
        personality = self._create_personality(config["personality"])
        
        # Create goal
        goal = CallerGoal(
            primary_goal=config["goal"],
            secondary_goals=[],
            success_criteria=[config["goal"]],
            failure_conditions=["call failed"],
            max_conversation_turns=20
        )
        
        # Create scenario
        scenario = CallerScenario(
            scenario_type=ScenarioType(config["scenario_type"]),
            goal=goal,
            context={}
        )
        
        # Create caller
        caller = CallerAgent(
            bridge_url=self.bridge_url,
            personality=personality,
            scenario=scenario,
            caller_name=config.get("caller_name", "TestCaller"),
            caller_phone=config.get("caller_phone", "+15551234567")
        )
        
        timeout = config.get("timeout", 60.0)
        
        async with caller:
            success = await caller.start_call(timeout=timeout)
            
            return {
                "scenario_type": caller.scenario.type.value,
                "personality": caller.personality.type.value,
                "caller_name": caller.caller_name,
                "success": success,
                "conversation_turns": caller.conversation_turns,
                "goals_achieved": caller.goals_achieved,
                "goals_total": len(caller.scenario.goal.success_criteria)
            }
            
    def _create_personality(self, personality_type: str) -> CallerPersonality:
        """Create personality from type string."""
        configs = {
            "normal": ("polite", "Normal", 7, 6, 0.2, 0.8),
            "difficult": ("stubborn", "Confrontational", 3, 5, 0.7, 0.4),
            "confused": ("uncertain", "Confused", 6, 3, 0.1, 0.3),
            "angry": ("frustrated", "Aggressive", 2, 6, 0.9, 0.6),
            "elderly": ("polite", "Slow and careful", 8, 2, 0.1, 0.5),
            "impatient": ("rushed", "Hurried", 2, 7, 0.8, 0.7),
            "tech_savvy": ("knowledgeable", "Direct", 6, 9, 0.4, 0.9),
            "suspicious": ("distrustful", "Cautious", 5, 4, 0.3, 0.5)
        }
        
        trait, style, patience, tech, interrupt, clarity = configs.get(
            personality_type, configs["normal"]
        )
        
        return CallerPersonality(
            type=PersonalityType(personality_type),
            traits=[trait],
            communication_style=style,
            patience_level=patience,
            tech_comfort=tech,
            tendency_to_interrupt=interrupt,
            provides_clear_info=clarity
        )
        
    async def run_batch_tests(
        self, 
        scenarios: List[Dict[str, Any]], 
        parallel: bool = False,
        max_concurrent: int = 3,
        delay_between_tests: float = 2.0
    ) -> BatchTestResults:
        """Run batch tests with optional parallelization."""
        logger.info(f"Starting batch test with {len(scenarios)} scenarios")
        
        start_time = datetime.now()
        
        if parallel:
            # Run tests in parallel with concurrency limit
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def limited_test(scenario):
                async with semaphore:
                    return await self.run_single_test(scenario)
                    
            tasks = [limited_test(scenario) for scenario in scenarios]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle exceptions
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Scenario {i} failed with exception: {result}")
                    # Create error result
                    error_result = TestResult(
                        scenario_name=scenarios[i].get("name", f"Scenario {i}"),
                        scenario_type="unknown",
                        personality_type="unknown",
                        caller_name="unknown",
                        start_time=start_time,
                        end_time=datetime.now(),
                        duration=0.0,
                        success=False,
                        conversation_turns=0,
                        goals_achieved=[],
                        goals_total=0,
                        error_message=str(result)
                    )
                    processed_results.append(error_result)
                else:
                    processed_results.append(result)
                    
            results = processed_results
            
        else:
            # Run tests sequentially
            results = []
            for i, scenario in enumerate(scenarios):
                result = await self.run_single_test(scenario)
                results.append(result)
                
                # Delay between tests (except for last one)
                if i < len(scenarios) - 1:
                    await asyncio.sleep(delay_between_tests)
                    
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()
        
        successful_tests = sum(1 for r in results if r.success)
        failed_tests = len(results) - successful_tests
        avg_duration = total_duration / len(results) if results else 0.0
        
        batch_results = BatchTestResults(
            total_tests=len(results),
            successful_tests=successful_tests,
            failed_tests=failed_tests,
            total_duration=total_duration,
            average_duration=avg_duration,
            results=results
        )
        
        logger.info(f"Batch test completed: {successful_tests}/{len(results)} successful")
        
        return batch_results
        
    def generate_report(self, results: BatchTestResults, output_file: Optional[str] = None) -> str:
        """Generate a comprehensive test report."""
        report_lines = []
        
        # Header
        report_lines.append("=" * 80)
        report_lines.append("CALLER AGENT BATCH TEST REPORT")
        report_lines.append("=" * 80)
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
        
        # Summary
        report_lines.append("SUMMARY")
        report_lines.append("-" * 40)
        report_lines.append(f"Total Tests: {results.total_tests}")
        report_lines.append(f"Successful: {results.successful_tests} ({results.success_rate:.1%})")
        report_lines.append(f"Failed: {results.failed_tests}")
        report_lines.append(f"Total Duration: {results.total_duration:.1f}s")
        report_lines.append(f"Average Duration: {results.average_duration:.1f}s")
        report_lines.append("")
        
        # Duration statistics
        if results.results:
            durations = [r.duration for r in results.results]
            report_lines.append("DURATION STATISTICS")
            report_lines.append("-" * 40)
            report_lines.append(f"Min Duration: {min(durations):.1f}s")
            report_lines.append(f"Max Duration: {max(durations):.1f}s")
            report_lines.append(f"Median Duration: {statistics.median(durations):.1f}s")
            if len(durations) > 1:
                report_lines.append(f"Std Dev: {statistics.stdev(durations):.1f}s")
            report_lines.append("")
        
        # Personality breakdown
        personality_stats = results.get_stats_by_personality()
        if personality_stats:
            report_lines.append("PERSONALITY TYPE BREAKDOWN")
            report_lines.append("-" * 40)
            for personality, stats in personality_stats.items():
                report_lines.append(f"{personality.upper()}")
                report_lines.append(f"  Tests: {stats['total']}")
                report_lines.append(f"  Success Rate: {stats['success_rate']:.1%}")
                report_lines.append(f"  Avg Duration: {stats['avg_duration']:.1f}s")
                report_lines.append(f"  Avg Turns: {stats['avg_turns']:.1f}")
                report_lines.append(f"  Avg Goal Rate: {stats['avg_goals']:.1%}")
                report_lines.append("")
                
        # Scenario breakdown
        scenario_stats = results.get_stats_by_scenario()
        if scenario_stats:
            report_lines.append("SCENARIO TYPE BREAKDOWN")
            report_lines.append("-" * 40)
            for scenario, stats in scenario_stats.items():
                report_lines.append(f"{scenario.upper()}")
                report_lines.append(f"  Tests: {stats['total']}")
                report_lines.append(f"  Success Rate: {stats['success_rate']:.1%}")
                report_lines.append(f"  Avg Duration: {stats['avg_duration']:.1f}s")
                report_lines.append(f"  Avg Turns: {stats['avg_turns']:.1f}")
                report_lines.append(f"  Avg Goal Rate: {stats['avg_goals']:.1%}")
                report_lines.append("")
        
        # Individual results
        report_lines.append("INDIVIDUAL RESULTS")
        report_lines.append("-" * 40)
        for i, result in enumerate(results.results):
            status = "✅ PASS" if result.success else "❌ FAIL"
            report_lines.append(f"{i+1:2}. {status} {result.scenario_name}")
            report_lines.append(f"    Personality: {result.personality_type}")
            report_lines.append(f"    Duration: {result.duration:.1f}s")
            report_lines.append(f"    Turns: {result.conversation_turns}")
            report_lines.append(f"    Goals: {len(result.goals_achieved)}/{result.goals_total}")
            if result.error_message:
                report_lines.append(f"    Error: {result.error_message}")
            report_lines.append("")
            
        report = "\n".join(report_lines)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report)
            logger.info(f"Report saved to: {output_file}")
            
        return report
        
    def save_results_json(self, results: BatchTestResults, output_file: str):
        """Save detailed results as JSON."""
        data = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": results.total_tests,
                "successful_tests": results.successful_tests,
                "failed_tests": results.failed_tests,
                "success_rate": results.success_rate,
                "total_duration": results.total_duration,
                "average_duration": results.average_duration
            },
            "personality_stats": results.get_stats_by_personality(),
            "scenario_stats": results.get_stats_by_scenario(),
            "results": [result.to_dict() for result in results.results]
        }
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
            
        logger.info(f"JSON results saved to: {output_file}")


async def load_and_run_scenarios(
    scenarios_file: str = "scenarios.json",
    config_name: Optional[str] = None,
    bridge_url: str = "ws://localhost:8000/ws/telephony",
    parallel: bool = False,
    output_prefix: str = "test_results"
) -> BatchTestResults:
    """Load scenarios from file and run batch tests."""
    
    logger.info(f"Loading scenarios from: {scenarios_file}")
    
    with open(scenarios_file, 'r') as f:
        config = json.load(f)
        
    scenarios = config["scenarios"]
    
    # Apply test configuration if specified
    if config_name and config_name in config.get("test_configurations", {}):
        test_config = config["test_configurations"][config_name]
        scenario_indices = test_config["scenarios"]
        
        if scenario_indices == "all":
            selected_scenarios = scenarios
        else:
            selected_scenarios = [scenarios[i] for i in scenario_indices]
            
        parallel = test_config.get("parallel", parallel)
        
        # Handle repeat
        repeat_count = test_config.get("repeat", 1)
        if repeat_count > 1:
            repeated_scenarios = []
            for _ in range(repeat_count):
                repeated_scenarios.extend(selected_scenarios)
            selected_scenarios = repeated_scenarios
            
        logger.info(f"Using test configuration: {config_name}")
        logger.info(f"Running {len(selected_scenarios)} scenarios (repeat={repeat_count})")
        
    else:
        selected_scenarios = scenarios
        logger.info(f"Running all {len(selected_scenarios)} scenarios")
        
    # Run tests
    tester = BatchCallerTester(bridge_url)
    results = await tester.run_batch_tests(selected_scenarios, parallel=parallel)
    
    # Generate reports
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Text report
    report_file = f"{output_prefix}_{timestamp}.txt"
    report = tester.generate_report(results, report_file)
    print(report)
    
    # JSON results
    json_file = f"{output_prefix}_{timestamp}.json"
    tester.save_results_json(results, json_file)
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run batch caller agent tests")
    parser.add_argument("--scenarios", default="scenarios.json", help="Scenarios file")
    parser.add_argument("--config", help="Test configuration name")
    parser.add_argument("--bridge-url", default="ws://localhost:8000/ws/telephony", help="Bridge URL")
    parser.add_argument("--parallel", action="store_true", help="Run tests in parallel")
    parser.add_argument("--output", default="test_results", help="Output file prefix")
    
    args = parser.parse_args()
    
    try:
        asyncio.run(load_and_run_scenarios(
            scenarios_file=args.scenarios,
            config_name=args.config,
            bridge_url=args.bridge_url,
            parallel=args.parallel,
            output_prefix=args.output
        ))
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Test failed: {e}")
        exit(1) 