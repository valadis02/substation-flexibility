"""Minimal InfluxDB 1.x client over HTTP (stdlib only): chunked query to DataFrames, line-protocol write."""
import json, urllib.parse, urllib.request
import pandas as pd


class Influx:
    def __init__(self, url, db, timeout=60):
        self.url, self.db, self.timeout = url.rstrip("/"), db, timeout

    def query(self, q):
        """Run an InfluxQL query; returns a list of (tags, DataFrame indexed by UTC time)."""
        params = urllib.parse.urlencode(dict(db=self.db, q=q, epoch="s", chunked="true", chunk_size=10000))
        with urllib.request.urlopen(f"{self.url}/query?{params}", timeout=self.timeout) as r:
            body = r.read().decode()
        parts = {}
        for line in body.splitlines():
            if not line.strip():
                continue
            for res in json.loads(line).get("results", []):
                if "error" in res:
                    raise RuntimeError(res["error"])
                for s in res.get("series", []):
                    key = tuple(sorted((s.get("tags") or {}).items()))
                    df = pd.DataFrame(s["values"], columns=s["columns"])
                    parts.setdefault(key, []).append(df)
        out = []
        for key, dfs in parts.items():
            df = pd.concat(dfs)
            df.index = pd.to_datetime(df.pop("time"), unit="s", utc=True)
            out.append((dict(key), df.sort_index()))
        return out

    def write(self, lines, batch=5000):
        for i in range(0, len(lines), batch):
            req = urllib.request.Request(f"{self.url}/write?db={self.db}&precision=s",
                                         data="\n".join(lines[i:i + batch]).encode(), method="POST")
            urllib.request.urlopen(req, timeout=self.timeout)
        return len(lines)


def _esc(v):
    return str(v).replace(" ", r"\ ").replace(",", r"\,").replace("=", r"\=")


def to_lines(measurement, df, tags):
    """DataFrame (UTC index, numeric columns) -> line protocol; NaN fields are skipped, empty rows dropped."""
    tag = ",".join(f"{_esc(k)}={_esc(v)}" for k, v in tags.items())
    head = f"{measurement},{tag}" if tag else measurement
    lines = []
    for ts, row in df.iterrows():
        f = ",".join(f"{_esc(k)}={float(v)}" for k, v in row.items() if pd.notna(v))
        if f:
            lines.append(f"{head} {f} {int(ts.timestamp())}")
    return lines
