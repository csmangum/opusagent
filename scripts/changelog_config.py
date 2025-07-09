"""
Configuration file for the Changelog Agent.
"""

# Changelog format settings
CHANGELOG_FORMAT = {
    "title": "# Changelog",
    "description": """
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
""",
    "section_order": ["Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"],
    "unreleased_header": "## [Unreleased]"
}

# OpenAI settings
OPENAI_SETTINGS = {
    "model": "gpt-4",
    "max_tokens": 2000,
    "temperature": 0.3,
    "system_prompt": "You are a technical writer specializing in changelog generation."
}

# GitHub settings
GITHUB_SETTINGS = {
    "per_page": 100,
    "api_version": "application/vnd.github.v3+json"
}

# Commit filtering settings
COMMIT_FILTERS = {
    "skip_merge_commits": True,
    "skip_patterns": [
        r"^Merge branch",
        r"^Merge pull request",
        r"^Update.*\.md$",
        r"^Fix typo",
        r"^Update README",
        r"^Update .gitignore"
    ],
    "important_patterns": [
        r"^feat:",
        r"^fix:",
        r"^break:",
        r"^add:",
        r"^remove:",
        r"^change:",
        r"^update:",
        r"^improve:",
        r"^refactor:",
        r"^docs:",
        r"^test:"
    ]
}

# PR filtering settings
PR_FILTERS = {
    "skip_labels": ["documentation", "internal", "chore"],
    "important_labels": ["breaking-change", "feature", "bugfix", "enhancement"]
}

# File patterns to consider for changelog impact
SIGNIFICANT_FILE_PATTERNS = [
    r".*\.py$",
    r".*\.js$",
    r".*\.ts$",
    r".*\.jsx$",
    r".*\.tsx$",
    r".*\.go$",
    r".*\.rs$",
    r".*\.java$",
    r".*\.cpp$",
    r".*\.c$",
    r".*\.h$",
    r".*\.hpp$",
    r"requirements\.txt$",
    r"package\.json$",
    r"Cargo\.toml$",
    r"pom\.xml$",
    r".*\.sql$",
    r".*\.yml$",
    r".*\.yaml$",
    r"Dockerfile$",
    r"docker-compose\.yml$"
]

# Patterns to ignore for changelog
IGNORE_FILE_PATTERNS = [
    r".*\.md$",
    r".*\.txt$",
    r".*\.log$",
    r".*test.*",
    r".*spec.*",
    r".*\.gitignore$",
    r".*\.DS_Store$",
    r".*/__pycache__/.*",
    r".*/node_modules/.*",
    r".*/venv/.*",
    r".*/\.git/.*"
]

# Default branch settings
DEFAULT_BRANCH = "main"
CHANGELOG_BRANCH_PREFIX = "update-changelog"

# Date format settings
DATE_FORMAT = "%Y-%m-%d"
ISO_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"