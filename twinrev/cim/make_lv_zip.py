"""Usage: python3 make_lv_zip.py <cim-grid-data>/IEEE_EU_LV/IEEE_EU_LV_reduced cel3_lv200.zip
       (published test case instead: --trafo-kva 800 --main-r-ohm-km 0.249 and another archive name)

Public IEEE European LV test feeder (NEPLAN CIM export, dpsim-simulator/cim-grid-data) packaged for the TWIN-REV DSO
pipeline as cell 3: loads PQ1..PQ55 renamed lod_01..lod_55 (dpsv matches profiles to DPsim names by prefix, so PQ1
would also catch PQ10..PQ19), SV saved as _SSH (NEPLAN CIM16 has no SSH).

Design for the 55 Austin homes (defaults). The published feeder is sized for UK homes; Austin homes peak at about twice
the load (air conditioning), so with the published cables the feeder is over its limits already today. The defaults
size the feeder the way a DSO would for these homes, leaving no headroom (a network at the edge of its capacity):
  --trafo-kva 200       the test case keeps the whole 800 kVA substation transformer for this one feeder, while a
                        substation of that size supplies several feeders; the feeder's share is a 200 kVA transformer
                        (IEC R10 size; today's yearly peak ~98 %) with the same per-unit impedance (uk 4 %): ratedS set,
                        r and x scaled by 800/kVA.
  --main-r-ohm-km 0.164 main cable one size up, Al 185 mm2 instead of Al 120 mm2 (0.249 ohm/km).

The archive name must be new whenever the grid changes (TWIN-REV's DPsim service keeps the XMLs of an archive name it
has seen); the XMLs inside carry the archive name. --lines-json writes each line's resistance (ohm/km) and cable
class, from which the service takes the thermal rating (the CIM has no current limits).
"""
import argparse, re, zipfile, os
ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("out"); ap.add_argument("--trafo-kva", type=float, default=200.0)
ap.add_argument("--lines-json")
ap.add_argument("--main-r-ohm-km", type=float, default=0.164,
                help="main cable class resistance (published 0.249 = Al 120 mm2; default 0.164 = Al 185 mm2)")
a = ap.parse_args()
name = os.path.basename(a.out)[:-4]           # XMLs inside must carry the archive name
files = {f.split("_")[-1].split(".")[0]: os.path.join(a.src, f) for f in os.listdir(a.src) if f.endswith(".xml")}
eq = open(files["EQ"], encoding="utf-8").read()
def ren(m):
    return re.sub(r"(<cim:IdentifiedObject\.name>)PQ(\d+)(</cim:IdentifiedObject\.name>)",
                  lambda n: f"{n.group(1)}lod_{int(n.group(2)):02d}{n.group(3)}", m.group(0))
eq, n = re.subn(r"<cim:EnergyConsumer [^>]*>.*?</cim:EnergyConsumer>", ren, eq, flags=re.S)
print("EnergyConsumer blocks:", n, "renamed:", len(re.findall(r">lod_\d\d<", eq)))
k = 800.0 / a.trafo_kva
def trafo(m):
    b = m.group(0)
    b = re.sub(r"(<cim:PowerTransformerEnd\.ratedS>)[^<]*", lambda t: f"{t.group(1)}{a.trafo_kva / 1000:.6f}", b)
    for f in ("r", "x"):
        b = re.sub(rf"(<cim:PowerTransformerEnd\.{f}>)([^<]*)", lambda t: f"{t.group(1)}{float(t.group(2)) * k:.6f}", b)
    return b
eq, nt = re.subn(r"<cim:PowerTransformerEnd [^>]*>.*?</cim:PowerTransformerEnd>", trafo, eq, flags=re.S)
print(f"transformer ends: {nt}, rating {a.trafo_kva:g} kVA (impedance x{k:.2f})")
if a.main_r_ohm_km and abs(a.main_r_ohm_km - 0.249) > 1e-6:
    def upsize(m):
        b = m.group(0)
        L = float(re.search(r"<cim:Conductor\.length>([^<]*)", b).group(1))
        r = float(re.search(r"<cim:ACLineSegment\.r>([^<]*)", b).group(1))
        if r / L >= 0.5:
            return b
        return re.sub(r"(<cim:ACLineSegment\.r>)[^<]*", lambda t: f"{t.group(1)}{a.main_r_ohm_km * L:.6f}", b)
    eq = re.sub(r"<cim:ACLineSegment [^>]*>.*?</cim:ACLineSegment>", upsize, eq, flags=re.S)
    print(f"main cable class: {a.main_r_ohm_km} ohm/km")
if a.lines_json:
    import json
    lines = {}
    for b in re.findall(r"<cim:ACLineSegment [^>]*>.*?</cim:ACLineSegment>", eq, re.S):
        g = lambda t: re.search(rf"<cim:{t}>([^<]*)", b).group(1)
        r_km = float(g("ACLineSegment.r")) / float(g("Conductor.length"))
        lines[g("IdentifiedObject.name")] = dict(r_ohm_km=round(r_km, 4), cls="main" if r_km < 0.5 else "branch")
    json.dump(dict(dict(source="IEEE European LV test feeder, NEPLAN CIM export (dpsim-simulator/cim-grid-data)"), lines=lines),
              open(a.lines_json, "w"), indent=1)
    print(f"lines: {len(lines)} -> {a.lines_json}")
with zipfile.ZipFile(a.out, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr(f"{name}_EQ.xml", eq)
    z.write(files["TP"], f"{name}_TP.xml")
    z.write(files["SV"], f"{name}_SSH.xml")
print("wrote", a.out)
