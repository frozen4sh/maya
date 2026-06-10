# Copyright Epic Games, Inc. All Rights Reserved.
import os
import re
import json
import time
import logging
import platform
import importlib
import subprocess
import webbrowser
import http.client
from pathlib import Path
from datetime import datetime, timedelta
from urllib.parse import urlparse

import maya.OpenMayaUI as omui
import maya.api.OpenMaya as om
from maya import cmds

try:
    import shiboken6 as shiboken
    from PySide6 import QtGui, QtCore, QtWidgets
except ImportError:
    try:
        import shiboken2 as shiboken
        from PySide2 import QtGui, QtCore, QtWidgets
    except ImportError:
        raise ImportError("No compatible Qt bindings found (PySide6 or PySide2)")

DOCUMENTATION_URL = "https://dev.epicgames.com/documentation/en-us/metahuman/metahuman-for-maya"
EULA_URL = "https://www.fab.com/eula"
DOWNLOAD_URL = "https://www.fab.com/listings/9e3bf55e-d4c3-44fc-a3d4-ec4cb772ec29"
LATEST_VERSION_URL = "https://metahuman-versioning.ucs.on.epicgames.com/api/v1/mayaversions"

LIBS = {
    "PyDNA": "dna",
    "PyDNACalib2": "dnacalib2",
    "PyRDF": "rdf",
}

PLUGINS = {
    "cbsnode_maya": "cbsNode",
    "DNACalibMayaPlugin": "DNACalibMayaPlugin",
    "riglogic4_maya": "embeddedRL4",
    "MayaUERBFPlugin": "MayaUERBFPlugin",
    "PreviewRigLogic": "PreviewRigLogic",
    "SwingTwistEvaluatorPlugin": "SwingTwistEvaluatorPlugin",
}

CHECK_INTERVAL_DAYS = 1
WINDOW_TITLE = "MetaHuman for Maya"


def maya_useNewAPI():
    """
    The presence of this function tells Maya that the plugin produces, and
    expects to be passed, objects created using the Maya Python API 2.0.
    """
    pass


def is_batch_mode():
    if not hasattr(cmds, "about"):
        return False
    else:
        return cmds.about(batch=True)


def current_dir():
    return Path(os.path.dirname(current_dir.__code__.co_filename))


def get_version():
    version_file = os.path.abspath(os.path.join(current_dir(), "version.txt"))
    with open(version_file, encoding="utf-8") as f:
        version = f.read().replace("\n", "").replace("\r", "").replace("\t", "").strip()
    return version


MENU_NAME = "MetaHuman"
VERSION = get_version()

QSETTINGS = QtCore.QSettings(
    QtCore.QSettings.Format.IniFormat,
    QtCore.QSettings.Scope.UserScope,
    "Epic Games",
    "MetaHumanForMaya/MetaHumanForMaya",
)
SETTINGS_PATH = Path(QSETTINGS.fileName()).parent.as_posix()


# --------------------------------------------------------------------------------------------------


logger = logging.getLogger("MetaHumanForMaya")
log_level_name = os.getenv("MH4M_LOGLEVEL", "INFO").upper()
log_level = getattr(logging, log_level_name, logging.INFO)
logger.setLevel(log_level)


# --------------------------------------------------------------------------------------------------


def get_maya_main_window():
    """Get the main Maya window as a QtWidgets.QMainWindow instance."""
    ptr = omui.MQtUtil.mainWindow()
    if ptr is not None:
        return shiboken.wrapInstance(int(ptr), QtWidgets.QMainWindow)


# --------------------------------------------------------------------------------------------------


def load_plugin_info():
    json_path = current_dir() / "plugin_info.json"
    with json_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_package_version(package_name):
    data = load_plugin_info()
    for entry in data.get("Packages", []):
        if entry.startswith(f"{package_name}-"):
            return entry.split("-", maxsplit=1)[1]
    return None


