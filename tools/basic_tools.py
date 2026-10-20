"""Jarvis Windows application launcher and basic browser/file tools.

Application discovery is dynamic: Windows packaged-app manifests, Start Menu
shortcuts, App Paths registry entries, PATH commands, installed-program metadata,
registered URI schemes, and explicit executable paths are supported.
"""
import difflib
import json
import os
import re
import shutil
import subprocess
import time
import winreg
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus, urlparse

from config import FILES_DIR

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
CHROME_PROFILES = {
    "work": "Profile 11",
    "main": "Profile 2",
    "automation": "Profile 12",
    "n8n": "Profile 12",  # backwards-compatible alias
}
PROFILE_ALIASES = {
    "n8n": "automation",
    "automation browser": "automation",
    "work browser": "work",
    "main browser": "main",
}
APP_ALIASES = {
    "calc": "calculator", "msstore": "microsoftstore",
    "store": "microsoftstore", "windowsstore": "microsoftstore",
    "microsoft store": "microsoftstore", "fileexplorer": "explorer",
    "windowsfileexplorer": "explorer", "photosapp": "photos",
    "windowsphotos": "photos", "mspaint": "paint", "vscode": "visualstudiocode",
    "vs code": "visualstudiocode", "code": "visualstudiocode",
    "edge": "microsoftedge", "msedge": "microsoftedge",
    "power point": "powerpoint", "ms powerpoint": "powerpoint",
    "ms word": "word", "ms excel": "excel", "cmd": "commandprompt",
    "command prompt": "commandprompt", "windows terminal": "terminal",
    "google chrome": "chrome", "anti gravity": "antigravity",
    "google antigravity": "antigravity",
}
APP_URI_SCHEMES = {
    "photos": "ms-photos:",
    "microsoftstore": "ms-windows-store://home",
    "calculator": "calculator:",
    "camera": "microsoft.windows.camera:",
    "settings": "ms-settings:",
    "microsoftedge": "microsoft-edge:",
    "spotify": "spotify:",
    "telegram": "tg:",
}
WINDOWS_EXE_ALIASES = {
    "notepad": "notepad.exe", "calculator": "calc.exe", "paint": "mspaint.exe",
    "explorer": "explorer.exe", "commandprompt": "cmd.exe",
    "powershell": "powershell.exe", "terminal": "wt.exe",
    "taskmanager": "taskmgr.exe", "snippingtool": "SnippingTool.exe",
}


def _success(message, **extra):
    return {"success": True, "result": message, **extra}


def _failure(message, **extra):
    return {"success": False, "error": message, **extra}


def _normalize(value):
    return re.sub(r"[^a-z0-9]", "", str(value).casefold())


def _canonical_app_name(name):
    aliases = {_normalize(k): _normalize(v) for k, v in APP_ALIASES.items()}
    normalized = _normalize(name)
    return aliases.get(normalized, normalized)


def _canonical_profile(profile):
    normalized = str(profile).strip().casefold()
    return PROFILE_ALIASES.get(normalized, normalized)


def get_time():
    return _success(datetime.now().strftime("%I:%M:%S %p"))


def _validate_profile(profile):
    if not isinstance(profile, str) or not profile.strip():
        return None, _failure("Chrome profile must be text.")
    profile = _canonical_profile(profile)
    if profile not in {"work", "main", "automation"}:
        return None, _failure("Unknown Chrome profile. Use work, main, or automation.")
    if not Path(CHROME_PATH).is_file():
        return None, _failure(f"Chrome was not found at: {CHROME_PATH}")
    return profile, None


def _start_menu_directories():
    result = []
    for root in (os.environ.get("APPDATA"), os.environ.get("PROGRAMDATA")):
        if root:
            path = Path(root) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
            if path.is_dir():
                result.append(path)
    return result


def _find_start_menu_shortcuts(requested):
    target, found = _canonical_app_name(requested), []
    for root in _start_menu_directories():
        try:
            for path in root.rglob("*.lnk"):
                name = _canonical_app_name(path.stem)
                if not name:
                    continue
                if name == target:
                    score = 1.0
                elif target in name or name in target:
                    score = 0.86 + 0.13 * min(len(target), len(name)) / max(len(target), len(name))
                else:
                    score = difflib.SequenceMatcher(None, target, name).ratio()
                if score >= 0.82:
                    found.append((score, path))
        except (OSError, PermissionError):
            continue
    found.sort(key=lambda pair: pair[0], reverse=True)
    unique, seen = [], set()
    for score, path in found:
        if str(path).casefold() not in seen:
            seen.add(str(path).casefold())
            unique.append((score, path))
    return unique


