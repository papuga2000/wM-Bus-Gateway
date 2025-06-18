#!/usr/bin/env python3

import argparse
import logging
from pathlib import Path

from esphome.git import run_git_command
from semantic_version import Version
import difflib

logger = logging.getLogger(__name__)


TAG_PREFIX = "v"
PARENT_DIR = Path(__file__).parent.parent.resolve()


def git(*args, dry_run=True):
    if dry_run:
        logger.info(f"Would run: git {' '.join(args)}")
        return ""
    return run_git_command(["git", *args], cwd=PARENT_DIR)


def get_latest_tag():
    output = git("describe", "--tags", "--abbrev=0", "--match", "v*", dry_run=False)
    return Version(output.strip().removeprefix(TAG_PREFIX))


def checkout_master(dry_run=True):
    git("checkout", "master", dry_run=dry_run)


def ensure_clean_tree(dry_run=True):
    output = git("status", "--porcelain", dry_run=dry_run)

    if output:
        raise RuntimeError(
            "Git tree is not clean. Please commit or stash your changes before tagging."
        )


def replace_versions_content(old_version: Version, new_version: Version, dry_run=True):
    REPLACEMENTS = {
        PARENT_DIR / "packages" / "version.yaml": "wmbus_gateway_version: {version}",
        PARENT_DIR / "blueprint.yaml": "wmbus_gateway.yaml@{version}",
    }
    for file, replacement in REPLACEMENTS.items():
        content = file.read_text()
        new_content = content.replace(
            replacement.format(version=f"{TAG_PREFIX}{old_version}"),
            replacement.format(version=f"{TAG_PREFIX}{new_version}"),
        )

        if content != new_content:
            diff = difflib.unified_diff(
                content.splitlines(),
                new_content.splitlines(),
                lineterm="",
            )
            logger.info(
                f"Updating {file.relative_to(PARENT_DIR)} from {old_version} to {new_version}"
            )
            for line in diff:
                logger.debug(line)

            if not dry_run:
                file.write_text(new_content)
        else:
            raise RuntimeError(f"No changes made to {file}")


def parse_args():
    class Args(argparse.Namespace):
        bump: str | None
        version: str | None
        dry_run: bool
        verbose: bool

    parser = argparse.ArgumentParser(description="Tag a new version.")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--bump",
        choices=["major", "minor", "patch"],
        help="Type of version bump (major, minor, patch).",
    )
    group.add_argument("--version", help="Specify an explicit version (e.g., 1.2.3).")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done, but don't make any changes.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose (DEBUG) logging.",
    )

    return parser.parse_args(namespace=Args())


if __name__ == "__main__":
    args = parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)

    checkout_master(args.dry_run)
    ensure_clean_tree(args.dry_run)

    last_version = get_latest_tag()

    if args.version:
        new_version = Version(args.version)
    else:
        new_version = getattr(last_version, f"next_{args.bump}")()

    input(
        f"Press Enter to continue with version {new_version} (or Ctrl+C to cancel)..."
    )
    replace_versions_content(last_version, new_version, args.dry_run)

    logger.info("Committing version update...")
    git("commit", "-am", f'"Release {new_version}"', dry_run=args.dry_run)

    for tag in [f"{TAG_PREFIX}{new_version}", "latest"]:
        logger.info(f"Tagging with: {tag}")
        git("tag", "--force", tag, dry_run=args.dry_run)

    logger.info("Pushing changes...")
    git("push", "--tags", dry_run=args.dry_run)
