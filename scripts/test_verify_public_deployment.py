import importlib.util
from pathlib import Path
import unittest


SCRIPT_PATH = Path(__file__).with_name("verify-public-deployment.py")
SPEC = importlib.util.spec_from_file_location("verify_public_deployment", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class FakeResponse:
    def __init__(self, url, status_code=200, text="AgriPay Logistics AI"):
        self.url = url
        self.status_code = status_code
        self.text = text


class VerifyPublicDeploymentTests(unittest.TestCase):
    def test_checks_all_required_public_routes(self):
        requested = []

        def fake_get(url, timeout):
            requested.append((url, timeout))
            return FakeResponse(url)

        results = MODULE.verify_deployment("https://example.test", get=fake_get)

        self.assertEqual(
            [url for url, _timeout in requested],
            [
                "https://example.test/",
                "https://example.test/landing",
                "https://example.test/login",
                "https://example.test/health/",
            ],
        )
        self.assertTrue(all(result["ok"] for result in results))

    def test_rejects_success_page_without_agripay_identity(self):
        def fake_get(url, timeout):
            return FakeResponse(url, text="Unrelated application")

        results = MODULE.verify_deployment("https://example.test", get=fake_get)

        self.assertFalse(results[0]["ok"])
        self.assertIn("AgriPay", results[0]["error"])


if __name__ == "__main__":
    unittest.main()