def _apply_used_resolve(packages):
    rez_env = os.getenv("REZ_USED_RESOLVE")
    if not rez_env:
        return packages
    used_resolve = {}
    for entry in rez_env.split(" "):
        if "-" not in entry or not entry:
            continue
        name = entry.split("-", 1)[0]
        used_resolve[name] = entry
    merged = []
    for pkg in packages:
        if "-" not in pkg:
            merged.append(pkg)
            continue
        name = pkg.split("-", 1)[0]
        merged.append(used_resolve.get(name, pkg))
    return merged


def _deduplicate_packages(packages):
    seen = set()
    unique = []
    for pkg in packages:
        if pkg not in seen:
            unique.append(pkg)
            seen.add(pkg)
    return unique


def _filter_packages(packages):
    filtered_prefixes = ("maya", "python", "platform", "os", "arch")
    result = []
    for pkg in packages:
        name = pkg.split("-", 1)[0]
        if name in filtered_prefixes:
            continue
        result.append(pkg)
    return result


def format_info_text(info):
    lines = [
        f"Name:     {info.get('Name')}",
        f"Version:  {get_version()}",
        f"System:   {platform.system()}",
        f"Host:     {cmds.about(installedVersion=True)}",
        f"Settings: {SETTINGS_PATH}",
    ]

    packages = info.get("Packages", [])
    packages = _apply_used_resolve(packages)
    packages = _deduplicate_packages(packages)
    packages = _filter_packages(packages)

    lines.append("Packages:")
    for package in packages:
        lines.append(f"  • {package}")

    return "\n".join(lines)


