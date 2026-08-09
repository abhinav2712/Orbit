"""Schema/rule validation for generated zerops.yaml — pure function, no network calls."""

from __future__ import annotations

import yaml

ALLOWED_BASE_PREFIXES = (
    "python@",
    "alpine/python@",
    "nodejs@",
    "alpine/nodejs@",
    "go@",
    "alpine/go@",
    "static",
    "php@",
    "alpine/php@",
)


def validate_zerops_yaml(yaml_text: str) -> list[str]:
    """Returns a list of human-readable errors. Empty list = valid."""
    try:
        doc = yaml.safe_load(yaml_text)
    except yaml.YAMLError as e:
        return [f"not valid YAML: {e}"]

    if not isinstance(doc, dict) or "zerops" not in doc:
        return ["top-level 'zerops:' key is missing"]

    services = doc["zerops"]
    if not isinstance(services, list) or not services:
        return ["'zerops:' must be a non-empty list of service blocks"]

    errors: list[str] = []
    seen_setups = set()

    for i, svc in enumerate(services):
        prefix = f"service #{i + 1}"
        if not isinstance(svc, dict) or "setup" not in svc:
            errors.append(f"{prefix}: missing required 'setup' key")
            continue

        setup_name = svc["setup"]
        prefix = f"service '{setup_name}'"
        if setup_name in seen_setups:
            errors.append(f"{prefix}: duplicate setup name")
        seen_setups.add(setup_name)

        if "run" not in svc or not isinstance(svc["run"], dict):
            errors.append(f"{prefix}: missing or invalid 'run' block")
            continue
        run = svc["run"]

        base = run.get("base") or (svc.get("build") or {}).get("base")
        if base and not str(base).startswith(ALLOWED_BASE_PREFIXES):
            errors.append(
                f"{prefix}: base image '{base}' isn't on the known-good allowlist"
            )

        if "start" not in run and "startCommands" not in run and base != "static":
            errors.append(
                f"{prefix}: 'run' needs 'start' or 'startCommands' (unless base is 'static')"
            )

        ports = run.get("ports")
        if ports is not None:
            if not isinstance(ports, list):
                errors.append(f"{prefix}: 'run.ports' must be a list")
            else:
                for p in ports:
                    port_val = p.get("port") if isinstance(p, dict) else p
                    if not isinstance(port_val, int) or not (10 <= port_val <= 65435):
                        errors.append(
                            f"{prefix}: port '{port_val}' must be an int in 10-65435"
                        )

        build = svc.get("build")
        if build and not build.get("deployFiles"):
            errors.append(f"{prefix}: 'build' block present but missing 'deployFiles'")

    return errors
