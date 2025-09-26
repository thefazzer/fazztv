"""
GitHub Repository Configuration Wizard

Interactive CLI wizard for adding, editing, and managing GitHub repositories.
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import subprocess
from fazztv.utils.git_operations import GitOperations


@dataclass
class GitHubRepo:
    """Represents a GitHub repository configuration."""
    name: str
    owner: str
    url: str
    description: str = ""
    is_private: bool = False
    default_branch: str = "main"
    local_path: Optional[str] = None

    @property
    def full_name(self) -> str:
        """Return the full repository name (owner/repo)."""
        return f"{self.owner}/{self.name}"

    @property
    def clone_url(self) -> str:
        """Return the HTTPS clone URL."""
        return f"https://github.com/{self.owner}/{self.name}.git"

    @property
    def ssh_url(self) -> str:
        """Return the SSH clone URL."""
        return f"git@github.com:{self.owner}/{self.name}.git"


class GitHubRepoWizard:
    """Interactive wizard for managing GitHub repository configurations."""

    def __init__(self, config_file: str = "github_repos.json"):
        """
        Initialize the GitHub Repository Wizard.

        Args:
            config_file: Path to the JSON file storing repository configurations
        """
        self.config_file = Path(config_file)
        self.repos: Dict[str, GitHubRepo] = {}
        self.load_repos()

    def load_repos(self):
        """Load existing repository configurations from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    self.repos = {
                        key: GitHubRepo(**value)
                        for key, value in data.items()
                    }
            except (json.JSONDecodeError, TypeError) as e:
                print(f"Error loading config: {e}")
                self.repos = {}

    def save_repos(self):
        """Save repository configurations to file."""
        data = {
            key: asdict(repo)
            for key, repo in self.repos.items()
        }
        with open(self.config_file, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"✓ Saved {len(self.repos)} repositories to {self.config_file}")

    def validate_github_url(self, url: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate and parse a GitHub URL.

        Args:
            url: GitHub repository URL

        Returns:
            Tuple of (is_valid, owner, repo_name)
        """
        # Check for GitHub-specific patterns
        github_patterns = [
            r'github\.com[:/]([^/]+)/([^/\.]+)(?:\.git)?',
            r'^([^/]+)/([^/]+)$'  # Simple owner/repo format
        ]

        for pattern in github_patterns:
            match = re.search(pattern, url)
            if match:
                owner, repo = match.groups()
                # Additional validation for simple format
                if '/' not in pattern:  # Simple format
                    # Make sure it doesn't contain protocol or domain
                    if '://' in url or '.' in url.split('/')[0]:
                        continue
                return True, owner, repo.replace('.git', '')

        return False, None, None

    def prompt_input(self, prompt: str, default: str = "", required: bool = True) -> str:
        """
        Prompt user for input with optional default value.

        Args:
            prompt: The prompt message
            default: Default value (shown in brackets)
            required: Whether the field is required

        Returns:
            User input or default value
        """
        if default:
            prompt_text = f"{prompt} [{default}]: "
        else:
            prompt_text = f"{prompt}: "

        while True:
            value = input(prompt_text).strip()
            if not value and default:
                return default
            if not value and required:
                print("This field is required. Please enter a value.")
                continue
            return value

    def prompt_yes_no(self, prompt: str, default: bool = False) -> bool:
        """
        Prompt for yes/no confirmation.

        Args:
            prompt: The prompt message
            default: Default value

        Returns:
            Boolean response
        """
        default_text = "Y/n" if default else "y/N"
        response = input(f"{prompt} [{default_text}]: ").strip().lower()

        if not response:
            return default
        return response in ['y', 'yes']

    def add_repository(self):
        """Interactive wizard to add a new repository."""
        print("\n=== Add New GitHub Repository ===")

        # Get repository URL or name
        repo_input = self.prompt_input(
            "Enter GitHub URL or 'owner/repo' format"
        )

        is_valid, owner, name = self.validate_github_url(repo_input)

        if not is_valid:
            # Manual input if URL parsing failed
            owner = self.prompt_input("Repository owner/organization")
            name = self.prompt_input("Repository name")
        else:
            print(f"✓ Detected: {owner}/{name}")

        # Check if already exists
        full_name = f"{owner}/{name}"
        if full_name in self.repos:
            if self.prompt_yes_no(f"Repository {full_name} already exists. Update it?"):
                self.edit_repository(full_name)
            return

        # Get additional details
        description = self.prompt_input("Description", required=False)
        is_private = self.prompt_yes_no("Is this a private repository?")
        default_branch = self.prompt_input("Default branch", default="main")

        # Local path setup
        if self.prompt_yes_no("Set up local clone?"):
            local_path = self.prompt_input(
                "Local path",
                default=f"./{name}"
            )
        else:
            local_path = None

        # Create repository object
        repo = GitHubRepo(
            name=name,
            owner=owner,
            url=f"https://github.com/{owner}/{name}",
            description=description,
            is_private=is_private,
            default_branch=default_branch,
            local_path=local_path
        )

        # Clone if requested
        if local_path and not Path(local_path).exists():
            if self.prompt_yes_no("Clone repository now?"):
                self.clone_repository(repo)

        # Save
        self.repos[full_name] = repo
        self.save_repos()

        print(f"\n✓ Successfully added repository: {full_name}")
        self.display_repo(repo)

    def edit_repository(self, repo_key: Optional[str] = None):
        """
        Edit an existing repository configuration.

        Args:
            repo_key: Repository key (owner/name) or None to select
        """
        if not self.repos:
            print("No repositories configured. Add one first.")
            return

        if not repo_key:
            repo_key = self.select_repository()
            if not repo_key:
                return

        repo = self.repos[repo_key]
        print(f"\n=== Edit Repository: {repo_key} ===")
        self.display_repo(repo)

        # Edit fields
        print("\nPress Enter to keep current value, or enter new value:")

        repo.description = self.prompt_input(
            "Description",
            default=repo.description,
            required=False
        )

        repo.is_private = self.prompt_yes_no(
            "Is private?",
            default=repo.is_private
        )

        repo.default_branch = self.prompt_input(
            "Default branch",
            default=repo.default_branch
        )

        new_local_path = self.prompt_input(
            "Local path",
            default=repo.local_path or "",
            required=False
        )
        repo.local_path = new_local_path if new_local_path else None

        self.save_repos()
        print(f"\n✓ Updated repository: {repo_key}")

    def delete_repository(self):
        """Delete a repository configuration."""
        if not self.repos:
            print("No repositories configured.")
            return

        repo_key = self.select_repository()
        if not repo_key:
            return

        repo = self.repos[repo_key]
        self.display_repo(repo)

        if self.prompt_yes_no(f"\nDelete configuration for {repo_key}?"):
            del self.repos[repo_key]
            self.save_repos()
            print(f"✓ Deleted repository: {repo_key}")

    def list_repositories(self):
        """List all configured repositories."""
        if not self.repos:
            print("No repositories configured.")
            return

        print("\n=== Configured Repositories ===")
        for i, (key, repo) in enumerate(self.repos.items(), 1):
            status = "🔒" if repo.is_private else "📂"
            local = "✓" if repo.local_path and Path(repo.local_path).exists() else "✗"
            print(f"{i}. {status} {key} [Local: {local}]")
            if repo.description:
                print(f"   {repo.description}")

    def select_repository(self) -> Optional[str]:
        """
        Interactive repository selection.

        Returns:
            Selected repository key or None
        """
        self.list_repositories()

        try:
            choice = int(self.prompt_input("\nSelect repository number (0 to cancel)"))
            if choice == 0:
                return None

            keys = list(self.repos.keys())
            if 1 <= choice <= len(keys):
                return keys[choice - 1]
            else:
                print("Invalid selection.")
                return None
        except ValueError:
            print("Invalid input.")
            return None

    def display_repo(self, repo: GitHubRepo):
        """Display repository details."""
        print(f"\n  Repository: {repo.full_name}")
        print(f"  URL: {repo.url}")
        print(f"  Description: {repo.description or 'None'}")
        print(f"  Private: {'Yes' if repo.is_private else 'No'}")
        print(f"  Default Branch: {repo.default_branch}")
        print(f"  Local Path: {repo.local_path or 'Not set'}")
        if repo.local_path:
            exists = Path(repo.local_path).exists()
            print(f"  Local Clone: {'Exists' if exists else 'Not cloned'}")

    def clone_repository(self, repo: GitHubRepo):
        """
        Clone a repository to local path.

        Args:
            repo: Repository to clone
        """
        if not repo.local_path:
            print("No local path configured.")
            return

        local_path = Path(repo.local_path)
        if local_path.exists():
            print(f"Path {local_path} already exists.")
            return

        print(f"Cloning {repo.full_name} to {local_path}...")

        try:
            # Use GitOperations for reliable cloning
            git_ops = GitOperations()

            # Create parent directory if needed
            local_path.parent.mkdir(parents=True, exist_ok=True)

            # Clone the repository
            cmd = ["git", "clone", repo.clone_url, str(local_path)]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                print(f"✓ Successfully cloned to {local_path}")

                # Checkout default branch if different from main
                if repo.default_branch != "main":
                    git_ops_local = GitOperations(str(local_path))
                    subprocess.run(
                        ["git", "checkout", repo.default_branch],
                        cwd=str(local_path),
                        capture_output=True
                    )
            else:
                print(f"✗ Clone failed: {result.stderr}")

        except Exception as e:
            print(f"✗ Error cloning repository: {e}")

    def sync_repository(self):
        """Pull latest changes for a repository."""
        repo_key = self.select_repository()
        if not repo_key:
            return

        repo = self.repos[repo_key]
        if not repo.local_path:
            print("No local path configured for this repository.")
            if self.prompt_yes_no("Set up local clone?"):
                local_path = self.prompt_input(
                    "Local path",
                    default=f"./{repo.name}"
                )
                repo.local_path = local_path
                self.save_repos()
                self.clone_repository(repo)
            return

        local_path = Path(repo.local_path)
        if not local_path.exists():
            if self.prompt_yes_no("Local clone doesn't exist. Clone now?"):
                self.clone_repository(repo)
            return

        print(f"Syncing {repo.full_name}...")
        try:
            git_ops = GitOperations(str(local_path))
            git_ops.pull("origin", repo.default_branch)
            print(f"✓ Successfully synced {repo.full_name}")
        except Exception as e:
            print(f"✗ Sync failed: {e}")

    def run(self):
        """Run the interactive wizard main loop."""
        print("\n🚀 GitHub Repository Configuration Wizard")
        print("=" * 50)

        while True:
            print("\n=== Main Menu ===")
            print("1. Add repository")
            print("2. Edit repository")
            print("3. Delete repository")
            print("4. List repositories")
            print("5. Clone/Setup local repository")
            print("6. Sync repository (pull latest)")
            print("0. Exit")

            try:
                choice = int(self.prompt_input("Select option"))

                if choice == 0:
                    print("\n👋 Goodbye!")
                    break
                elif choice == 1:
                    self.add_repository()
                elif choice == 2:
                    self.edit_repository()
                elif choice == 3:
                    self.delete_repository()
                elif choice == 4:
                    self.list_repositories()
                elif choice == 5:
                    repo_key = self.select_repository()
                    if repo_key:
                        self.clone_repository(self.repos[repo_key])
                elif choice == 6:
                    self.sync_repository()
                else:
                    print("Invalid option.")

            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except ValueError:
                print("Invalid input. Please enter a number.")


def main():
    """Entry point for the GitHub repository wizard."""
    import sys

    # Allow custom config file via command line
    config_file = sys.argv[1] if len(sys.argv) > 1 else "github_repos.json"

    wizard = GitHubRepoWizard(config_file)
    wizard.run()


if __name__ == "__main__":
    main()