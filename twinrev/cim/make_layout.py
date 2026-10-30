"""Usage: python3 make_layout.py <cim-grid-data>/IEEE_EU_LV/IEEE_EU_LV_reduced ../service/lv_layout.json

Single-line diagram of the IEEE European LV feeder for the network view (GET /view): positions from the CIM diagram
layout (DI) of the public NEPLAN export, connectivity from its topology (TP). Loads are named lod_01..lod_55 as in
make_lv_zip.py. Output: nodes {name: [x, y]}, lines {name: {path, nodes}}, loads {lod: {pos, node}}, trafo, source.
"""
import collections, glob, json, os, re, sys

src, out_path = sys.argv[1], sys.argv[2]
part = lambda p: open(glob.glob(os.path.join(src, f"*_{p}.xml"))[0], encoding="utf-8").read()
eq, tp, di = part("EQ"), part("TP"), part("DI")

objs = {}
for text in (eq, tp):
    for cls, rid, body in re.findall(r'<cim:(\w+) rdf:ID="([^"]+)">(.*?)</cim:\1>', text, re.S):
        n = re.search(r"<cim:IdentifiedObject\.name>([^<]*)", body)
        objs[rid] = (cls, n.group(1) if n else None)

term_node = {rid: re.search(r'TopologicalNode rdf:resource="#([^"]+)', b).group(1)
             for rid, b in re.findall(r'<cim:Terminal rdf:about="#([^"]+)">(.*?)</cim:Terminal>', tp, re.S)
             if "TopologicalNode" in b}
conn = collections.defaultdict(list)
for rid, b in re.findall(r'<cim:Terminal rdf:ID="([^"]+)">(.*?)</cim:Terminal>', eq, re.S):
    e = re.search(r'ConductingEquipment rdf:resource="#([^"]+)', b).group(1)
    if rid in term_node:
        conn[e].append(objs[term_node[rid]][1])

pts = collections.defaultdict(list)
for b in re.findall(r"<cim:DiagramObjectPoint [^>]*>(.*?)</cim:DiagramObjectPoint>", di, re.S):
    d = re.search(r'DiagramObject rdf:resource="#([^"]+)', b).group(1)
    pts[d].append((int(re.search(r"sequenceNumber>(\d+)", b).group(1)),
                   round(float(re.search(r"xPosition>([^<]*)", b).group(1)), 1),
                   round(float(re.search(r"yPosition>([^<]*)", b).group(1)), 1)))

out = dict(source="IEEE European LV test feeder, NEPLAN CIM export (dpsim-simulator/cim-grid-data), diagram layout",
           nodes={}, lines={}, loads={}, trafo=None, infeed=None)
for d, b in re.findall(r'<cim:DiagramObject rdf:ID="([^"]+)">(.*?)</cim:DiagramObject>', di, re.S):
    obj = re.search(r'IdentifiedObject rdf:resource="#([^"]+)', b).group(1)
    cls, name = objs[obj]
    p = [[x, y] for _, x, y in sorted(pts.get(d, []))]
    if not p:
        continue
    if cls == "TopologicalNode":
        out["nodes"][name] = [round(sum(q[0] for q in p) / len(p), 1), round(sum(q[1] for q in p) / len(p), 1)]
    elif cls == "ACLineSegment":
        out["lines"][name] = dict(path=p, nodes=conn[obj])
    elif cls == "EnergyConsumer":
        out["loads"]["lod_%02d" % int(name[2:])] = dict(pos=p[0], node=(conn[obj] or [None])[0])
    elif cls == "PowerTransformer":
        out["trafo"] = dict(name=name, pos=p[0], nodes=conn[obj])
    elif cls == "ExternalNetworkInjection":
        out["infeed"] = p[0]
json.dump(out, open(out_path, "w"), separators=(",", ":"))
print(f"nodes {len(out['nodes'])}, lines {len(out['lines'])}, loads {len(out['loads'])}, trafo {out['trafo']} -> {out_path}")
