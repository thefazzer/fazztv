"""
Test suite for GitHub Repository Wizard
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from fazztv.utils.github_wizard import GitHubRepo, GitHubRepoWizard


class TestGitHubRepo(unittest.TestCase):
    """Test GitHubRepo dataclass."""

    def test_repo_creation(self):
        """Test creating a repository object."""
        repo = GitHubRepo(
            name="test-repo",
            owner="testuser",
            url="https://github.com/testuser/test-repo",
            description="Test repository",
            is_private=True,
            default_branch="main",
            local_path="/path/to/repo"
        )

        self.assertEqual(repo.name, "test-repo")
        self.assertEqual(repo.owner, "testuser")
        self.assertEqual(repo.full_name, "testuser/test-repo")
        self.assertEqual(repo.clone_url, "https://github.com/testuser/test-repo.git")
        self.assertEqual(repo.ssh_url, "git@github.com:testuser/test-repo.git")
        self.assertTrue(repo.is_private)

    def test_repo_defaults(self):
        """Test repository with default values."""
        repo = GitHubRepo(
            name="minimal",
            owner="user",
            url="https://github.com/user/minimal"
        )

        self.assertEqual(repo.description, "")
        self.assertFalse(repo.is_private)
        self.assertEqual(repo.default_branch, "main")
        self.assertIsNone(repo.local_path)


class TestGitHubRepoWizard(unittest.TestCase):
    """Test GitHubRepoWizard class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_file = tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.json',
            delete=False
        )
        self.temp_file.close()
        self.wizard = GitHubRepoWizard(self.temp_file.name)

    def tearDown(self):
        """Clean up test fixtures."""
        Path(self.temp_file.name).unlink(missing_ok=True)

    def test_validate_github_url(self):
        """Test GitHub URL validation."""
        test_cases = [
            ("https://github.com/owner/repo", True, "owner", "repo"),
            ("https://github.com/owner/repo.git", True, "owner", "repo"),
            ("git@github.com:owner/repo.git", True, "owner", "repo"),
            ("github.com/owner/repo", True, "owner", "repo"),
            ("owner/repo", True, "owner", "repo"),
            ("invalid-url", False, None, None),
            ("https://gitlab.com/owner/repo", False, None, None),
        ]

        for url, expected_valid, expected_owner, expected_repo in test_cases:
            is_valid, owner, repo = self.wizard.validate_github_url(url)
            self.assertEqual(is_valid, expected_valid, f"Failed for URL: {url}")
            if expected_valid:
                self.assertEqual(owner, expected_owner)
                self.assertEqual(repo, expected_repo)

    def test_save_and_load_repos(self):
        """Test saving and loading repository configurations."""
        # Add test repositories
        repo1 = GitHubRepo(
            name="repo1",
            owner="owner1",
            url="https://github.com/owner1/repo1",
            description="First repo"
        )
        repo2 = GitHubRepo(
            name="repo2",
            owner="owner2",
            url="https://github.com/owner2/repo2",
            is_private=True
        )

        self.wizard.repos = {
            "owner1/repo1": repo1,
            "owner2/repo2": repo2
        }

        # Save repositories
        self.wizard.save_repos()

        # Create new wizard instance and load
        new_wizard = GitHubRepoWizard(self.temp_file.name)

        # Verify loaded data
        self.assertEqual(len(new_wizard.repos), 2)
        self.assertIn("owner1/repo1", new_wizard.repos)
        self.assertIn("owner2/repo2", new_wizard.repos)

        loaded_repo1 = new_wizard.repos["owner1/repo1"]
        self.assertEqual(loaded_repo1.name, "repo1")
        self.assertEqual(loaded_repo1.description, "First repo")
        self.assertFalse(loaded_repo1.is_private)

        loaded_repo2 = new_wizard.repos["owner2/repo2"]
        self.assertEqual(loaded_repo2.name, "repo2")
        self.assertTrue(loaded_repo2.is_private)

    def test_empty_config_file(self):
        """Test handling of empty/missing config file."""
        # Delete the temp file to simulate missing config
        Path(self.temp_file.name).unlink()

        wizard = GitHubRepoWizard(self.temp_file.name)
        self.assertEqual(len(wizard.repos), 0)

    def test_corrupted_config_file(self):
        """Test handling of corrupted config file."""
        # Write invalid JSON
        with open(self.temp_file.name, 'w') as f:
            f.write("{ invalid json }")

        wizard = GitHubRepoWizard(self.temp_file.name)
        self.assertEqual(len(wizard.repos), 0)

    @patch('builtins.input')
    def test_prompt_input(self, mock_input):
        """Test user input prompting."""
        # Test with user input
        mock_input.return_value = "user value"
        result = self.wizard.prompt_input("Enter value")
        self.assertEqual(result, "user value")

        # Test with default value
        mock_input.return_value = ""
        result = self.wizard.prompt_input("Enter value", default="default")
        self.assertEqual(result, "default")

    @patch('builtins.input')
    def test_prompt_yes_no(self, mock_input):
        """Test yes/no prompting."""
        test_cases = [
            ("y", True),
            ("yes", True),
            ("Y", True),
            ("YES", True),
            ("n", False),
            ("no", False),
            ("N", False),
            ("NO", False),
            ("", False),  # Default is False
        ]

        for input_val, expected in test_cases:
            mock_input.return_value = input_val
            result = self.wizard.prompt_yes_no("Confirm?", default=False)
            self.assertEqual(result, expected)

        # Test with default True
        mock_input.return_value = ""
        result = self.wizard.prompt_yes_no("Confirm?", default=True)
        self.assertTrue(result)

    @patch('subprocess.run')
    @patch('builtins.input')
    def test_clone_repository(self, mock_input, mock_run):
        """Test repository cloning."""
        repo = GitHubRepo(
            name="test",
            owner="owner",
            url="https://github.com/owner/test",
            local_path="./test_clone"
        )

        # Mock successful clone
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        # Create a temporary directory to simulate the clone
        with tempfile.TemporaryDirectory() as temp_dir:
            repo.local_path = str(Path(temp_dir) / "test_clone")
            self.wizard.clone_repository(repo)

            # Verify git clone was called
            mock_run.assert_called()
            call_args = mock_run.call_args[0][0]
            self.assertEqual(call_args[0], "git")
            self.assertEqual(call_args[1], "clone")
            self.assertIn(repo.clone_url, call_args)


if __name__ == "__main__":
    unittest.main()