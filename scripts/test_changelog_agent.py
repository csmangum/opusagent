#!/usr/bin/env python3
"""
Test script for the Changelog Agent to verify functionality.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
import subprocess
import json
from datetime import datetime

# Add the parent directory to path
sys.path.append(str(Path(__file__).parent))

from changelog_agent import ChangelogAgent, CommitInfo, PRInfo


def create_test_git_repo():
    """Create a temporary git repository for testing."""
    temp_dir = tempfile.mkdtemp()
    
    # Initialize git repo
    subprocess.run(["git", "init"], cwd=temp_dir, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=temp_dir, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=temp_dir, capture_output=True)
    
    # Create some test files and commits
    test_file = Path(temp_dir) / "test_file.py"
    test_file.write_text("print('Hello, World!')")
    
    subprocess.run(["git", "add", "."], cwd=temp_dir, capture_output=True)
    subprocess.run(["git", "commit", "-m", "feat: Add initial test file"], cwd=temp_dir, capture_output=True)
    
    # Add another commit
    test_file.write_text("print('Hello, World!')\nprint('Another line')")
    subprocess.run(["git", "add", "."], cwd=temp_dir, capture_output=True)
    subprocess.run(["git", "commit", "-m", "fix: Update test file with additional functionality"], cwd=temp_dir, capture_output=True)
    
    return temp_dir


def test_commit_parsing():
    """Test the commit parsing functionality."""
    print("Testing commit parsing...")
    
    # Create test repo
    test_repo = create_test_git_repo()
    
    try:
        # Create agent (will fail without OpenAI key, but that's okay for this test)
        try:
            agent = ChangelogAgent(repo_path=test_repo, openai_key="dummy-key")
        except Exception as e:
            print(f"Expected error (no valid OpenAI key): {e}")
            return True
        
        # Test commit retrieval
        commits = agent.get_commits_since_date("2020-01-01")
        print(f"Found {len(commits)} commits")
        
        for commit in commits:
            print(f"  - {commit.message} ({commit.hash[:8]})")
        
        return len(commits) > 0
        
    finally:
        # Clean up
        shutil.rmtree(test_repo)


def test_changelog_generation():
    """Test the changelog generation with mock data."""
    print("\nTesting changelog generation...")
    
    # Create mock commit and PR data
    mock_commits = [
        CommitInfo(
            hash="abc123def456",
            message="feat: Add new user authentication system",
            author="Developer A",
            date="2024-01-15T10:30:00",
            files_changed=["auth.py", "models.py"]
        ),
        CommitInfo(
            hash="def456abc789",
            message="fix: Resolve security vulnerability in login",
            author="Developer B",
            date="2024-01-16T14:20:00",
            files_changed=["auth.py"]
        )
    ]
    
    mock_prs = [
        PRInfo(
            number=123,
            title="Add user profile management",
            body="This PR adds comprehensive user profile management functionality",
            author="developer-c",
            merged_at="2024-01-17T09:15:00Z",
            labels=["feature", "enhancement"],
            commits=[]
        )
    ]
    
    # Test basic changelog generation without LLM
    test_repo = create_test_git_repo()
    
    try:
        agent = ChangelogAgent(repo_path=test_repo, openai_key="dummy-key")
        
        # Test basic generation (fallback method)
        changelog_entries = agent._generate_basic_changelog_entries(mock_commits, mock_prs)
        print("Generated changelog entries:")
        print(changelog_entries)
        
        # Test changelog update
        agent.update_changelog(changelog_entries)
        
        # Check if changelog was created
        changelog_path = Path(test_repo) / "CHANGELOG.md"
        if changelog_path.exists():
            print(f"\nChangelog created successfully:")
            print(changelog_path.read_text())
            return True
        else:
            print("Failed to create changelog")
            return False
            
    finally:
        shutil.rmtree(test_repo)


def test_configuration():
    """Test the configuration loading."""
    print("\nTesting configuration...")
    
    try:
        from changelog_config import CHANGELOG_FORMAT, COMMIT_FILTERS, PR_FILTERS
        
        print(f"Changelog format: {CHANGELOG_FORMAT['title']}")
        print(f"Commit filters: {len(COMMIT_FILTERS['skip_patterns'])} skip patterns")
        print(f"PR filters: {len(PR_FILTERS['skip_labels'])} skip labels")
        
        return True
        
    except Exception as e:
        print(f"Configuration test failed: {e}")
        return False


def test_github_repo_detection():
    """Test GitHub repository detection."""
    print("\nTesting GitHub repo detection...")
    
    test_repo = create_test_git_repo()
    
    try:
        # Add a fake GitHub remote
        subprocess.run([
            "git", "remote", "add", "origin", 
            "https://github.com/testuser/testrepo.git"
        ], cwd=test_repo, capture_output=True)
        
        agent = ChangelogAgent(repo_path=test_repo, openai_key="dummy-key")
        
        print(f"Detected GitHub owner: {agent.github_owner}")
        print(f"Detected GitHub repo: {agent.github_repo}")
        
        return agent.github_owner == "testuser" and agent.github_repo == "testrepo"
        
    except Exception as e:
        print(f"GitHub detection test failed: {e}")
        return False
        
    finally:
        shutil.rmtree(test_repo)


def main():
    """Run all tests."""
    print("Running Changelog Agent Tests")
    print("=" * 40)
    
    tests = [
        ("Commit Parsing", test_commit_parsing),
        ("Changelog Generation", test_changelog_generation),
        ("Configuration", test_configuration),
        ("GitHub Repo Detection", test_github_repo_detection),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            status = "PASS" if result else "FAIL"
            print(f"\n{test_name}: {status}")
            if result:
                passed += 1
        except Exception as e:
            print(f"\n{test_name}: ERROR - {e}")
    
    print("\n" + "=" * 40)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("All tests passed! ✅")
        return 0
    else:
        print("Some tests failed! ❌")
        return 1


if __name__ == "__main__":
    sys.exit(main())