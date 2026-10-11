import json, os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

base = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(base, "q-vercel-latency.json")
if not os.path.exists(path):
    path = os.path.join(base, "..", "q-vercel-latency.json")
with open(path) as f:
    DATA = json.load(f)
if isinstance(DATA, dict):
    for v in DATA.values():
        if isinstance(v, list):
            DATA = v
            break

def pick(r, *names):
    for n in names:
        if n in r:
            return r[n]
    return None

def percentile(vals, p):
    s = sorted(vals)
    if not s:
        return 0.0
    k = (len(s) - 1) * p / 100
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)

@app.post("/")
@app.post("/api/latency")
@app.post("/api")
async def latency(request: Request):
    body = await request.json()
    regions = body.get("regions", [])
    threshold = body.get("threshold_ms", 180)
    out = {}
    for reg in regions:
        rows = [r for r in DATA if pick(r, "region") == reg]
        lat = [pick(r, "latency_ms", "latency") for r in rows]
        lat = [x for x in lat if x is not None]
        up = [pick(r, "uptime_pct", "uptime") for r in rows]
        up = [x for x in up if x is not None]
        out[reg] = {
            "avg_latency": sum(lat) / len(lat) if lat else 0,
            "p95_latency": percentile(lat, 95),
            "avg_uptime": sum(up) / len(up) if up else 0,
            "breaches": sum(1 for x in lat if x > threshold),
        }
    return {"regions": out, **out}
