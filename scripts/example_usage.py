#!/usr/bin/env python3
"""
Example usage of the Changelog Agent.
This script demonstrates how to use the changelog agent with different configurations.
"""

import os
import sys
from pathlib import Path

# Add the scripts directory to path
sys.path.append(str(Path(__file__).parent))

from changelog_agent import ChangelogAgent


def example_basic_usage():
    """Example 1: Basic usage with environment variables."""
    print("Example 1: Basic usage")
    print("=" * 40)
    
    # Assumes OPENAI_API_KEY and GITHUB_TOKEN are set in environment
    try:
        agent = ChangelogAgent()
        
        # Run with default settings (last 30 days)
        agent.run()
        
    except ValueError as e:
        print(f"Error: {e}")
        print("Make sure to set OPENAI_API_KEY environment variable")


def example_custom_timeframe():
    """Example 2: Custom timeframe and no PR creation."""
    print("\nExample 2: Custom timeframe (last 7 days, no PR)")
    print("=" * 40)
    
    try:
        agent = ChangelogAgent()
        
        # Run for last 7 days without creating a PR
        agent.run(since_days=7, create_pr=False)
        
    except ValueError as e:
        print(f"Error: {e}")
        print("Make sure to set OPENAI_API_KEY environment variable")


def example_dry_run():
    """Example 3: Dry run (no commits, no PR)."""
    print("\nExample 3: Dry run (no commits, no PR)")
    print("=" * 40)
    
    try:
        agent = ChangelogAgent()
        
        # Run without committing changes or creating PR
        agent.run(since_days=14, commit_changes=False, create_pr=False)
        
    except ValueError as e:
        print(f"Error: {e}")
        print("Make sure to set OPENAI_API_KEY environment variable")


def example_with_api_keys():
    """Example 4: Providing API keys directly."""
    print("\nExample 4: Providing API keys directly")
    print("=" * 40)
    
    # Example with API keys provided directly
    openai_key = os.getenv("OPENAI_API_KEY") or "your-openai-key-here"
    github_token = os.getenv("GITHUB_TOKEN") or "your-github-token-here"
    
    try:
        agent = ChangelogAgent(
            openai_key=openai_key,
            github_token=github_token
        )
        
        # Run with custom settings
        agent.run(since_days=30, commit_changes=False, create_pr=False)
        
    except ValueError as e:
        print(f"Error: {e}")


def example_manual_steps():
    """Example 5: Manual step-by-step execution."""
    print("\nExample 5: Manual step-by-step execution")
    print("=" * 40)
    
    try:
        agent = ChangelogAgent()
        
        # Step 1: Get commits from last 30 days
        commits = agent.get_commits_since_date("2024-01-01")
        print(f"Found {len(commits)} commits")
        
        # Step 2: Get PRs from last 30 days
        prs = agent.get_merged_prs_since_date("2024-01-01")
        print(f"Found {len(prs)} PRs")
        
        # Step 3: Read existing changelog
        existing_changelog = agent.read_existing_changelog()
        print(f"Existing changelog: {len(existing_changelog)} characters")
        
        # Step 4: Generate new entries
        if commits or prs:
            new_entries = agent.generate_changelog_entries(commits, prs, existing_changelog)
            print(f"Generated entries:\n{new_entries}")
            
            # Step 5: Update changelog
            agent.update_changelog(new_entries)
            print("Changelog updated successfully!")
            
            # Optional: Commit changes
            # agent.commit_changes("Update changelog with recent changes")
            
            # Optional: Create PR
            # agent.create_pull_request()
        else:
            print("No changes found to add to changelog.")
        
    except ValueError as e:
        print(f"Error: {e}")


def main():
    """Run all examples."""
    print("Changelog Agent - Example Usage")
    print("=" * 50)
    
    # Check if we have the required environment variables
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  OPENAI_API_KEY environment variable not set.")
        print("   Set it with: export OPENAI_API_KEY='your-key-here'")
        print("   Or provide it directly in the script.")
        print()
    
    if not os.getenv("GITHUB_TOKEN"):
        print("ℹ️  GITHUB_TOKEN environment variable not set.")
        print("   GitHub features will be limited.")
        print("   Set it with: export GITHUB_TOKEN='your-token-here'")
        print()
    
    # Run examples
    examples = [
        example_basic_usage,
        example_custom_timeframe,
        example_dry_run,
        example_with_api_keys,
        example_manual_steps
    ]
    
    for example in examples:
        try:
            example()
        except KeyboardInterrupt:
            print("\n\nExecution interrupted by user.")
            break
        except Exception as e:
            print(f"Example failed: {e}")


if __name__ == "__main__":
    main()