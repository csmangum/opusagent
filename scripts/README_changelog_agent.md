# Changelog Agent

An intelligent LLM-powered agent that automatically analyzes your git commits and pull requests to generate and maintain changelogs.

## Features

- **Automatic Analysis**: Scans git commits and merged PRs to identify changes
- **Intelligent Categorization**: Uses GPT-4 to categorize changes into Added, Changed, Fixed, etc.
- **Keep a Changelog Format**: Follows the standard [Keep a Changelog](https://keepachangelog.com/) format
- **Smart Filtering**: Ignores internal changes and focuses on user-facing modifications
- **GitHub Integration**: Fetches PR information and creates pull requests automatically
- **Customizable**: Configurable filtering, formatting, and behavior

## Prerequisites

1. **OpenAI API Key**: Required for LLM-powered changelog generation
2. **GitHub Token**: Optional but recommended for PR analysis and creation
3. **Git Repository**: Must be run from within a git repository

## Installation

The script will automatically install missing dependencies (`openai` and `GitPython`) when run.

Alternatively, install them manually:

```bash
pip install openai GitPython requests
```

## Setup

### Environment Variables

Create a `.env` file or set environment variables:

```bash
export OPENAI_API_KEY="your-openai-api-key"
export GITHUB_TOKEN="your-github-token"  # Optional but recommended
```

### GitHub Token

To create a GitHub token:

1. Go to GitHub Settings > Developer settings > Personal access tokens
2. Generate a new token with these scopes:
   - `repo` (for private repos) or `public_repo` (for public repos)
   - `pull_request` (to create PRs)

## Usage

### Basic Usage

Run the agent with default settings (analyzes last 30 days):

```bash
python scripts/changelog_agent.py
```

### Advanced Usage

```bash
# Analyze last 60 days without creating a PR
python scripts/changelog_agent.py --since-days 60 --no-pr

# Dry run (don't commit or create PR)
python scripts/changelog_agent.py --no-commit --no-pr

# Specify custom repository path
python scripts/changelog_agent.py --repo-path /path/to/repo

# Provide tokens directly
python scripts/changelog_agent.py --openai-key sk-... --github-token ghp_...
```

### Command Line Options

```
--repo-path         Path to git repository (default: current directory)
--since-days        Days to look back for changes (default: 30)
--github-token      GitHub API token
--openai-key        OpenAI API key
--no-commit         Don't commit changes to git
--no-pr             Don't create pull request
```

## How It Works

1. **Commit Analysis**: Scans git history for commits in the specified time period
2. **PR Analysis**: Fetches merged pull requests from GitHub API
3. **Content Filtering**: Filters out internal changes, merge commits, and documentation updates
4. **LLM Processing**: Uses GPT-4 to analyze changes and generate appropriate changelog entries
5. **Changelog Update**: Updates `CHANGELOG.md` with new entries in Keep a Changelog format
6. **Git Operations**: Commits changes and creates a pull request

## Changelog Format

The agent generates changelogs following the [Keep a Changelog](https://keepachangelog.com/) standard:

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- New feature descriptions

### Changed
- Modified functionality descriptions

### Fixed
- Bug fix descriptions

### Security
- Security-related changes
```

## Configuration

The agent uses `changelog_config.py` for customization:

- **Commit Filtering**: Patterns to skip or prioritize
- **PR Filtering**: Labels to consider or ignore
- **File Patterns**: Which file changes are significant
- **Format Settings**: Changelog structure and sections
- **OpenAI Settings**: Model, temperature, and prompts

## Examples

### Example 1: Weekly Changelog Update

```bash
# Run weekly to update changelog with recent changes
python scripts/changelog_agent.py --since-days 7
```

### Example 2: Release Preparation

```bash
# Generate changelog for upcoming release (30 days, no PR)
python scripts/changelog_agent.py --since-days 30 --no-pr
```

### Example 3: Initial Changelog Creation

```bash
# Create initial changelog from last 6 months
python scripts/changelog_agent.py --since-days 180
```

## Troubleshooting

### Common Issues

1. **"OpenAI API key is required"**
   - Set the `OPENAI_API_KEY` environment variable
   - Or pass `--openai-key` flag

2. **"GitHub token not provided"**
   - PR analysis will be skipped
   - Set `GITHUB_TOKEN` environment variable for full functionality

3. **"Invalid git repository"**
   - Ensure you're running from within a git repository
   - Or specify correct path with `--repo-path`

4. **"Could not determine GitHub repo info"**
   - Ensure your git remote is set to a GitHub repository
   - Check with `git remote -v`

### Debug Mode

For detailed logging, you can modify the script to increase verbosity or add debug prints.

## Customization

### Filtering Commits

Edit `changelog_config.py` to modify:

```python
COMMIT_FILTERS = {
    "skip_patterns": [
        r"^Merge branch",
        r"^Fix typo",
        # Add your patterns here
    ],
    "important_patterns": [
        r"^feat:",
        r"^fix:",
        # Add your patterns here
    ]
}
```

### PR Labels

Configure which PR labels to consider:

```python
PR_FILTERS = {
    "skip_labels": ["documentation", "internal"],
    "important_labels": ["breaking-change", "feature"]
}
```

### LLM Prompts

Customize the AI behavior by modifying the prompt in `generate_changelog_entries()`.

## Integration

### CI/CD Integration

Create a GitHub Action to run the changelog agent:

```yaml
name: Update Changelog
on:
  schedule:
    - cron: '0 0 * * 1'  # Weekly on Monday
  workflow_dispatch:

jobs:
  update-changelog:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run changelog agent
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: python scripts/changelog_agent.py --since-days 7
```

### Pre-commit Hook

Add to `.pre-commit-config.yaml`:

```yaml
- repo: local
  hooks:
    - id: changelog-agent
      name: Update Changelog
      entry: python scripts/changelog_agent.py --since-days 1 --no-pr
      language: system
      pass_filenames: false
      always_run: true
```

## Contributing

To enhance the changelog agent:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This tool is part of the FastAgent project and follows the same license terms.