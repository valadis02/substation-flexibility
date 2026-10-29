"""In-memory stand-in for InfluxDB 1.x, enough for the service's own writes and queries (local testing only)."""
import json, re, threading, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime, timezone

POINTS = {}   # (measurement, tags tuple) -> {ts: {field: value}}


def _parse(line):
    head, fields, ts = line.rsplit(" ", 2) if line.count(" ") >= 2 else (None, None, None)
    m, *tags = head.split(",")
    tags = tuple(sorted(tuple(t.split("=", 1)) for t in tags))
    f = {k: float(v) for k, v in (p.split("=", 1) for p in fields.split(","))}
    POINTS.setdefault((m, tags), {}).setdefault(int(ts), {}).update(f)


def _ts(s):
    return int(datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp())


Q = re.compile(r"SELECT (?P<f>.+?) FROM (?P<m>\w+) WHERE site='(?P<site>[^']+)' AND time >= '(?P<t0>[^']+)' AND time < '(?P<t1>[^']+)'(?: GROUP BY (?P<g>\w+))?")


L = re.compile(r"SELECT last\((?P<f>\w+)\) FROM (?P<m>\w+) WHERE site='(?P<site>[^']+)' GROUP BY (?P<g>\w+)")


def _query(q):
    l = L.match(q)
    if l:
        series = [{"name": meas, "tags": {l["g"]: dict(tags)[l["g"]]}, "columns": ["time", "last"],
                   "values": [[max(t for t in pts if l["f"] in pts[t]), None]]}
                  for (meas, tags), pts in POINTS.items() if meas == l["m"] and dict(tags).get("site") == l["site"]]
        return {"results": [{"statement_id": 0, "series": series}]}
    m = Q.match(q)
    fields = [x.strip() for x in m["f"].split(",")]
    t0, t1 = _ts(m["t0"]), _ts(m["t1"])
    series = []
    for (meas, tags), pts in POINTS.items():
        td = dict(tags)
        if meas != m["m"] or td.get("site") != m["site"]:
            continue
        rows = [[t] + [pts[t].get(f) for f in fields] for t in sorted(pts) if t0 <= t < t1]
        if rows:
            s = {"name": meas, "columns": ["time"] + fields, "values": rows}
            if m["g"]:
                s["tags"] = {m["g"]: td[m["g"]]}
            series.append(s)
    return {"results": [{"statement_id": 0, "series": series}]}


class H(BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"])).decode()
        for line in body.splitlines():
            if line.strip():
                _parse(line)
        self.send_response(204); self.end_headers()

    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)["q"][0]
        out = json.dumps(_query(q)).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(out)

    def log_message(self, *a):
        pass


def serve(port=18086):
    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv
