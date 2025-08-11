#!/usr/bin/env python

import os
import sys
from pathlib import Path

try:
    import git
except ImportError:
    git = None

from dotenv import load_dotenv

from aider.args import get_parser


def get_git_root():
    """Try and guess the git repo, since the conf.yml can be at the repo root"""
    try:
        repo = git.Repo(search_parent_directories=True)
        return repo.working_tree_dir
    except (git.InvalidGitRepositoryError, FileNotFoundError, TypeError):
        return None


def generate_search_path_list(default_file, git_root, command_line_file):
    files = []
    files.append(Path.home() / default_file)  # homedir
    if git_root:
        files.append(Path(git_root) / default_file)  # git root
    files.append(default_file)
    if command_line_file:
        files.append(command_line_file)

    resolved_files = []
    for fn in files:
        try:
            resolved_files.append(Path(fn).resolve())
        except OSError:
            pass

    files = resolved_files
    files.reverse()
    uniq = []
    for fn in files:
        if fn not in uniq:
            uniq.append(fn)
    uniq.reverse()
    files = uniq
    files = list(map(str, files))
    files = list(dict.fromkeys(files))

    return files


def load_dotenv_files(git_root, dotenv_fname, encoding="utf-8"):
    # Standard .env file search path
    dotenv_files = generate_search_path_list(
        ".env",
        git_root,
        dotenv_fname,
    )

    # Explicitly add the OAuth keys file to the beginning of the list
    oauth_keys_file = Path.home() / ".aider" / "oauth-keys.env"
    if oauth_keys_file.exists():
        # Insert at the beginning so it's loaded first (and potentially overridden)
        dotenv_files.insert(0, str(oauth_keys_file.resolve()))
        # Remove duplicates if it somehow got included by generate_search_path_list
        dotenv_files = list(dict.fromkeys(dotenv_files))

    loaded = []
    for fname in dotenv_files:
        try:
            if Path(fname).exists():
                load_dotenv(fname, override=True, encoding=encoding)
                loaded.append(fname)
        except OSError as e:
            print(f"OSError loading {fname}: {e}")
        except Exception as e:
            print(f"Error loading {fname}: {e}")
    return loaded


def check_config_files_for_yes(config_files):
    found = False
    for config_file in config_files:
        if Path(config_file).exists():
            try:
                with open(config_file, "r") as f:
                    for line in f:
                        if line.strip().startswith("yes:"):
                            print("Configuration error detected.")
                            print(f"The file {config_file} contains a line starting with 'yes:'")
                            print("Please replace 'yes:' with 'yes-always:' in this file.")
                            found = True
            except Exception:
                pass
    return found


class Config:
    def __init__(self, argv=None, git_root=None, **kwargs):
        if argv is None:
            argv = sys.argv[1:]

        self.git_root = git_root

        conf_fname = Path(".aider.conf.yml")

        default_config_files = []
        try:
            default_config_files += [conf_fname.resolve()]  # CWD
        except OSError:
            pass

        if self.git_root:
            git_conf = Path(self.git_root) / conf_fname  # git root
            if git_conf not in default_config_files:
                default_config_files.append(git_conf)
        default_config_files.append(Path.home() / conf_fname)  # homedir
        self.default_config_files = list(map(str, default_config_files))

        parser_config_files = list(self.default_config_files)
        parser_config_files.reverse()

        self.parser = get_parser(parser_config_files, self.git_root)
        try:
            args, _ = self.parser.parse_known_args(argv)
        except AttributeError as e:
            if all(
                word in str(e)
                for word in ["bool", "object", "has", "no", "attribute", "strip"]
            ):
                if check_config_files_for_yes(self.default_config_files):
                    sys.exit(1)
            raise e

        self.loaded_dotenvs = load_dotenv_files(self.git_root, args.env_file, args.encoding)

        # Parse again to include any arguments that might have been defined in .env
        self.args = self.parser.parse_args(argv)

        for key, value in kwargs.items():
            if hasattr(self.args, key):
                setattr(self.args, key, value)
