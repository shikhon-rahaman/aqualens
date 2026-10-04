"""Smoke test script: Full flow against deployed URL.

Tests the complete citizen observation flow end-to-end:
1. Health check
2. Fetch sites
3. Fetch form schema
4. Create observation (without photos for simplicity)
5. Fetch observation detail
6. Fetch FHIR export
7. List observations on map
8. Expert queue (with PIN)

Usage:
    python scripts/smoke_test.py https://your-deployed-backend.com
    python scripts/smoke_test.py http://localhost:8000  # Local test
"""

import json
import sys
import time
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


class SmokeTest:
    def __init__(self, base_url: str, expert_pin: str = "change-me"):
        self.base_url = base_url.rstrip("/")
        self.expert_pin = expert_pin
        self.passed = 0
        self.failed = 0
        self.warnings = 0

    def request(
        self,
        method: str,
        path: str,
        data: Any = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Make HTTP request."""
        url = f"{self.base_url}{path}"
        req_headers = {"Content-Type": "application/json"}
        if headers:
            req_headers.update(headers)

        body = json.dumps(data).encode("utf-8") if data else None
        req = Request(url, data=body, headers=req_headers, method=method)

        try:
            with urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as e:
            error_body = e.read().decode("utf-8")
            try:
                error_json = json.loads(error_body)
                raise Exception(
                    f"HTTP {e.code}: {error_json.get('detail', error_body)}"
                )
            except json.JSONDecodeError:
                raise Exception(f"HTTP {e.code}: {error_body}")
        except URLError as e:
            raise Exception(f"Connection failed: {e.reason}")

    def test(self, name: str, func):
        """Run a test and track results."""
        print(f"\n{'='*60}")
        print(f"TEST: {name}")
        print("=" * 60)
        try:
            func()
            print(f"[+] PASS: {name}")
            self.passed += 1
        except Exception as e:
            print(f"[X] FAIL: {name}")
            print(f"  Error: {e}")
            self.failed += 1

    def warn(self, message: str):
        """Print warning."""
        print(f"[!] WARNING: {message}")
        self.warnings += 1

    def run(self):
        """Run all smoke tests."""
        print("\n" + "=" * 60)
        print("AQUALENS SMOKE TEST")
        print(f"Target: {self.base_url}")
        print("=" * 60)

        # Test 1: Health check
        self.test("Health check", self.test_health)

        # Test 2: Form schema
        self.test("Form schema", self.test_form_schema)

        # Test 3: Sites list
        site_id = None
        def test_sites_wrapper():
            nonlocal site_id
            site_id = self.test_sites()
        self.test("Sites list", test_sites_wrapper)

        if not site_id:
            self.warn("No sites available, skipping observation tests")
        else:
            # Test 4: Create observation
            obs_id = None
            def test_create_wrapper():
                nonlocal obs_id
                obs_id = self.test_create_observation(site_id)
            self.test("Create observation", test_create_wrapper)

            if obs_id:
                # Test 5: Fetch observation
                self.test(
                    "Fetch observation detail",
                    lambda: self.test_fetch_observation(obs_id)
                )

                # Test 6: FHIR export
                self.test(
                    "FHIR export",
                    lambda: self.test_fhir_export(obs_id)
                )

                # Test 7: List observations
                self.test("List observations", self.test_list_observations)

                # Test 8: Expert queue (requires PIN)
                self.test("Expert queue", self.test_expert_queue)

        # Summary
        print("\n" + "=" * 60)
        print("SMOKE TEST SUMMARY")
        print("=" * 60)
        print(f"Passed:   {self.passed}")
        print(f"Failed:   {self.failed}")
        print(f"Warnings: {self.warnings}")
        print("=" * 60)

        if self.failed > 0:
            print("[X] SMOKE TEST FAILED")
            sys.exit(1)
        elif self.warnings > 0:
            print("[!] SMOKE TEST PASSED WITH WARNINGS")
            sys.exit(0)
        else:
            print("[+] SMOKE TEST PASSED")
            sys.exit(0)

    def test_health(self):
        """Test health endpoint."""
        resp = self.request("GET", "/health")
        assert resp["status"] == "ok", "Health status not ok"
        assert "ai_chain" in resp, "Missing ai_chain"
        assert "db" in resp, "Missing db"
        print(f"  Status: {resp['status']}")
        print(f"  AI Chain: {' -> '.join(resp['ai_chain'])}")
        print(f"  DB: {resp['db']}")

    def test_form_schema(self):
        """Test form schema endpoint."""
        resp = self.request("GET", "/api/form-schema")
        assert "fields" in resp, "Missing fields"
        assert len(resp["fields"]) > 0, "No fields in schema"
        print(f"  Fields: {len(resp['fields'])}")

    def test_sites(self) -> str | None:
        """Test sites endpoint."""
        resp = self.request("GET", "/api/sites")
        assert "sites" in resp, "Missing sites"
        sites = resp["sites"]
        assert len(sites) > 0, "No sites available"
        print(f"  Sites: {len(sites)}")
        demo_sites = [s for s in sites if s.get("is_demo")]
        print(f"  Demo sites: {len(demo_sites)}")
        return sites[0]["id"]

    def test_create_observation(self, site_id: str) -> str:
        """Test creating an observation."""
        payload = {
            "site_id": site_id,
            "facing_downstream": True,
            "answers": {
                "channel_form": "A",
                "bottom_type": "A",
                "bank_type": "A",
                "water_flow": "B",
                "water_aspect": "A",
                "water_withdrawal": "no",
                "barriers": "no",
                "draining_pipes": "no",
                "sewage_discharge": "no",
                "construction": "no",
                "impervious_left": "no",
                "impervious_right": "no",
                "vegetation_left": "yes",
                "vegetation_right": "yes",
                "veg_type_left": "C",
                "veg_type_right": "C",
                "invasive_species": "no",
                "vegetation_cuts": "no",
                "overall_assessment": "good",
                "feelings": {
                    "joy": {"value": 4, "na": False},
                    "serenity": {"value": 5, "na": False},
                    "anger": {"value": 1, "na": False},
                    "fear": {"value": 1, "na": False},
                },
            },
            "field_sources": {
                "channel_form": "human",
                "bottom_type": "human",
                "bank_type": "human",
                "water_flow": "human",
                "water_aspect": "human",
                "water_withdrawal": "human",
                "barriers": "human",
                "draining_pipes": "human",
                "sewage_discharge": "human",
                "construction": "human",
                "impervious_left": "human",
                "impervious_right": "human",
                "vegetation_left": "human",
                "vegetation_right": "human",
                "veg_type_left": "human",
                "veg_type_right": "human",
                "invasive_species": "human",
                "vegetation_cuts": "human",
                "overall_assessment": "human",
                "feelings": "human",
            },
            "ai_suggestions": {},
            "status": "confirmed",
            "overall_user": "good",
        }

        resp = self.request("POST", "/api/observations/json", data=payload)
        assert "id" in resp, "Missing observation ID"
        obs_id = resp["id"]
        print(f"  Created observation: {obs_id}")
        print(f"  Status: {resp.get('status')}")
        print(f"  Risk ecosystem: {resp.get('risk_ecosystem')}")
        return obs_id

    def test_fetch_observation(self, obs_id: str):
        """Test fetching observation detail."""
        resp = self.request("GET", f"/api/observations/{obs_id}")
        assert resp["id"] == obs_id, "Observation ID mismatch"
        assert "answers" in resp, "Missing answers"
        assert "field_sources" in resp, "Missing field_sources"
        print(f"  ID: {resp['id']}")
        print(f"  Site: {resp.get('site_name')}")
        print(f"  Overall: {resp.get('overall_user')} (user) / {resp.get('overall_suggested')} (suggested)")

    def test_fhir_export(self, obs_id: str):
        """Test FHIR export."""
        resp = self.request("GET", f"/api/observations/{obs_id}/fhir")
        assert "bundle" in resp, "Missing FHIR bundle"
        assert "excluded" in resp, "Missing excluded fields"
        bundle = resp["bundle"]
        assert bundle["resourceType"] == "Bundle", "Not a FHIR Bundle"
        print(f"  Bundle entries: {len(bundle.get('entry', []))}")
        print(f"  Excluded fields: {len(resp['excluded'])}")

    def test_list_observations(self):
        """Test listing observations."""
        resp = self.request("GET", "/api/observations")
        assert "observations" in resp, "Missing observations"
        observations = resp["observations"]
        print(f"  Total observations: {len(observations)}")
        if observations:
            synthetic = [o for o in observations if o.get("is_synthetic")]
            print(f"  Synthetic: {len(synthetic)}")
            needs_review = [o for o in observations if o.get("needs_expert")]
            print(f"  Needs review: {len(needs_review)}")

    def test_expert_queue(self):
        """Test expert queue endpoint."""
        try:
            resp = self.request(
                "GET",
                "/api/queue",
                headers={"X-Expert-Pin": self.expert_pin}
            )
            assert "observations" in resp, "Missing observations"
            queue = resp["observations"]
            print(f"  Queue size: {len(queue)}")
            if len(queue) == 0:
                self.warn("Expert queue is empty - no observations need review")
        except Exception as e:
            if "401" in str(e) or "Invalid" in str(e):
                self.warn(f"Expert PIN authentication failed (PIN: {self.expert_pin})")
                self.warn("Set correct PIN: python scripts/smoke_test.py <url> <pin>")
            else:
                raise


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/smoke_test.py <base_url> [expert_pin]")
        print("Example: python scripts/smoke_test.py https://aqualens-api.onrender.com")
        print("Example: python scripts/smoke_test.py http://localhost:8000 my-pin")
        sys.exit(1)

    base_url = sys.argv[1]
    expert_pin = sys.argv[2] if len(sys.argv) > 2 else "change-me"

    test = SmokeTest(base_url, expert_pin)
    test.run()


if __name__ == "__main__":
    main()
