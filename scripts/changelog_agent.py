#!/usr/bin/env python3
"""
Changelog Agent - An LLM-powered agent that analyzes commits and PRs to automatically
generate and maintain changelogs.
"""

import os
import re
import json
import subprocess
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import argparse
import requests
from dataclasses import dataclass
from pathlib import Path

# Add the parent directory to path so we can import from the main package
sys.path.append(str(Path(__file__).parent.parent))

try:
    import openai
except ImportError:
    print("OpenAI package not found. Installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "openai"])
    import openai

try:
    import git
except ImportError:
    print("GitPython package not found. Installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "GitPython"])
    import git


@dataclass
class ChangelogEntry:
    """Represents a single changelog entry."""
    version: str
    date: str
    changes: List[str]
    type: str  # 'added', 'changed', 'deprecated', 'removed', 'fixed', 'security'


@dataclass
class CommitInfo:
    """Represents commit information."""
    hash: str
    message: str
    author: str
    date: str
    files_changed: List[str]


@dataclass
class PRInfo:
    """Represents pull request information."""
    number: int
    title: str
    body: str
    author: str
    merged_at: str
    labels: List[str]
    commits: List[CommitInfo]


class ChangelogAgent:
    """Main agent class for changelog generation."""
    
    def __init__(self, repo_path: str = ".", github_token: str = None, openai_key: str = None):
        self.repo_path = repo_path
        self.github_token = github_token or os.getenv("GITHUB_TOKEN")
        self.openai_key = openai_key or os.getenv("OPENAI_API_KEY")
        
        if not self.openai_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable.")
        
        openai.api_key = self.openai_key
        
        # Initialize git repo
        try:
            self.repo = git.Repo(repo_path)
        except git.InvalidGitRepositoryError:
            raise ValueError(f"Invalid git repository at {repo_path}")
        
        # Get GitHub repo info
        try:
            self.github_owner, self.github_repo = self._get_github_repo_info()
        except ValueError as e:
            print(f"Warning: {e}. GitHub features will be limited.")
            self.github_owner, self.github_repo = None, None
        
        self.changelog_path = Path(repo_path) / "CHANGELOG.md"
        
    def _get_github_repo_info(self) -> Tuple[str, str]:
        """Extract GitHub owner and repo name from git remote."""
        try:
            # Check if origin remote exists
            if not any(r.name == 'origin' for r in self.repo.remotes):
                raise ValueError("No origin remote found")
            
            origin = self.repo.remotes.origin
            url = origin.url
            
            # Handle both SSH and HTTPS URLs
            if url.startswith("git@github.com:"):
                repo_path = url.replace("git@github.com:", "").replace(".git", "")
            elif url.startswith("https://github.com/"):
                repo_path = url.replace("https://github.com/", "").replace(".git", "")
            else:
                raise ValueError(f"Unsupported git remote URL: {url}")
            
            owner, repo = repo_path.split("/")
            return owner, repo
        except Exception as e:
            raise ValueError(f"Could not determine GitHub repo info: {e}")
    
    def _run_git_command(self, command: List[str]) -> str:
        """Run a git command and return output."""
        try:
            result = subprocess.run(
                ["git"] + command,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Git command failed: {e.stderr}")
    
    def get_commits_since_date(self, since_date: str) -> List[CommitInfo]:
        """Get commits since a specific date."""
        commits = []
        
        try:
            # Get commit log
            log_output = self._run_git_command([
                "log", 
                f"--since={since_date}",
                "--format=%H|%s|%an|%ad",
                "--date=iso"
            ])
            
            if not log_output:
                return commits
            
            for line in log_output.split("\n"):
                if line.strip():
                    parts = line.split("|")
                    if len(parts) >= 4:
                        hash_val = parts[0]
                        message = parts[1]
                        author = parts[2]
                        date = parts[3]
                        
                        # Get files changed in this commit
                        files_output = self._run_git_command([
                            "diff-tree", "--no-commit-id", "--name-only", "-r", hash_val
                        ])
                        files_changed = files_output.split("\n") if files_output else []
                        
                        commits.append(CommitInfo(
                            hash=hash_val,
                            message=message,
                            author=author,
                            date=date,
                            files_changed=files_changed
                        ))
        except Exception as e:
            print(f"Error getting commits: {e}")
        
        return commits
    
    def get_merged_prs_since_date(self, since_date: str) -> List[PRInfo]:
        """Get merged PRs since a specific date."""
        if not self.github_token:
            print("GitHub token not provided. Skipping PR analysis.")
            return []
        
        if not self.github_owner or not self.github_repo:
            print("GitHub repository info not available. Skipping PR analysis.")
            return []
        
        prs = []
        
        try:
            # Convert date to ISO format
            since_dt = datetime.fromisoformat(since_date.replace("Z", "+00:00"))
            since_iso = since_dt.isoformat()
            
            # GitHub API endpoint
            url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/pulls"
            
            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            params = {
                "state": "closed",
                "sort": "updated",
                "direction": "desc",
                "per_page": 100
            }
            
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            for pr_data in response.json():
                if (pr_data["merged_at"] and 
                    datetime.fromisoformat(pr_data["merged_at"].replace("Z", "+00:00")) >= since_dt):
                    
                    # Get PR commits
                    commits_url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/pulls/{pr_data['number']}/commits"
                    commits_response = requests.get(commits_url, headers=headers)
                    commits_response.raise_for_status()
                    
                    commits = []
                    for commit_data in commits_response.json():
                        commits.append(CommitInfo(
                            hash=commit_data["sha"],
                            message=commit_data["commit"]["message"],
                            author=commit_data["commit"]["author"]["name"],
                            date=commit_data["commit"]["author"]["date"],
                            files_changed=[]  # We'll get this separately if needed
                        ))
                    
                    prs.append(PRInfo(
                        number=pr_data["number"],
                        title=pr_data["title"],
                        body=pr_data["body"] or "",
                        author=pr_data["user"]["login"],
                        merged_at=pr_data["merged_at"],
                        labels=[label["name"] for label in pr_data["labels"]],
                        commits=commits
                    ))
        
        except Exception as e:
            print(f"Error getting PRs: {e}")
        
        return prs
    
    def read_existing_changelog(self) -> str:
        """Read existing changelog content."""
        if self.changelog_path.exists():
            return self.changelog_path.read_text()
        return ""
    
    def generate_changelog_entries(self, commits: List[CommitInfo], prs: List[PRInfo], 
                                 existing_changelog: str) -> str:
        """Use LLM to generate changelog entries."""
        
        # Prepare context for LLM
        context = {
            "commits": [
                {
                    "hash": commit.hash[:8],
                    "message": commit.message,
                    "author": commit.author,
                    "date": commit.date,
                    "files_changed": commit.files_changed
                }
                for commit in commits
            ],
            "prs": [
                {
                    "number": pr.number,
                    "title": pr.title,
                    "body": pr.body,
                    "author": pr.author,
                    "merged_at": pr.merged_at,
                    "labels": pr.labels
                }
                for pr in prs
            ]
        }
        
        prompt = f"""
You are a technical writer helping to generate changelog entries from git commits and pull requests. 

Analyze the following commits and pull requests, and generate appropriate changelog entries following the "Keep a Changelog" format:

## Commits:
{json.dumps(context['commits'], indent=2)}

## Pull Requests:
{json.dumps(context['prs'], indent=2)}

## Existing Changelog:
{existing_changelog[:2000]}...

Please generate new changelog entries that:
1. Follow the "Keep a Changelog" format (https://keepachangelog.com/)
2. Group changes by type: Added, Changed, Deprecated, Removed, Fixed, Security
3. Focus on user-facing changes, not internal refactoring
4. Use clear, concise language
5. Don't duplicate entries already in the existing changelog
6. Include PR numbers in brackets when available

Format your response as a markdown section that can be added to the changelog, starting with a version header like:

## [Unreleased]

### Added
- New feature descriptions

### Changed
- Modified functionality descriptions

### Fixed
- Bug fix descriptions

Only include sections that have actual changes. If a commit or PR is purely internal (refactoring, tests, etc.), you may skip it unless it has user-facing implications.
"""

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a technical writer specializing in changelog generation."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            print(f"Error generating changelog entries: {e}")
            return self._generate_basic_changelog_entries(commits, prs)
    
    def _generate_basic_changelog_entries(self, commits: List[CommitInfo], prs: List[PRInfo]) -> str:
        """Generate basic changelog entries without LLM."""
        entries = ["## [Unreleased]", ""]
        
        if prs:
            entries.append("### Changed")
            for pr in prs:
                entries.append(f"- {pr.title} [#{pr.number}]")
            entries.append("")
        
        if commits:
            entries.append("### Commits")
            for commit in commits:
                # Skip merge commits
                if not commit.message.startswith("Merge"):
                    entries.append(f"- {commit.message} ({commit.hash[:8]})")
            entries.append("")
        
        return "\n".join(entries)
    
    def update_changelog(self, new_entries: str) -> None:
        """Update the changelog file with new entries."""
        existing_content = self.read_existing_changelog()
        
        if not existing_content:
            # Create new changelog
            header = """# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

"""
            full_content = header + new_entries
        else:
            # Insert new entries after header
            lines = existing_content.split('\n')
            header_end = 0
            
            # Find where to insert new entries
            for i, line in enumerate(lines):
                if line.startswith('## ['):
                    header_end = i
                    break
            
            if header_end == 0:
                # No existing entries, add after header
                full_content = existing_content + "\n" + new_entries
            else:
                # Insert before first version
                new_lines = lines[:header_end] + [new_entries, ""] + lines[header_end:]
                full_content = '\n'.join(new_lines)
        
        self.changelog_path.write_text(full_content)
        print(f"Updated changelog at {self.changelog_path}")
    
    def commit_changes(self, message: str = "Update changelog") -> None:
        """Commit the changelog changes."""
        try:
            self.repo.index.add([str(self.changelog_path)])
            self.repo.index.commit(message)
            print(f"Committed changes: {message}")
        except Exception as e:
            print(f"Error committing changes: {e}")
    
    def create_pull_request(self, branch_name: str = "update-changelog", 
                          title: str = "Update changelog", 
                          body: str = "Automated changelog update") -> None:
        """Create a pull request with changelog changes."""
        if not self.github_token:
            print("GitHub token not provided. Cannot create PR.")
            return
        
        if not self.github_owner or not self.github_repo:
            print("GitHub repository info not available. Cannot create PR.")
            return
        
        try:
            # Create and push branch
            current_branch = self.repo.active_branch.name
            
            # Create new branch
            new_branch = self.repo.create_head(branch_name)
            new_branch.checkout()
            
            # Push branch
            origin = self.repo.remotes.origin
            origin.push(new_branch)
            
            # Create PR via GitHub API
            url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/pulls"
            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            data = {
                "title": title,
                "body": body,
                "head": branch_name,
                "base": current_branch
            }
            
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            
            pr_data = response.json()
            print(f"Created PR #{pr_data['number']}: {pr_data['html_url']}")
            
            # Switch back to original branch
            self.repo.heads[current_branch].checkout()
            
        except Exception as e:
            print(f"Error creating PR: {e}")
    
    def run(self, since_days: int = 30, commit_changes: bool = True, 
            create_pr: bool = True) -> None:
        """Run the changelog agent."""
        print("Starting changelog agent...")
        
        # Calculate since date
        since_date = (datetime.now() - timedelta(days=since_days)).isoformat()
        
        print(f"Analyzing changes since {since_date}")
        
        # Get commits and PRs
        commits = self.get_commits_since_date(since_date)
        prs = self.get_merged_prs_since_date(since_date)
        
        print(f"Found {len(commits)} commits and {len(prs)} PRs")
        
        if not commits and not prs:
            print("No changes found. Nothing to update.")
            return
        
        # Read existing changelog
        existing_changelog = self.read_existing_changelog()
        
        # Generate new entries
        print("Generating changelog entries...")
        new_entries = self.generate_changelog_entries(commits, prs, existing_changelog)
        
        # Update changelog
        self.update_changelog(new_entries)
        
        # Commit changes
        if commit_changes:
            self.commit_changes("Update changelog with recent changes")
        
        # Create PR
        if create_pr:
            self.create_pull_request(
                title="Update changelog with recent changes",
                body=f"Automated changelog update covering {len(commits)} commits and {len(prs)} PRs from the last {since_days} days."
            )
        
        print("Changelog agent completed!")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Changelog Agent - Automated changelog generation")
    parser.add_argument("--repo-path", default=".", help="Path to git repository")
    parser.add_argument("--since-days", type=int, default=30, help="Days to look back for changes")
    parser.add_argument("--github-token", help="GitHub API token")
    parser.add_argument("--openai-key", help="OpenAI API key")
    parser.add_argument("--no-commit", action="store_true", help="Don't commit changes")
    parser.add_argument("--no-pr", action="store_true", help="Don't create PR")
    
    args = parser.parse_args()
    
    try:
        agent = ChangelogAgent(
            repo_path=args.repo_path,
            github_token=args.github_token,
            openai_key=args.openai_key
        )
        
        agent.run(
            since_days=args.since_days,
            commit_changes=not args.no_commit,
            create_pr=not args.no_pr
        )
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()