class AboutDialog(QtWidgets.QDialog):
    def __init__(self, plugin_info, parent=None):
        super().__init__(parent)
        self.setWindowTitle(WINDOW_TITLE)
        self.setMinimumSize(400, 400)

        self.info_text = format_info_text(plugin_info)

        main_layout = QtWidgets.QVBoxLayout(self)

        self.text_edit = QtWidgets.QPlainTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setPlainText(self.info_text)
        self.text_edit.setStyleSheet(
            """
            QPlainTextEdit {
                font-family: Consolas, monospace;
                font-size: 10pt;
            }
        """
        )

        button_row = QtWidgets.QHBoxLayout()
        button_row.setContentsMargins(0, 0, 0, 0)

        copy_button = QtWidgets.QPushButton("Copy to Clipboard")
        copy_button.clicked.connect(self.copy_to_clipboard)

        ok_button = QtWidgets.QPushButton("OK")
        ok_button.clicked.connect(self.accept)

        button_row.addWidget(copy_button, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        button_row.addStretch(1)
        button_row.addWidget(ok_button, 0, QtCore.Qt.AlignmentFlag.AlignRight)

        main_layout.addWidget(self.text_edit)
        main_layout.addLayout(button_row)

        self.resize(400, 600)

    def copy_to_clipboard(self):
        QtGui.QGuiApplication.clipboard().setText(self.info_text)


# --------------------------------------------------------------------------------------------------


def _safe_ssl_context():
    try:
        import ssl  # imported here on purpose
    except Exception as e:
        logger.error("ssl module import failed: %s", e)
        return None

    def _pick_ca_locations():
        # env overrides
        env_file = os.environ.get("SSL_CERT_FILE")
        if env_file and os.path.isfile(env_file):
            return env_file, None
        env_dir = os.environ.get("SSL_CERT_DIR")
        if env_dir and os.path.isdir(env_dir):
            return None, env_dir

        # defaults from this openssl build
        try:
            dvp = ssl.get_default_verify_paths()
            if getattr(dvp, "cafile", None) and os.path.isfile(dvp.cafile):
                return dvp.cafile, None
            if getattr(dvp, "capath", None) and os.path.isdir(dvp.capath):
                return None, dvp.capath
        except Exception:
            pass

        # common unix locations
        if os.name == "posix":
            common = [
                "/etc/ssl/certs/ca-certificates.crt",  # debian, ubuntu
                "/etc/pki/tls/certs/ca-bundle.crt",  # rhel, centos, fedora
                "/etc/ssl/ca-bundle.pem",  # suse
                "/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem",
                "/etc/ssl/cert.pem",  # macos
                "/usr/local/etc/openssl@1.1/cert.pem",  # homebrew old
                "/usr/local/etc/openssl/cert.pem",  # homebrew current
            ]
            for p in common:
                if os.path.isfile(p):
                    return p, None

        return None, None

    try:
        ctx = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED
        if hasattr(ssl, "TLSVersion"):
            ctx.minimum_version = ssl.TLSVersion.TLSv1_2

        cafile, capath = _pick_ca_locations()
        if cafile or capath:
            ctx.load_verify_locations(cafile=cafile, capath=capath)
        else:
            logger.debug("No system CA bundle: relying on OpenSSL defaults")

        return ctx
    except Exception as e:
        logger.error("failed building SSL context: %s", e)
        return None


def https_get(url, timeout=10):
    try:
        parsed = urlparse(url)
        if parsed.scheme != "https":
            logger.error(f"Only HTTPS URLs are supported, got: {parsed.scheme}")
            return None, None

        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"

        ctx = _safe_ssl_context()
        if ctx is None:
            logger.error("cannot create SSL context, HTTPS is unavailable in this runtime")
            return None, None

        conn = http.client.HTTPSConnection(parsed.hostname, parsed.port or 443, timeout=timeout, context=ctx)

        try:
            conn.request("GET", path, headers={"User-Agent": "MetaHumanForMaya"})
            resp = conn.getresponse()
            body = resp.read()
            body_str = body.decode("utf-8", errors="replace")
            try:
                return resp.status, json.loads(body_str)
            except json.JSONDecodeError:
                return resp.status, body_str
        finally:
            conn.close()

    except (http.client.HTTPException, OSError, TimeoutError) as e:
        logger.error(f"Network error fetching {url}: {e}")
        return None, None
    except Exception as e:
        logger.error(f"Unexpected error fetching {url}: {e}")
        return None, None


# --------------------------------------------------------------------------------------------------


def get_latest_version():
    try:
        status, content = https_get(LATEST_VERSION_URL, timeout=15)

        # Check if request failed
        if status is None or content is None:
            logger.error("Failed to fetch latest version (network error)")
            return None

        if status != 200:
            logger.error(f"Error checking for updates, request returned: {status}")
            return None

        # Ensure content is a dict
        if not isinstance(content, dict):
            logger.error(f"Unexpected response type: {type(content)}")
            return None

        # Get platform-specific data
        system = platform.system()
        data = content.get(system, {})

        if not data:
            logger.warning(f"No version data available for platform: {system}")
            return None

        version = data.get("version")
        if not version:
            logger.warning(f"Version field missing in response for platform: {system}")
            return None

        return version

    except Exception as e:
        logger.error(f"Unexpected error getting latest version: {e}")
        return None


def is_update_available():
    try:
        if is_batch_mode():
            return (False, VERSION)

        latest = get_latest_version()
        if latest is None:
            return (None, None)

        logger.debug(f"Latest version: {latest}, current version: {VERSION}")
        try:
            current_is_smaller = compare_semver_versions(VERSION, latest) == -1
        except (ValueError, AttributeError) as e:
            logger.error(f"Error comparing versions '{VERSION}' vs '{latest}': {e}")
            return (None, None)

        if current_is_smaller:
            return (True, latest)

        return (False, VERSION)

    except Exception as e:
        logger.error(f"Unexpected error checking for updates: {e}")
        return (None, None)


class UpdatePrompt(QtWidgets.QDialog):
    def __init__(self, message, update_available=False, parent=None):
        super().__init__(parent)
        self.setWindowTitle(WINDOW_TITLE)
        self.setMinimumWidth(400)

        layout = QtWidgets.QVBoxLayout(self)

        label = QtWidgets.QLabel(message, self)
        label.setWordWrap(True)

        button_box = QtWidgets.QDialogButtonBox(self)

        if update_available:
            label.setText(label.text() + "\n" + "Would you like to go to download page?")
            button_box.setStandardButtons(QtWidgets.QDialogButtonBox.Yes | QtWidgets.QDialogButtonBox.No)
        else:
            button_box.setStandardButtons(QtWidgets.QDialogButtonBox.Ok)

        layout.addWidget(label)
        layout.addWidget(button_box)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)


