#!/usr/bin/env python3
"""Tests for the Dahua VTO codec guardian."""

import importlib.util
from pathlib import Path
import unittest

MODULE_PATH = Path(__file__).parents[1] / "files" / "vto_codec_guardian.py"
spec = importlib.util.spec_from_file_location("vto_codec_guardian", MODULE_PATH)
guardian = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guardian)


class ParseEncodeConfigTests(unittest.TestCase):
    def test_parses_only_required_main_audio_values(self):
        response = """\
table.Encode[0].ExtraFormat[0].Audio.Compression=PCM
table.Encode[0].ExtraFormat[0].Audio.Frequency=16000
table.Encode[0].MainFormat[0].Audio.Compression=G.711A
table.Encode[0].MainFormat[0].Audio.Frequency=8000
"""

        self.assertEqual(
            guardian.parse_encode_config(response),
            {"compression": "G.711A", "frequency": "8000"},
        )

    def test_rejects_response_missing_required_values(self):
        with self.assertRaisesRegex(
            guardian.GuardianError, "missing required main audio values"
        ):
            guardian.parse_encode_config(
                "table.Encode[0].ExtraFormat[0].Audio.Frequency=16000"
            )


class FakeResponse:
    def __init__(self, body, status=200):
        self.body = body.encode()
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.body


class FakeOpener:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.requests = []

    def open(self, url, timeout):
        self.requests.append((url, timeout))
        return next(self.responses)


class DahuaClientTests(unittest.TestCase):
    def test_reads_main_audio_state_through_get_config(self):
        opener = FakeOpener(
            [
                FakeResponse(
                    "table.Encode[0].MainFormat[0].Audio.Compression=G.711A\n"
                    "table.Encode[0].MainFormat[0].Audio.Frequency=8000\n"
                )
            ]
        )
        client = guardian.DahuaClient(
            "http://vto.example", "user", "secret", 7, opener=opener
        )

        state = client.read()

        self.assertEqual(state, {"compression": "G.711A", "frequency": "8000"})
        self.assertEqual(
            opener.requests,
            [
                (
                    "http://vto.example/cgi-bin/configManager.cgi?"
                    "action=getConfig&name=Encode",
                    7,
                )
            ],
        )

    def test_writes_only_requested_fields_through_set_config(self):
        opener = FakeOpener([FakeResponse("OK")])
        client = guardian.DahuaClient(
            "http://vto.example/", "user", "secret", 9, opener=opener
        )

        client.write({"frequency": "8000"})

        self.assertEqual(
            opener.requests,
            [
                (
                    "http://vto.example/cgi-bin/configManager.cgi?"
                    "action=setConfig&"
                    "Encode%5B0%5D.MainFormat%5B0%5D.Audio.Frequency=8000",
                    9,
                )
            ],
        )

    def test_rejects_unsuccessful_set_config_response(self):
        client = guardian.DahuaClient(
            "http://vto.example",
            "user",
            "secret",
            9,
            opener=FakeOpener([FakeResponse("Error")]),
        )

        with self.assertRaisesRegex(guardian.GuardianError, "returned 'Error'"):
            client.write({"frequency": "8000"})


class DahuaRequestTests(unittest.TestCase):
    def test_builds_set_query_from_only_requested_fields(self):
        query = guardian.build_set_query({"compression": "G.711A", "frequency": "8000"})

        self.assertEqual(
            query,
            "action=setConfig&"
            "Encode%5B0%5D.MainFormat%5B0%5D.Audio.Compression=G.711A&"
            "Encode%5B0%5D.MainFormat%5B0%5D.Audio.Frequency=8000",
        )


class FakeClient:
    def __init__(self, states):
        self.states = iter(states)
        self.writes = []

    def read(self):
        return next(self.states)

    def write(self, changes):
        self.writes.append(changes)


class GuardianEnforcementTests(unittest.TestCase):
    def test_compliant_state_performs_no_write(self):
        client = FakeClient([{"compression": "G.711A", "frequency": "8000"}])

        result = guardian.enforce_desired_state(client, "G.711A", "8000")

        self.assertEqual(result, "compliant")
        self.assertEqual(client.writes, [])

    def test_repairs_only_drifted_fields_and_verifies(self):
        client = FakeClient(
            [
                {"compression": "PCM", "frequency": "8000"},
                {"compression": "G.711A", "frequency": "8000"},
            ]
        )

        result = guardian.enforce_desired_state(client, "G.711A", "8000")

        self.assertEqual(result, "repaired")
        self.assertEqual(client.writes, [{"compression": "G.711A"}])

    def test_fails_when_repaired_state_does_not_verify(self):
        client = FakeClient(
            [
                {"compression": "PCM", "frequency": "16000"},
                {"compression": "PCM", "frequency": "16000"},
            ]
        )

        with self.assertRaisesRegex(guardian.GuardianError, "did not verify"):
            guardian.enforce_desired_state(client, "G.711A", "8000")

        self.assertEqual(
            client.writes,
            [{"compression": "G.711A", "frequency": "8000"}],
        )


if __name__ == "__main__":
    unittest.main()
