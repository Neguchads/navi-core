"""CycloneDX inventory of installed Python distributions, not a security verdict."""
from importlib import metadata
import re

from .cli import NaviError

def inventory(distributions=None):
    components = {}
    for dist in metadata.distributions() if distributions is None else distributions:
        name, version = dist.metadata.get("Name"), dist.version
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,199}", name):
            raise NaviError("Invalid installed distribution name")
        if not isinstance(version, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.!+_-]{0,199}", version):
            raise NaviError("Invalid installed distribution version")
        key = re.sub(r"[-_.]+", "-", name).lower()
        if key in components:
            raise NaviError("Duplicate installed distribution")
        component = {"type": "library", "name": key, "version": version,
                     "bom-ref": "pkg:pypi/" + key + "@" + version}
        # Only declared SPDX expressions; never include arbitrary license prose or paths.
        license_expression = dist.metadata.get("License-Expression")
        if isinstance(license_expression, str) and re.fullmatch(r"[A-Za-z0-9.()+ :\-]{1,200}", license_expression):
            component["properties"] = [{"name": "navi:declared-license-expression", "value": license_expression}]
        components[key] = component
    return {"bomFormat": "CycloneDX", "specVersion": "1.6", "version": 1,
            "metadata": {"properties": [{"name": "navi:scope", "value": "installed-python-environment; not release dependency closure or vulnerability/license clearance"}]},
            "components": [components[k] for k in sorted(components)]}