# --------------------------------------------------------------------------------------------------


class WarningDialog(QtWidgets.QDialog):
    def __init__(self, message, parent=None):
        super().__init__(parent)
        self.setWindowTitle(WINDOW_TITLE + " | Warning")
        self.setMinimumWidth(400)
        self.message = message

        main_layout = QtWidgets.QVBoxLayout(self)
        content_layout = QtWidgets.QVBoxLayout()
        content_layout.setSpacing(10)

        icon = self.style().standardIcon(QtWidgets.QStyle.SP_MessageBoxWarning)
        icon_label = QtWidgets.QLabel(self)
        icon_label.setPixmap(icon.pixmap(32, 32))
        icon_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)

        self.text_edit = QtWidgets.QPlainTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.text_edit.setPlainText(message)
        self.text_edit.setStyleSheet(
            """
            QPlainTextEdit {
                font-family: Consolas, monospace;
                font-size: 10pt;
            }
        """
        )

        content_layout.addWidget(icon_label)
        content_layout.addWidget(self.text_edit)

        button_row = QtWidgets.QHBoxLayout()

        copy_btn = QtWidgets.QPushButton("Copy to Clipboard")
        copy_btn.clicked.connect(self.copy_to_clipboard)

        ignore_btn = QtWidgets.QPushButton("Ignore and continue")
        ignore_btn.clicked.connect(self.accept)

        cancel_btn = QtWidgets.QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        button_row.addWidget(copy_btn, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        button_row.addStretch(1)
        button_row.addWidget(ignore_btn, 0, QtCore.Qt.AlignmentFlag.AlignRight)
        button_row.addWidget(cancel_btn, 0, QtCore.Qt.AlignmentFlag.AlignRight)

        main_layout.addLayout(content_layout)
        main_layout.addLayout(button_row)

    def copy_to_clipboard(self):
        QtGui.QGuiApplication.clipboard().setText(self.message)


# --------------------------------------------------------------------------------------------------


def should_check_for_updates():
    if is_batch_mode():
        return False

    disable_updates = QSETTINGS.value("disable_updates", type=int)
    if disable_updates == 1:
        return False

    timestamp = QSETTINGS.value("last_update_check", type=int)
    if timestamp:
        last_check = datetime.fromtimestamp(timestamp)
        if datetime.now() - last_check < timedelta(days=CHECK_INTERVAL_DAYS):
            return False

    return True


def parse_semver_version(version_string):
    match = re.search(r"(?:v)?(\d+)(?:\.(\d+))?(?:\.(\d+))?$", version_string)
    if not match:
        raise ValueError(f"Could not extract version from string: '{version_string}'")
    major = match.group(1)
    minor = match.group(2)
    patch = match.group(3)
    return f"{major}.{minor}.{patch}"


def compare_semver_versions(v1, v2):
    def normalize(v):
        parts = parse_semver_version(v).split(".")
        return [int(p) if p is not None and p != "None" else 0 for p in parts]

    v1_parts = normalize(v1)
    v2_parts = normalize(v2)

    for a, b in zip(v1_parts, v2_parts):
        if a < b:
            return -1  # v1 < v2
        elif a > b:
            return 1  # v1 > v2
    return 0  # equal


def check_lib_version(name, expected_version):
    try:
        lib = importlib.import_module(name)
    except ImportError:
        logger.error(f"Library '{name}' could not be imported.")
        return False, "N/A"

    actual_version = "0.0.0"

    if hasattr(lib, "VersionInfo_getVersionString"):
        actual_version = lib.VersionInfo_getVersionString()
    elif hasattr(lib, "__version__"):
        actual_version = lib.__version__
    else:
        raise AttributeError(
            f"Cannot determine the major version of library '{name}'. "
            "Expected a 'VersionInfo_getVersionString' method or '__version__' attribute."
        )

    actual_version = parse_semver_version(actual_version)

    return (actual_version == expected_version), actual_version


def user_warning(message):
    logger.warning(message)
    if is_batch_mode():
        return

    QtWidgets.QApplication.restoreOverrideCursor()
    dialog = WarningDialog(message, get_maya_main_window())
    dialog.resize(920, 360)
    result = dialog.exec()

    return result == QtWidgets.QDialog.Rejected


def get_user_plugin_path():
    version = cmds.about(version=True)
    doc_root = os.path.join(os.environ["USERPROFILE"], "Documents", "maya")
    return os.path.join(doc_root, version, "plug-ins").replace("\\", "/")


def get_maya_plugin_search_paths():
    paths = set()
    for path in os.environ.get("MAYA_PLUG_IN_PATH", "").split(os.pathsep):
        if path:
            paths.add(os.path.normpath(path).replace("\\", "/"))
    paths.add(get_user_plugin_path())
    return list(paths)


def dependency_checks():
    issues = []

    # libs
    for package, lib in LIBS.items():
        expected = get_package_version(package)
        check, actual = check_lib_version(lib, expected)
        if not check:
            issues.append(
                {
                    "kind": "lib",
                    "name": lib,
                    "expected": expected,
                    "actual": actual,
                    "detail": (
                        "A plugin that uses an incompatible version of the specified "
                        "library is already loaded. If you've used a related external tool, "
                        "the issue may be caused by a plugin associated with it."
                    ),
                }
            )

    # plugins
    for package, plugin in PLUGINS.items():
        expected = get_package_version(package)

        if not cmds.pluginInfo(plugin, query=True, loaded=True):
            cmds.loadPlugin(plugin, quiet=True)

        actual = cmds.pluginInfo(plugin, query=True, version=True)
        if actual != expected:
            filepath = cmds.pluginInfo(plugin, query=True, path=True)
            issues.append(
                {
                    "kind": "plugin",
                    "name": plugin,
                    "expected": expected,
                    "actual": actual,
                    "detail": (
                        "Specified plugin is already loaded and incompatible with the "
                        "current application. Remove the plugin and try again."
                    ),
                    "path": filepath,
                }
            )

    # nothing to report
    if not issues:
        return

    # format a single combined warning dialog
    lines = []
    lines.append("Dependency mismatch summary\n")
    for i, item in enumerate(issues, 1):
        lines.append(f"{i}. {item['kind']}:   {item['name']}")
        lines.append(f"   expected: {item['expected']}")
        lines.append(f"   found:    {item['actual']}")
        if "path" in item and item["path"]:
            lines.append(f"   path:     {item['path']}")
        lines.append(f"   note:     {item['detail']}\n")

    message = "\n".join(lines)
    rejected = user_warning(message)

    if rejected:
        logger.error("dependency checks failed")
        raise Exception("Incompatible or incomplete environment, please refer to full error log for more info.")

    logger.warning("dependency mismatches present; continuing on user request")


def perform_check_for_updates(shy_dialog=False):
    update_available, ver = is_update_available()
    QSETTINGS.setValue("last_update_check", int(time.time()))

    message = ""
    if update_available is None:
        message = (
            "Error: Could not fetch version data from server. Please check if theres an update using Epic Launcher."
        )

    elif isinstance(update_available, bool):
        if update_available:
            message = f"A new version of {WINDOW_TITLE} is available: v{ver}"
        else:
            message = f"You have the latest version of {WINDOW_TITLE}: v{ver}"

    logger.info(message)
    if is_batch_mode():
        return message

    if shy_dialog and not update_available:
        return message

    dialog = UpdatePrompt(message, update_available, get_maya_main_window())
    result = dialog.exec()
    if update_available and result == QtWidgets.QDialog.Accepted:
        webbrowser.open(DOWNLOAD_URL)

    return message


def updates_check():
    try:
        logger.info("Checking for updates...")
        if should_check_for_updates():
            perform_check_for_updates(shy_dialog=True)
        else:
            logger.info("Check skipped.")
    except Exception as e:
        logger.error(f"Error during updates check: {e}")


# --------------------------------------------------------------------------------------------------


def command_open_EULA(*args):
    webbrowser.open(EULA_URL)


def command_open_licenses_folder(*args):
    licenses_dir = current_dir().parent / "licenses"
    system = platform.system()
    if system == "Windows":
        os.startfile(licenses_dir)
    elif system == "Darwin":  # macOS
        subprocess.run(["open", str(licenses_dir)])
    else:  # Linux and other UNIX-like
        subprocess.run(["xdg-open", str(licenses_dir)])


def command_check_for_updates(*args):
    perform_check_for_updates(shy_dialog=False)


def command_open_documentation(*args):
    webbrowser.open(DOCUMENTATION_URL)


def command_show_about(*args):
    plugin_info = load_plugin_info()
    logger.info(plugin_info)
    if is_batch_mode():
        return
    dialog = AboutDialog(plugin_info, get_maya_main_window())
    dialog.exec()


# --------------------------------------------------------------------------------------------------


def install_menu():
    # check if the menu already exists; if so, delete it
    uninstall_menu()

    # create a new menu in the Maya main menu bar
    menu = cmds.menu(MENU_NAME, label=MENU_NAME, to=True, parent="MayaWindow")

    cmds.menuItem(
        parent=menu,
        label="Character Assembler",
        command="import mh_character_assembler;mh_character_assembler.show()",
    )
    cmds.menuItem(
        parent=menu,
        label="Expression Editor",
        command="import mh_expression_editor;mh_expression_editor.show()",
    )
    cmds.menuItem(
        parent=menu,
        label="Pose Editor",
        command="import mh_pose_editor;mh_pose_editor.show()",
    )
    cmds.menuItem(
        parent=menu,
        label="Groom Exporter",
        command="import mh_groom_exporter;mh_groom_exporter.show()",
    )
    cmds.menuItem(
        parent=menu,
        divider=True,
    )
    cmds.menuItem(
        parent=menu,
        label="View EULA",
        command=command_open_EULA,
    )
    cmds.menuItem(
        parent=menu,
        label="Third party notices",
        command=command_open_licenses_folder,
    )
    cmds.menuItem(
        parent=menu,
        label="Check for updates",
        command=command_check_for_updates,
    )
    cmds.menuItem(
        parent=menu,
        label="Documentation",
        command=command_open_documentation,
    )
    cmds.menuItem(
        parent=menu,
        label="About",
        command=command_show_about,
    )
    cmds.menuItem(
        parent=menu,
        divider=True,
    )
    cmds.menuItem(
        parent=menu,
        label=VERSION,
        enable=False,
    )


def uninstall_menu():
    if cmds.menu(MENU_NAME, exists=True):
        cmds.deleteUI(MENU_NAME, menu=True)


# --------------------------------------------------------------------------------------------------


# initialize the plug-in
def initializePlugin(plugin):
    om.MFnPlugin(plugin, "MetaHumanForMaya", VERSION, "Any")

    # check dependencies
    dependency_checks()

    # check for updates
    updates_check()

    # add menu items to the custom menu
    install_menu()


# uninitialize the plug-in
def uninitializePlugin(plugin):
    om.MFnPlugin(plugin)
    uninstall_menu()
