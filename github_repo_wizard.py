#!/usr/bin/env python3
"""
GitHub Repository Wizard CLI

Interactive command-line tool for managing GitHub repository configurations.
"""

import sys
import argparse
from pathlib import Path

# Add the project root to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from fazztv.utils.github_wizard import GitHubRepoWizard


def main():
    """Main entry point for the GitHub repository wizard."""
    parser = argparse.ArgumentParser(
        description="GitHub Repository Configuration Wizard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Run interactive wizard with default config
  %(prog)s -c repos.json     # Use custom config file
  %(prog)s --list            # List all configured repositories
  %(prog)s --add             # Jump straight to add repository
  %(prog)s --sync owner/repo # Sync specific repository
        """
    )

    parser.add_argument(
        '-c', '--config',
        default='github_repos.json',
        help='Configuration file path (default: github_repos.json)'
    )

    parser.add_argument(
        '-l', '--list',
        action='store_true',
        help='List all configured repositories and exit'
    )

    parser.add_argument(
        '-a', '--add',
        action='store_true',
        help='Add a new repository'
    )

    parser.add_argument(
        '-e', '--edit',
        metavar='REPO',
        help='Edit specific repository (format: owner/repo)'
    )

    parser.add_argument(
        '-d', '--delete',
        metavar='REPO',
        help='Delete specific repository (format: owner/repo)'
    )

    parser.add_argument(
        '-s', '--sync',
        metavar='REPO',
        help='Sync (pull) specific repository (format: owner/repo)'
    )

    parser.add_argument(
        '--clone',
        metavar='REPO',
        help='Clone specific repository (format: owner/repo)'
    )

    args = parser.parse_args()

    # Initialize wizard
    wizard = GitHubRepoWizard(args.config)

    # Handle specific actions
    if args.list:
        wizard.list_repositories()
        return

    if args.add:
        wizard.add_repository()
        return

    if args.edit:
        if args.edit not in wizard.repos:
            print(f"Repository {args.edit} not found.")
            wizard.list_repositories()
            return
        wizard.edit_repository(args.edit)
        return

    if args.delete:
        if args.delete not in wizard.repos:
            print(f"Repository {args.delete} not found.")
            wizard.list_repositories()
            return

        repo = wizard.repos[args.delete]
        wizard.display_repo(repo)

        if wizard.prompt_yes_no(f"\nDelete configuration for {args.delete}?"):
            del wizard.repos[args.delete]
            wizard.save_repos()
            print(f"✓ Deleted repository: {args.delete}")
        return

    if args.sync:
        if args.sync not in wizard.repos:
            print(f"Repository {args.sync} not found.")
            wizard.list_repositories()
            return

        repo = wizard.repos[args.sync]
        if not repo.local_path or not Path(repo.local_path).exists():
            print(f"Local clone not set up for {args.sync}")
            if wizard.prompt_yes_no("Set up local clone?"):
                local_path = wizard.prompt_input(
                    "Local path",
                    default=f"./{repo.name}"
                )
                repo.local_path = local_path
                wizard.save_repos()
                wizard.clone_repository(repo)
        else:
            print(f"Syncing {repo.full_name}...")
            try:
                from fazztv.utils.git_operations import GitOperations
                git_ops = GitOperations(str(repo.local_path))
                git_ops.pull("origin", repo.default_branch)
                print(f"✓ Successfully synced {repo.full_name}")
            except Exception as e:
                print(f"✗ Sync failed: {e}")
        return

    if args.clone:
        if args.clone not in wizard.repos:
            print(f"Repository {args.clone} not found.")
            wizard.list_repositories()
            return

        wizard.clone_repository(wizard.repos[args.clone])
        return

    # Run interactive wizard
    wizard.run()


if __name__ == "__main__":
    main()