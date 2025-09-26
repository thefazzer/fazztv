# GitHub Repository Wizard

An interactive command-line wizard for managing GitHub repository configurations.

## Features

- **Interactive CLI**: User-friendly menu-driven interface
- **Repository Management**: Add, edit, delete, and list GitHub repositories
- **Local Cloning**: Set up and manage local clones of repositories
- **Sync Support**: Pull latest changes from remote repositories
- **Configuration Storage**: Save repository settings in JSON format
- **Validation**: Automatic GitHub URL parsing and validation
- **Integration**: Works with existing git operations utilities

## Installation

The wizard is included in the fazztv project. No additional installation required.

## Usage

### Interactive Mode

Run the wizard in interactive mode:

```bash
python3 github_repo_wizard.py
```

This opens the main menu where you can:
1. Add new repositories
2. Edit existing repositories
3. Delete repository configurations
4. List all configured repositories
5. Clone repositories locally
6. Sync (pull) latest changes

### Command-Line Options

```bash
# Use custom config file
python3 github_repo_wizard.py -c my_repos.json

# List all repositories
python3 github_repo_wizard.py --list

# Add a new repository directly
python3 github_repo_wizard.py --add

# Edit specific repository
python3 github_repo_wizard.py --edit owner/repo

# Delete specific repository
python3 github_repo_wizard.py --delete owner/repo

# Sync specific repository
python3 github_repo_wizard.py --sync owner/repo

# Clone specific repository
python3 github_repo_wizard.py --clone owner/repo
```

## Adding a Repository

When adding a repository, you can provide:
- GitHub URL (e.g., `https://github.com/owner/repo`)
- Short format (e.g., `owner/repo`)
- Manual entry (owner and name separately)

The wizard will prompt for:
- Repository description
- Whether it's private
- Default branch name
- Local clone path (optional)

## Configuration File

Repository configurations are stored in `github_repos.json` by default:

```json
{
  "owner/repo": {
    "name": "repo",
    "owner": "owner",
    "url": "https://github.com/owner/repo",
    "description": "Repository description",
    "is_private": false,
    "default_branch": "main",
    "local_path": "./repo"
  }
}
```

## Integration with Git Operations

The wizard integrates with the existing `GitOperations` class for:
- Reliable cloning with retry logic
- Safe pulling with fetch + merge strategy
- Error handling and timeout management

## Example Workflow

1. **Add a repository:**
   ```bash
   python3 github_repo_wizard.py --add
   ```
   Enter: `thefazzer/fazztv`

2. **Clone it locally:**
   ```bash
   python3 github_repo_wizard.py --clone thefazzer/fazztv
   ```

3. **Sync latest changes:**
   ```bash
   python3 github_repo_wizard.py --sync thefazzer/fazztv
   ```

4. **List all repositories:**
   ```bash
   python3 github_repo_wizard.py --list
   ```

## Security Notes

- The wizard stores repository metadata only
- No credentials or tokens are stored
- Uses HTTPS URLs by default for cloning
- Supports both public and private repository configurations

## Troubleshooting

### Clone fails with authentication error
- Ensure you have proper GitHub credentials configured
- Consider using SSH keys for private repositories

### Sync fails with merge conflicts
- The wizard uses safe merge strategies
- Manual conflict resolution may be required

### Configuration file issues
- The wizard validates JSON on load
- Corrupted configs are backed up and recreated