def _powershell_json(script, timeout=60):
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive",
             "-ExecutionPolicy", "Bypass", "-Command", script],
            capture_output=True, text=True, timeout=timeout, check=False,
            encoding="utf-8", errors="replace",
        )
        if result.returncode or not result.stdout.strip():
            return []
        output = result.stdout.strip()
        starts = [i for i in (output.find("["), output.find("{")) if i >= 0]
        if not starts:
            return []
        data = json.loads(output[min(starts):])
        return data if isinstance(data, list) else [data] if isinstance(data, dict) else []
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return []


def _get_registered_apps():
    """Enumerate AppX/MSIX app IDs from each package's XML manifest."""
    script = r"""
$ErrorActionPreference = 'SilentlyContinue'
$rows = @()
foreach ($package in Get-AppxPackage) {
  try {
    $manifest = Get-AppxPackageManifest -Package $package.PackageFullName
    foreach ($app in $manifest.SelectNodes("//*[local-name()='Application']")) {
      $id = [string]$app.GetAttribute('Id')
      if (-not [string]::IsNullOrWhiteSpace($id)) {
        $rows += [PSCustomObject]@{
          Name = [string]$package.Name
          PackageFamilyName = [string]$package.PackageFamilyName
          ApplicationId = $id
          AppID = ([string]$package.PackageFamilyName + '!' + $id)
        }
      }
    }
  } catch { continue }
}
ConvertTo-Json -InputObject @($rows) -Compress -Depth 3
"""
    return [x for x in _powershell_json(script)
            if isinstance(x, dict) and x.get("Name") and x.get("AppID")]


def _get_app_paths():
    found, seen = [], set()
    bases = [
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\App Paths"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\App Paths"),
    ]
    views = [0]
    if hasattr(winreg, "KEY_WOW64_32KEY"):
        views += [winreg.KEY_WOW64_32KEY, winreg.KEY_WOW64_64KEY]
    for hive, base in bases:
        for view in views:
            try:
                with winreg.OpenKey(hive, base, 0, winreg.KEY_READ | view) as root:
                    i = 0
                    while True:
                        try:
                            subname = winreg.EnumKey(root, i)
                            i += 1
                        except OSError:
                            break
                        try:
                            with winreg.OpenKey(root, subname) as key:
                                value, _ = winreg.QueryValueEx(key, None)
                            path = os.path.expandvars(str(value).strip().strip('"'))
                            if os.path.isfile(path) and os.path.normcase(path) not in seen:
                                seen.add(os.path.normcase(path))
                                found.append({"name": Path(subname).stem, "path": path, "target": path})
                        except OSError:
                            continue
            except OSError:
                continue
    return found


def _get_installed_programs():
    script = r"""
$ErrorActionPreference = 'SilentlyContinue'
$roots = @('HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*',
'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*',
'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*')
$rows = @()
foreach ($root in $roots) {
  foreach ($item in Get-ItemProperty $root) {
    if ($item.DisplayName) {
      $rows += [PSCustomObject]@{ Name=[string]$item.DisplayName;
        InstallLocation=[string]$item.InstallLocation; DisplayIcon=[string]$item.DisplayIcon }
    }
  }
}
ConvertTo-Json -InputObject @($rows) -Compress -Depth 3
"""
    return [x for x in _powershell_json(script) if isinstance(x, dict) and x.get("Name")]


def _score_name(requested, candidate):
    target, name = _canonical_app_name(requested), _canonical_app_name(candidate)
    if not target or not name:
        return 0.0
    if target == name:
        return 1.0
    if target in name or name in target:
        return 0.82 + 0.17 * min(len(target), len(name)) / max(len(target), len(name))
    return difflib.SequenceMatcher(None, target, name).ratio()


