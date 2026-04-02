#!/usr/bin/env python3

import argparse
from logging import getLogger

from release_utils import (
    COMMON_PARSER,
    PARENT_DIR,
    CommonArgs,
    Tag,
    checkout_master,
    ensure_clean_tree,
    git,
    replace_versions_content,
    setup_logging,
)
from urllib3 import request

logger = getLogger(__name__)


REPO = "IoTLabs-pl/ESPHome-components"
YAML_KEY = "esphome_components_version"


def get_current_version():
    for line in (
        PARENT_DIR.joinpath("packages", "version.yaml").read_text().splitlines()
    ):
        line = line.strip()
        key, _, value = map(str.strip, line.partition(":"))
        if key == YAML_KEY:
            return Tag(value)

    raise RuntimeError(
        f"Could not find '{YAML_KEY}' in version.yaml. "
        "Please ensure the file is formatted correctly."
    )


def latest_version():
    logger.info("Fetching latest version from GitHub...")
    resp = request("GET", f"https://api.github.com/repos/{REPO}/releases/latest")
    if resp.status != 200:
        raise RuntimeError(
            f"Failed to fetch latest version: {resp.status} {getattr(resp, 'reason', '')}"
        )
    latest_version = Tag(resp.json()["tag_name"])
    logger.debug("Got latest version: %s", latest_version)
    return latest_version


def parse_args():
    class Args(CommonArgs):
        version: Tag | None

    parser = argparse.ArgumentParser(
        description="Change external ESPHome components version.",
        parents=[COMMON_PARSER],
    )

    parser.add_argument(
        "--version",
        help="Specify an explicit version (e.g., 1.2.3).",
        type=Tag,
    )

    return parser.parse_args(namespace=Args())


if __name__ == "__main__":
    args = parse_args()

    setup_logging(args)

    checkout_master(args.dry_run)
    ensure_clean_tree(args.dry_run)

    current_version = get_current_version()

    if args.version:
        new_version = args.version
    else:
        new_version = latest_version()

    input(
        f"Press Enter to continue with version {new_version} (or Ctrl+C to cancel)..."
    )

    logger.info("Creating branch for new version...")
    git("checkout", "-b", f"components-{new_version}", dry_run=args.dry_run)

    replace_versions_content(
        current_version,
        new_version,
        {
            PARENT_DIR / "packages" / "version.yaml": f"{YAML_KEY}: {{version}}",
        },
        dry_run=args.dry_run,
    )

    logger.info("Committing changes...")
    git("commit", "-am", f"Bump {REPO} to {new_version}", dry_run=args.dry_run)

    logger.info("Pushing changes...")
    git("push", dry_run=args.dry_run)
