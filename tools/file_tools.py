
"""Safe file and folder operations for Jarvis on Windows."""

import os
import shutil
import subprocess
from pathlib import Path
from config import WORKSPACE_ROOT

def _failure(message):
    return {"success": False, "error": message}


def _success(message, **extra):
    return {"success": True, "result": message, **extra}


def _get_path(path):
    """Validate a path and expand ~ and environment variables."""
    if not isinstance(path, str) or not path.strip():
        raise ValueError("A non-empty path is required.")

    expanded = os.path.expandvars(os.path.expanduser(path.strip()))
    return Path(expanded).resolve()


def create_folder(path):
    """Create a folder; report an error if it already exists."""
    try:
        target = _get_path(path)

        if target.exists():
            return _failure(f"Path already exists: {target}")

        target.mkdir(parents=True, exist_ok=False)

        if not target.is_dir():
            return _failure("Folder creation could not be verified.")

        return _success(f"Created folder: {target}", path=str(target))

    except Exception as error:
        return _failure(f"Could not create folder: {error}")


def list_directory(path=None):
    """List items in a directory. Defaults to the user's Desktop."""
    try:
        target = _get_path(path) if path else WORKSPACE_ROOT

        if not target.is_dir():
            return _failure(f"Directory not found: {target}")

        items = []
        for item in sorted(target.iterdir(), key=lambda p: p.name.lower()):
            try:
                items.append({
                    "name": item.name,
                    "type": "folder" if item.is_dir() else "file",
                    "path": str(item),
                })
            except OSError:
                continue

        return _success(
            f"Found {len(items)} items in {target}",
            path=str(target),
            count=len(items),
            items=items,
        )

    except Exception as error:
        return _failure(f"Could not list directory: {error}")


def create_text_file(path, content):
    """Create a UTF-8 text file without overwriting an existing file."""
    try:
        if not isinstance(content, str):
            return _failure("File content must be text.")

        target = _get_path(path)

        if target.exists():
            return _failure(f"File already exists; nothing overwritten: {target}")

        if not target.parent.is_dir():
            return _failure(f"Parent folder does not exist: {target.parent}")

        with target.open("x", encoding="utf-8", newline="") as file:
            file.write(content)

        if target.read_text(encoding="utf-8") != content:
            return _failure(f"File created, but verification failed: {target}")

        return _success(
            f"Created and verified text file: {target}",
            path=str(target),
            characters=len(content),
            verified=True,
        )

    except Exception as error:
        return _failure(f"Could not create text file: {error}")


def read_text_file(path, max_chars=12000):
    """Read a text file, limiting output size."""
    try:
        target = _get_path(path)

        if not target.is_file():
            return _failure(f"File not found: {target}")

        if target.stat().st_size > 2_000_000:
            return _failure("File is larger than the 2 MB safety limit.")

        max_chars = max(1, min(int(max_chars), 20000))
        content = target.read_text(encoding="utf-8")

        return _success(
            content[:max_chars],
            path=str(target),
            characters=len(content),
            truncated=len(content) > max_chars,
        )

    except UnicodeDecodeError:
        return _failure("This file is not valid UTF-8 text.")
    except Exception as error:
        return _failure(f"Could not read file: {error}")


def rename_path(source, new_name):
    """Rename an item within its current parent directory."""
    try:
        original = _get_path(source)

        if not original.exists():
            return _failure(f"Source not found: {original}")

        if not isinstance(new_name, str) or not new_name.strip():
            return _failure("Provide a new name.")

        name = new_name.strip()

        if name in {".", ".."} or Path(name).name != name:
            return _failure("New name must be a name, not a path.")

        destination = original.with_name(name)

        if destination.exists():
            return _failure(f"Destination already exists: {destination}")

        original.rename(destination)

        if not destination.exists():
            return _failure("Rename could not be verified.")

        return _success(
            f"Renamed to: {destination}",
            old_path=str(original),
            new_path=str(destination),
        )

    except Exception as error:
        return _failure(f"Could not rename item: {error}")


def _transfer_path(source, destination, move=False):
    """Copy or move an item without overwriting existing destinations."""
    try:
        src = _get_path(source)
        dst = _get_path(destination)

        if not src.exists():
            return _failure(f"Source not found: {src}")

        if not dst.parent.is_dir():
            return _failure(f"Destination parent folder not found: {dst.parent}")

        if dst.exists():
            return _failure(f"Destination already exists: {dst}")

        if src.is_dir():
            if dst == src or src in dst.parents:
                return _failure("Cannot copy or move a folder into itself.")

        if move:
            shutil.move(str(src), str(dst))
        elif src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)

        if not dst.exists():
            return _failure("Operation could not be verified.")

        action = "Moved" if move else "Copied"
        return _success(
            f"{action}: {src} -> {dst}",
            source=str(src),
            destination=str(dst),
        )

    except Exception as error:
        return _failure(f"File operation failed: {error}")


def copy_path(source, destination):
    """Copy a file or folder without overwriting."""
    return _transfer_path(source, destination, move=False)


def move_path(source, destination):
    """Move a file or folder without overwriting."""
    return _transfer_path(source, destination, move=True)


def open_folder(path):
    """Open an existing folder in Windows File Explorer."""
    try:
        target = _get_path(path)

        if not target.is_dir():
            return _failure(f"Folder not found: {target}")

        subprocess.Popen(["explorer.exe", str(target)])
        return _success(f"Opened folder: {target}", path=str(target))

    except Exception as error:
        return _failure(f"Could not open folder: {error}")