def _choose_match(requested, candidates, minimum_score=0.82):
    scored = [( _score_name(requested, c.get("name", "")), c)
              for c in candidates]
    scored = sorted((x for x in scored if x[0] >= minimum_score),
                    key=lambda x: x[0], reverse=True)
    if not scored:
        return None, None
    best_score, best = scored[0]
    if best_score == 1.0:
        exact = [x for x in scored if x[0] == 1.0]
        targets = {str(x[1].get("target", "")).casefold() for x in exact}
        return (best, None) if len(targets) == 1 else (None, [x[1]["name"] for x in exact[:8]])
    if len(scored) > 1 and best_score - scored[1][0] < 0.08:
        return None, [x[1]["name"] for x in scored[:8]]
    return best, None


def _launch_shortcut(path):
    try:
        os.startfile(str(path))
        return _success(f"Launch requested for '{path.stem}'.", application=path.stem,
                        launch_method="start_menu_shortcut", verified=False)
    except OSError as exc:
        return _failure(f"Could not launch '{path.stem}': {exc}")


def _launch_registered_app(app):
    app_id = str(app.get("AppID", "")).strip()
    if not app_id:
        return _failure(f"No Windows AppID was found for '{app.get('Name', 'application')}'.")
    try:
        process = subprocess.Popen(["explorer.exe", f"shell:AppsFolder\\{app_id}"], close_fds=True)
        return _success(f"Launch requested for '{app.get('Name', app_id)}'.",
                        application=app.get("Name", app_id), app_id=app_id,
                        launch_method="windows_registered_app", process_id=process.pid,
                        verified=False)
    except OSError as exc:
        return _failure(f"Could not launch '{app.get('Name', app_id)}': {exc}")


def _launch_executable_path(path, requested):
    try:
        executable = Path(os.path.expandvars(str(path))).expanduser()
        if not executable.is_file():
            return _failure(f"Executable file does not exist: {executable}")
        process = subprocess.Popen([str(executable)], cwd=str(executable.parent), close_fds=True)
        return _success(f"Launch requested for '{requested}'.", application=requested,
                        executable=str(executable), launch_method="executable_path",
                        process_id=process.pid, verified=False)
    except (OSError, ValueError) as exc:
        return _failure(f"Could not launch '{requested}': {exc}")


def _registered_uri_scheme(uri):
    scheme = str(uri).split(":", 1)[0].casefold()
    if not re.fullmatch(r"[a-z][a-z0-9+.-]*", scheme):
        return False
    for hive, key_path in [
        (winreg.HKEY_CURRENT_USER, rf"Software\Classes\{scheme}"),
        (winreg.HKEY_LOCAL_MACHINE, rf"Software\Classes\{scheme}"),
        (winreg.HKEY_CLASSES_ROOT, scheme),
    ]:
        try:
            with winreg.OpenKey(hive, key_path) as key:
                try:
                    winreg.QueryValueEx(key, "URL Protocol")
                    return True
                except OSError:
                    try:
                        with winreg.OpenKey(key, r"shell\open\command"):
                            return True
                    except OSError:
                        pass
        except OSError:
            pass
    return False


def _launch_uri(uri, requested):
    try:
        os.startfile(uri)
        return _success(f"Launch requested for '{requested}' using its registered URI handler.",
                        application=requested, uri=uri, launch_method="registered_uri",
                        verified=False)
    except OSError as exc:
        return _failure(f"Could not launch '{requested}' through '{uri}': {exc}")


def _extract_executable(value):
    if not value:
        return None
    value = os.path.expandvars(str(value).strip())
    match = re.match(r'^"([^"]+\.exe)"', value, re.IGNORECASE)
    if not match:
        match = re.match(r"^(.+?\.exe)(?:,.*)?$", value, re.IGNORECASE)
    path = match.group(1).strip() if match else value
    return path if os.path.isfile(path) else None


def _verify_launch(requested, result, timeout=1.0):
    if not result.get("success"):
        return result
    time.sleep(timeout)
    try:
        from tools.windows_automation import list_windows
        info = list_windows()
        windows = info.get("windows", []) if isinstance(info, dict) and info.get("success") else []
        target = _canonical_app_name(requested)
        for window in windows:
            title = str(window.get("title", ""))
            normalized = _canonical_app_name(title)
            if target and (target in normalized or normalized in target):
                result["window_detected"] = title
                result["verified"] = True
                result["result"] = f"Opened '{requested}'. Window detected: '{title}'."
                return result
    except Exception:
        pass
    result["verified"] = False
    result["verification_note"] = (
        "Windows accepted the launch request, but a matching window title was not confirmed. "
        "The app may still be starting or use a different window title."
    )
    return result


