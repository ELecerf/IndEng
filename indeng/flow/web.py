"""Local browser interface for paired flow simulations."""
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import yaml

from indeng.config.loader import scenario_from_dict
from indeng.flow.engine import FlowEngine
from indeng.flow.model import COMPLEMENTS, FACTORIAL, MIX, POLICIES, STABLE, VARIANTS, make_inputs, study_from_scenario

DESIGNS = {design.name: design for design in (STABLE, MIX, *FACTORIAL, *COMPLEMENTS)}


def compare(config, design, seed, variants):
    study = study_from_scenario(scenario_from_dict(config))
    inputs = make_inputs(study, DESIGNS[design], int(seed))
    policies = POLICIES + VARIANTS if variants else POLICIES
    return [
        {"policy": policy, **FlowEngine(inputs, policy, study.defaults[policy.split("_")[0]]).run().kpis}
        for policy in policies
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--config", type=Path, default=Path("config/scenarios/flow_comparison.yaml"))
    args = parser.parse_args()
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    page = Path(__file__).with_name("comparison.html").read_bytes()

    class Handler(BaseHTTPRequestHandler):
        def send_data(self, status, data, mime="application/json"):
            self.send_response(status)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def send_json(self, status, data):
            self.send_data(status, json.dumps(data, allow_nan=False).encode())

        def do_GET(self):
            if self.path == "/":
                self.send_data(200, page, "text/html; charset=utf-8")
            elif self.path == "/api/config":
                self.send_json(200, {"config": config, "designs": list(DESIGNS)})
            else:
                self.send_error(404)

        def do_POST(self):
            if self.path != "/api/compare":
                self.send_error(404)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 100_000:
                    raise ValueError("Taille de la configuration invalide.")
                request = json.loads(self.rfile.read(length))
                rows = compare(request["config"], request["design"], request["seed"], request["variants"])
                self.send_json(200, rows)
            except (ValueError, TypeError, KeyError, AttributeError, OverflowError) as error:
                self.send_json(400, {"error": str(error)})

    with ThreadingHTTPServer(("127.0.0.1", args.port), Handler) as server:
        print(f"IndEng · http://127.0.0.1:{server.server_port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
