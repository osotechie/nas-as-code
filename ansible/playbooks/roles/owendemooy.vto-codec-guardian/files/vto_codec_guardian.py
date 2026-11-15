#!/usr/bin/env python3
"""Keep a Dahua VTO main audio codec at its desired state."""

import argparse
import json
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlencode
from urllib.request import (
    HTTPDigestAuthHandler,
    HTTPPasswordMgrWithDefaultRealm,
    build_opener,
)

COMPRESSION_RESPONSE_KEY = "table.Encode[0].MainFormat[0].Audio.Compression"
FREQUENCY_RESPONSE_KEY = "table.Encode[0].MainFormat[0].Audio.Frequency"


class GuardianError(RuntimeError):
    """The VTO state could not be read, repaired, or verified."""


REQUEST_KEYS = {
    "compression": "Encode[0].MainFormat[0].Audio.Compression",
    "frequency": "Encode[0].MainFormat[0].Audio.Frequency",
}


def build_set_query(changes):
    """Build a Dahua setConfig query for only the requested fields."""
    parameters = [("action", "setConfig")]
    parameters.extend((REQUEST_KEYS[key], value) for key, value in changes.items())
    return urlencode(parameters)


class DahuaClient:
    """Minimal Digest-authenticated client for Dahua configManager.cgi."""

    def __init__(self, base_url, username, password, timeout, opener=None):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        if opener is None:
            password_manager = HTTPPasswordMgrWithDefaultRealm()
            password_manager.add_password(None, self.base_url, username, password)
            opener = build_opener(HTTPDigestAuthHandler(password_manager))
        self.opener = opener

    def _request(self, query):
        url = f"{self.base_url}/cgi-bin/configManager.cgi?{query}"
        with self.opener.open(url, timeout=self.timeout) as response:
            return response.read().decode("utf-8", "replace")

    def read(self):
        """Read and parse the current main audio state."""
        return parse_encode_config(self._request("action=getConfig&name=Encode"))

    def write(self, changes):
        """Apply only requested main audio field changes."""
        response = self._request(build_set_query(changes)).strip()
        if response != "OK":
            raise GuardianError(f"Dahua setConfig returned {response!r}")


def parse_encode_config(response):
    """Return the main audio compression and frequency from a CGI response."""
    values = {}
    for line in response.splitlines():
        key, separator, value = line.partition("=")
        if separator:
            values[key] = value
    try:
        return {
            "compression": values[COMPRESSION_RESPONSE_KEY],
            "frequency": values[FREQUENCY_RESPONSE_KEY],
        }
    except KeyError as error:
        raise GuardianError(
            "Dahua response is missing required main audio values"
        ) from error


def enforce_desired_state(client, desired_compression, desired_frequency):
    """Repair and verify only the main audio fields that have drifted."""
    desired = {
        "compression": desired_compression,
        "frequency": desired_frequency,
    }
    current = client.read()
    changes = {key: value for key, value in desired.items() if current[key] != value}
    if not changes:
        return "compliant"

    client.write(changes)
    verified = client.read()
    if verified != desired:
        raise GuardianError("VTO main audio state did not verify after repair")
    return "repaired"


def load_config(path):
    """Load and validate the guardian's root-only JSON configuration."""
    with Path(path).open(encoding="utf-8") as config_file:
        config = json.load(config_file)

    required = (
        "base_url",
        "username",
        "password",
        "timeout_seconds",
        "desired_compression",
        "desired_frequency",
    )
    missing = [key for key in required if key not in config or config[key] == ""]
    if missing:
        raise GuardianError(f"Guardian configuration is missing: {', '.join(missing)}")
    if not str(config["base_url"]).startswith(("http://", "https://")):
        raise GuardianError("Guardian base_url must use http:// or https://")
    return config


def write_journal(message, priority):
    """Write an actionable, credential-free event through syslog."""
    subprocess.run(
        [
            "/usr/bin/logger",
            "--tag",
            "vto-codec-guardian",
            "--priority",
            f"user.{priority}",
            "--",
            message,
        ],
        check=False,
    )


def main(argv=None):
    """Run one compliance check, optionally repairing drift."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
        client = DahuaClient(
            config["base_url"],
            config["username"],
            config["password"],
            float(config["timeout_seconds"]),
        )
        desired_compression = str(config["desired_compression"])
        desired_frequency = str(config["desired_frequency"])

        if args.check_only:
            current = client.read()
            compliant = current == {
                "compression": desired_compression,
                "frequency": desired_frequency,
            }
            print(
                "compression={} frequency={} compliant={}".format(
                    current["compression"],
                    current["frequency"],
                    str(compliant).lower(),
                )
            )
            return 0 if compliant else 2

        result = enforce_desired_state(client, desired_compression, desired_frequency)
        if result == "repaired":
            write_journal(
                "Repaired and verified VTO main audio codec as "
                f"{desired_compression}/{desired_frequency}",
                "warning",
            )
        return 0
    except Exception as error:  # cron must make all failures actionable
        message = f"VTO codec check failed: {error}"
        write_journal(message, "err")
        print(message, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