def open_application(application):
    """Launch an installed app by spoken/name query using Windows discovery.

    No finite program can guarantee every app on every PC. This tries common
    Windows launch registrations dynamically, not a manually maintained app list.
    """
    if not isinstance(application, str) or not application.strip():
        return _failure("Please provide an application name.")
    requested = application.strip().strip('"')
    target = _canonical_app_name(requested)
    expanded = os.path.expandvars(requested)

    # Explicit executable path.
    if (requested.lower().endswith(".exe") or "\\" in requested or
        ("/" in requested and not requested.startswith(("http://", "https://")))):
        if os.path.isfile(expanded):
            return _verify_launch(requested, _launch_executable_path(expanded, requested))

    if target in {"explorer", "fileexplorer", "windowsfileexplorer"}:
        try:
            proc = subprocess.Popen(["explorer.exe"], close_fds=True)
            return _verify_launch("File Explorer", _success(
                "Launch requested for File Explorer.", application="File Explorer",
                launch_method="explorer", process_id=proc.pid, verified=False))
        except OSError as exc:
            return _failure(f"Could not open File Explorer: {exc}")

    # Registered URI handlers: useful for some built-in and Store apps.
    uri = APP_URI_SCHEMES.get(target)
    if uri and _registered_uri_scheme(uri):
        launched = _launch_uri(uri, requested)
        if launched.get("success"):
            return _verify_launch(requested, launched)

    shortcuts = _find_start_menu_shortcuts(requested)
    exact = [(score, path) for score, path in shortcuts if score == 1.0]
    if len(exact) == 1:
        return _verify_launch(requested, _launch_shortcut(exact[0][1]))
    if len(exact) > 1:
        return _failure(f"Multiple exact Start Menu shortcuts match '{requested}'.",
                        candidates=[str(p) for _, p in exact[:8]])

    # Packaged Windows apps, including many Store apps and Windows components.
    packaged = []
    for app in _get_registered_apps():
        packaged.append({"name": app["Name"], "target": app["AppID"], "app": app})
        if app.get("ApplicationId"):
            packaged.append({"name": app["ApplicationId"], "target": app["AppID"], "app": app})
    chosen, ambiguous = _choose_match(requested, packaged)
    if chosen:
        return _verify_launch(requested, _launch_registered_app(chosen["app"]))
    if ambiguous:
        return _failure(f"Several installed Windows apps match '{requested}'. Specify a more exact name.",
                        candidates=ambiguous)

    shortcut_candidates = [{"name": p.stem, "target": str(p), "path": p}
                           for _, p in shortcuts]
    chosen, ambiguous = _choose_match(requested, shortcut_candidates)
    if chosen:
        return _verify_launch(requested, _launch_shortcut(chosen["path"]))
    if ambiguous:
        return _failure(f"Several Start Menu shortcuts match '{requested}'.", candidates=ambiguous)

    # PATH and App Paths registrations.
    exe_candidates = _get_app_paths()
    alias = WINDOWS_EXE_ALIASES.get(target)
    if alias and shutil.which(alias):
        path = shutil.which(alias)
        exe_candidates.append({"name": requested, "target": path, "path": path})
    raw = requested.strip().strip('"')
    if re.fullmatch(r"[A-Za-z0-9_. -]+", raw):
        command = raw if raw.lower().endswith(".exe") else raw + ".exe"
        path = shutil.which(command)
        if path:
            exe_candidates.append({"name": Path(path).stem, "target": path, "path": path})
    chosen, ambiguous = _choose_match(requested, exe_candidates)
    if chosen:
        return _verify_launch(requested, _launch_executable_path(chosen["path"], requested))
    if ambiguous:
        return _failure(f"Several executable matches were found for '{requested}'.",
                        candidates=ambiguous)

    # Last resort: inspect installed-program registry metadata. Never run
    # UninstallString; only launch a verified executable path from DisplayIcon.
    installed = _get_installed_programs()
    diagnostic = []
    for item in installed:
        path = _extract_executable(item.get("DisplayIcon", ""))
        diagnostic.append({"name": item.get("Name", ""), "target": path or "" , "path": path})
    chosen, ambiguous = _choose_match(requested, diagnostic, 0.88)
    if chosen and chosen.get("path"):
        return _verify_launch(requested, _launch_executable_path(chosen["path"], requested))
    if ambiguous:
        return _failure(f"Several installed programs match '{requested}'.", candidates=ambiguous)

    return _failure(
        f"Could not find a usable Windows launch target for '{requested}'. "
        "The app may not be installed for this Windows account or may not expose a "
        "shortcut, AppID, registered URI, PATH command, App Paths entry, or discoverable executable.",
        searched_sources=["explicit executable path", "registered URI handlers",
                          "Start Menu shortcuts", "packaged app manifests",
                          "Windows App Paths registry", "PATH executables",
                          "installed-program registry metadata"],
    )


