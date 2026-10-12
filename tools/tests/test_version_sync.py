"""Cross-file consistency check for the three independent version numbers
(CLAUDE.md, "Three independent version numbers, decoupled since 1.0.1").

Each piece has two places its version must move together, and missing one is
documented there as a real, easy mistake: the addon's addon.xml.in and the
CoreELEC package.mk (CoreELEC packages the addon binary from the tag that
version names), and each plugin's plugin.json (only read for Dispatcharr's
not-yet-trusted import preview) and its plugin.py Plugin.version (what
Dispatcharr actually runs once trusted). Reads this repo's real files, like
test_timezone_settings_sync.py.
"""

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ADDON_XML_IN = REPO_ROOT / "pvr.dispatcharr-unofficial" / "addon.xml.in"
PACKAGE_MK = REPO_ROOT / "packaging" / "coreelec" / "pvr.dispatcharr-unofficial" / "package.mk"
CHANGELOG = REPO_ROOT / "CHANGELOG.md"
PLUGINS = ("timeshift_buffer", "recording_edl")

_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")

# The addon's own version may carry a release suffix after the semver core, which the two plugins' may not.
# Two reasons it has to be allowed here: Kodi's own addon-version grammar is `epoch:version-release`, so a
# `-<release>` part is a first-class part of the version it parses (and a non-empty release sorts *above* an
# empty one, which is what makes a Kodi 22 build upgrade cleanly over the same core version built for Kodi
# 21); and this project has shipped suffixed addon versions before -- `1.0.0-beta.1` through `-beta.3`, listed
# in docs/RELEASE_HISTORY.md and named as the convention by .github/workflows/build.yml's own tag trigger.
# The core must still be semver, and addon.xml.in and package.mk must still agree exactly.
_ADDON_VERSION = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.]+)?$")


def _addon_xml_version() -> str:
    text = ADDON_XML_IN.read_text(encoding="utf-8")
    # The <addon ...> element's own version attribute, not an <import>'s: the
    # first version="..." in the file belongs to the <?xml ...?> declaration
    # and is skipped by anchoring on the addon element.
    match = re.search(r"<addon\b[^>]*?\sversion=\"([^\"]+)\"", text, re.DOTALL)
    assert match, "no <addon version=...> in addon.xml.in"
    return match.group(1)


def _package_mk_version() -> str:
    match = re.search(r'^PKG_VERSION="([^"]+)"', PACKAGE_MK.read_text(encoding="utf-8"), re.MULTILINE)
    assert match, "no PKG_VERSION in package.mk"
    return match.group(1)


def _plugin_json_version(plugin: str) -> str:
    return json.loads((REPO_ROOT / "dispatcharr-plugin" / plugin / "plugin.json").read_text(encoding="utf-8"))[
        "version"
    ]


def _plugin_py_version(plugin: str) -> str:
    text = (REPO_ROOT / "dispatcharr-plugin" / plugin / "plugin.py").read_text(encoding="utf-8")
    # The Plugin class attribute, not the HTTP handler's server_version string.
    match = re.search(r"^class Plugin:\n(?:.*\n)*?\s+version = \"([^\"]+)\"", text, re.MULTILINE)
    assert match, f"no Plugin.version in {plugin}/plugin.py"
    return match.group(1)


def test_addon_version_is_semver_and_matches_the_coreelec_package():
    version = _addon_xml_version()
    assert _ADDON_VERSION.match(version), version
    assert _package_mk_version() == version, "addon.xml.in and packaging/coreelec/.../package.mk disagree"


def test_addon_version_has_a_changelog_entry():
    # CHANGELOG.md's addon entries are "## [X.Y.Z] - date"; a plugin's are
    # "## `name` [X.Y.Z] - date". The current addon version must have one.
    version = _addon_xml_version()
    assert f"## [{version}]" in CHANGELOG.read_text(encoding="utf-8"), f"no CHANGELOG.md entry for {version}"


@pytest.mark.parametrize("plugin", PLUGINS)
def test_plugin_json_and_plugin_py_versions_match(plugin):
    json_version = _plugin_json_version(plugin)
    assert _SEMVER.match(json_version), json_version
    assert _plugin_py_version(plugin) == json_version, f"{plugin}: plugin.json and plugin.py's Plugin.version disagree"


@pytest.mark.parametrize("plugin", PLUGINS)
def test_plugin_version_has_a_changelog_entry(plugin):
    version = _plugin_json_version(plugin)
    assert f"## `{plugin}` [{version}]" in CHANGELOG.read_text(
        encoding="utf-8"
    ), f"no CHANGELOG.md entry for {plugin} {version}"
