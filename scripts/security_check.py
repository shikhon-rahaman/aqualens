"""Security audit script: Check for secrets in git history and working directory.

Verifies:
- No .env files committed
- No API keys in git history
- No passwords or tokens exposed
- .gitignore properly configured

Usage:
    python scripts/security_check.py
"""

import os
import re
import subprocess
import sys
from pathlib import Path


class SecurityChecker:
    def __init__(self):
        self.issues = []
        self.warnings = []
        self.passed = []

    def error(self, message: str):
        """Record a security issue."""
        self.issues.append(message)
        print(f"[X] ERROR: {message}")

    def warn(self, message: str):
        """Record a warning."""
        self.warnings.append(message)
        print(f"[!] WARNING: {message}")

    def ok(self, message: str):
        """Record a passed check."""
        self.passed.append(message)
        print(f"[+] {message}")

    def check_gitignore(self):
        """Verify .gitignore includes secrets."""
        print("\n" + "=" * 60)
        print("Checking .gitignore")
        print("=" * 60)

        gitignore_path = Path(".gitignore")
        if not gitignore_path.exists():
            self.error(".gitignore file not found!")
            return

        content = gitignore_path.read_text()
        required_patterns = [
            ".env",
            "*.db",
            "uploads/",
            "cache/",
        ]

        for pattern in required_patterns:
            if pattern in content:
                self.ok(f".gitignore includes: {pattern}")
            else:
                self.error(f".gitignore missing pattern: {pattern}")

    def check_env_files(self):
        """Check for .env files in working directory."""
        print("\n" + "=" * 60)
        print("Checking for .env files")
        print("=" * 60)

        env_files = []
        for root, dirs, files in os.walk("."):
            # Skip common excluded directories
            dirs[:] = [
                d
                for d in dirs
                if d not in [".git", "node_modules", ".venv", "__pycache__"]
            ]

            for file in files:
                if file == ".env" or file.endswith(".env"):
                    path = Path(root) / file
                    env_files.append(path)

        if env_files:
            self.warn(f"Found {len(env_files)} .env file(s) in working directory:")
            for path in env_files:
                print(f"  - {path}")
                # Check if it contains actual secrets
                content = path.read_text()
                if self.has_secrets(content):
                    self.error(f"  [X] {path} contains actual secrets!")
                else:
                    self.ok(f"  [+] {path} appears to be example/empty")
        else:
            self.ok("No .env files found in working directory")

    def has_secrets(self, content: str) -> bool:
        """Check if content contains actual secrets."""
        # Check for filled API keys (not empty, not example)
        if re.search(r"GROQ_API_KEY=gsk_[a-zA-Z0-9]{40,}", content):
            return True
        if re.search(r"SUPABASE_KEY=[a-zA-Z0-9]{100,}", content):
            return True
        if re.search(r"postgresql://[^@]+:[^@]+@", content):
            # Has password in connection string
            if "password" not in content.lower():
                return True
        return False

    def check_git_history(self):
        """Check git history for secrets."""
        print("\n" + "=" * 60)
        print("Checking git history")
        print("=" * 60)

        try:
            # Check if git repo exists
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                self.warn("Not a git repository, skipping history check")
                return

            # Check for .env in git history
            result = subprocess.run(
                ["git", "log", "--all", "--oneline", "--", ".env"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.stdout.strip():
                self.error(".env file found in git history!")
                print("  Commits:")
                print("  " + result.stdout[:200])
            else:
                self.ok(".env not found in git history")

            # Check for API key patterns
            patterns = [
                ("gsk_", "Groq API key"),
                ("sk-", "OpenAI-style key"),
                ("eyJ", "JWT token"),
            ]

            for pattern, name in patterns:
                result = subprocess.run(
                    ["git", "log", "--all", "-S", pattern, "--oneline"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.stdout.strip():
                    self.warn(f"Pattern '{pattern}' ({name}) found in git history")
                    print(f"  Commits: {len(result.stdout.splitlines())}")
                else:
                    self.ok(f"No {name} patterns in git history")

        except subprocess.TimeoutExpired:
            self.warn("Git commands timed out")
        except FileNotFoundError:
            self.warn("Git command not found, skipping git checks")
        except Exception as e:
            self.warn(f"Git check failed: {e}")

    def check_tracked_files(self):
        """Check currently tracked files."""
        print("\n" + "=" * 60)
        print("Checking tracked files")
        print("=" * 60)

        try:
            result = subprocess.run(
                ["git", "ls-files"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                self.warn("Could not list tracked files")
                return

            tracked = result.stdout.splitlines()
            suspicious = []

            for file in tracked:
                if any(
                    pattern in file
                    for pattern in [".env", "secret", "password", ".pem", ".key"]
                ):
                    suspicious.append(file)

            if suspicious:
                self.error(f"Found {len(suspicious)} suspicious tracked file(s):")
                for file in suspicious:
                    print(f"  - {file}")
            else:
                self.ok("No suspicious files tracked in git")

        except Exception as e:
            self.warn(f"Could not check tracked files: {e}")

    def check_example_env(self):
        """Verify .env.example exists and is safe."""
        print("\n" + "=" * 60)
        print("Checking .env.example")
        print("=" * 60)

        example_path = Path(".env.example")
        if not example_path.exists():
            self.warn(".env.example not found")
            return

        content = example_path.read_text()

        if self.has_secrets(content):
            self.error(".env.example contains actual secrets!")
        else:
            self.ok(".env.example looks safe (no real secrets)")

        # Check for empty/placeholder values
        required_vars = ["GROQ_API_KEY", "DATABASE_URL", "EXPERT_PIN"]
        for var in required_vars:
            if f"{var}=" in content:
                # Check if it's empty or has example value
                match = re.search(rf"{var}=(.+)", content)
                if match:
                    value = match.group(1).strip()
                    if not value or "change-me" in value.lower() or "example" in value.lower():
                        self.ok(f"{var} is empty/placeholder in .env.example")
                    else:
                        self.warn(f"{var} has a value in .env.example (should be empty)")

    def run(self):
        """Run all security checks."""
        print("\n" + "=" * 60)
        print("AQUALENS SECURITY AUDIT")
        print("=" * 60)

        self.check_gitignore()
        self.check_env_files()
        self.check_example_env()
        self.check_git_history()
        self.check_tracked_files()

        # Summary
        print("\n" + "=" * 60)
        print("SECURITY AUDIT SUMMARY")
        print("=" * 60)
        print(f"Passed:   {len(self.passed)}")
        print(f"Warnings: {len(self.warnings)}")
        print(f"Errors:   {len(self.issues)}")
        print("=" * 60)

        if self.issues:
            print("\n[X] SECURITY AUDIT FAILED")
            print("\nActions required:")
            for issue in self.issues:
                print(f"  - {issue}")
            sys.exit(1)
        elif self.warnings:
            print("\n[!] SECURITY AUDIT PASSED WITH WARNINGS")
            print("\nRecommendations:")
            for warning in self.warnings:
                print(f"  - {warning}")
            sys.exit(0)
        else:
            print("\n[+] SECURITY AUDIT PASSED")
            print("\nNo security issues detected.")
            sys.exit(0)


def main():
    checker = SecurityChecker()
    checker.run()


if __name__ == "__main__":
    main()