def open_chrome(profile="work"):
    profile, error = _validate_profile(profile)
    if error:
        return error
    chrome_profile = CHROME_PROFILES[profile]
    try:
        process = subprocess.Popen([CHROME_PATH, f"--profile-directory={chrome_profile}"],
                                   close_fds=True)
        return _success(f"Requested Chrome profile '{profile}' to open.",
                        profile=profile, chrome_profile=chrome_profile,
                        process_id=process.pid, verified=False)
    except OSError as exc:
        return _failure(f"Could not open Chrome: {exc}")


def open_website(url, profile="work"):
    if not isinstance(url, str):
        return _failure("Website URL must be text.")
    url = url.strip()
    parsed = urlparse(url)
    if (parsed.scheme.lower() not in ("http", "https") or not parsed.netloc or
        any(char in url for char in "\r\n")):
        return _failure("Provide a valid http:// or https:// website URL.")
    profile, error = _validate_profile(profile)
    if error:
        return error
    chrome_profile = CHROME_PROFILES[profile]
    try:
        process = subprocess.Popen([CHROME_PATH, f"--profile-directory={chrome_profile}",
                                    "--new-tab", url], close_fds=True)
        return _success(f"Requested a new tab for {url} in Chrome profile '{profile}'.",
                        profile=profile, chrome_profile=chrome_profile, url=url,
                        new_tab=True, process_id=process.pid, verified=False)
    except OSError as exc:
        return _failure(f"Could not open website: {exc}")


def search_web(query, profile="work"):
    if not isinstance(query, str) or not query.strip():
        return _failure("Enter a search query.")
    return open_website("https://www.google.com/search?q=" + quote_plus(query.strip()), profile)


def search_youtube(query, profile="work"):
    if not isinstance(query, str) or not query.strip():
        return _failure("Enter a YouTube search query.")
    return open_website("https://www.youtube.com/results?search_query=" + quote_plus(query.strip()), profile)


def save_text_file(filename, content):
    if not isinstance(filename, str) or not filename.strip():
        return _failure("A filename is required.")
    if not isinstance(content, str):
        return _failure("File content must be text.")
    safe_name = Path(filename.strip()).name
    if safe_name in ("", ".", ".."):
        return _failure("Invalid filename.")
    if not safe_name.lower().endswith(".txt"):
        safe_name += ".txt"
    FILES_DIR.mkdir(parents=True, exist_ok=True)
    stem, suffix = Path(safe_name).stem, Path(safe_name).suffix
    for number in range(1000):
        name = safe_name if number == 0 else f"{stem}_{number}{suffix}"
        candidate = FILES_DIR / name
        try:
            with candidate.open("x", encoding="utf-8", newline="") as file:
                file.write(content)
            if candidate.read_text(encoding="utf-8") != content:
                return _failure(f"File was created but verification failed: {candidate}")
            return _success(f"Saved and verified file: {candidate}", path=str(candidate),
                            verified=True, characters=len(content))
        except FileExistsError:
            continue
        except Exception as exc:
            return _failure(f"Could not save the file: {exc}")
    return _failure("Could not find an unused filename after 1000 attempts.")
