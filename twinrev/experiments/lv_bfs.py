"""Offline power flow of the feeder archive made by cim/make_lv_zip.py (balanced backward-forward sweep), used only for
tests and for a quick look without the stack. The experiment's results come from TWIN-REV + DPsim (ev_capacity.py --backend twinrev)."""
import json, os, re, zipfile
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LV_BASE_V = 400.0


class Feeder:
    def __init__(self, archive, trafo_kva, main_a=340.0, branch_a=145.0):
        z = zipfile.ZipFile(archive)
        name = lambda s: next(n for n in z.namelist() if n.endswith(s))
        eq, tp, sv = (z.read(name(s)).decode("utf-8") for s in ("_EQ.xml", "_TP.xml", "_SSH.xml"))
        self.trafo_kva = trafo_kva
        term_node = {m[0]: m[1] for m in re.findall(r'<cim:Terminal rdf:about="#([^"]+)">.*?TopologicalNode rdf:resource="#([^"]+)"', tp, re.S)}
        eq_nodes = {}
        for tid, ce in re.findall(r'<cim:Terminal rdf:ID="([^"]+)">.*?ConductingEquipment rdf:resource="#([^"]+)"', eq, re.S):
            if tid in term_node:
                eq_nodes.setdefault(ce, []).append(term_node[tid])
        lines = json.load(open(os.path.join(HERE, "..", "service", "lv_lines.json")))["lines"]
        edges = []
        for b in re.findall(r'<cim:ACLineSegment rdf:ID="[^"]+">.*?</cim:ACLineSegment>', eq, re.S):
            g = lambda t: re.search(rf"<cim:{t}>([^<]*)", b).group(1)
            n, rid = g("IdentifiedObject.name"), re.search(r'rdf:ID="([^"]+)"', b).group(1)
            edges.append((n, *eq_nodes[rid], complex(float(g("ACLineSegment.r")), float(g("ACLineSegment.x")))))
        self.rating = {n: (main_a if lines[n]["cls"] == "main" else branch_a) for n, *_ in edges}
        ends = re.findall(r"<cim:PowerTransformerEnd [^>]*>.*?</cim:PowerTransformerEnd>", eq, re.S)
        rx = [(float(re.search(r"End\.r>([^<]*)", b).group(1)), float(re.search(r"End\.x>([^<]*)", b).group(1)),
               float(re.search(r"End\.ratedU>([^<]*)", b).group(1))) for b in ends]
        u_hv, u_lv = max(r[2] for r in rx), min(r[2] for r in rx)
        self.ztr = sum(complex(r[0], r[1]) * (u_lv / r[2]) ** 2 for r in rx)
        self.v_src = u_lv * 1000.0                                       # nominal secondary voltage behind the transformer
        self.load_node = {}
        for rid, nm in re.findall(r'<cim:EnergyConsumer rdf:ID="([^"]+)">\s*<cim:IdentifiedObject.name>([^<]*)', eq):
            self.load_node[nm] = eq_nodes[rid][0]
        # root: node on the LV side of the transformer (the node shared with the line network)
        tr_nodes = set(sum((v for k, v in eq_nodes.items() if re.search(rf'<cim:PowerTransformer rdf:ID="{re.escape(k)}"', eq)), []))
        adj = {}
        for n, a, b, zl in edges:
            adj.setdefault(a, []).append((b, n, zl))
            adj.setdefault(b, []).append((a, n, zl))
        roots = [t for t in tr_nodes if t in adj]
        self.root = roots[0]
        self.order, self.parent = [self.root], {}
        seen = {self.root}
        for u in self.order:
            for v, n, zl in adj[u]:
                if v not in seen:
                    seen.add(v)
                    self.parent[v] = (u, n, zl)
                    self.order.append(v)

    def run(self, p_kw, q_kvar):
        """p_kw, q_kvar: {lod: [24 values]}. Returns per hour: trafo %, highest cable %, lowest and highest voltage (pu)."""
        out = {k: [] for k in ("trafo_pct", "line_pct", "vmin_pu", "vmax_pu")}
        busiest = []
        for t in range(24):
            V = {n: complex(self.v_src, 0) / np.sqrt(3) for n in self.order}
            vtx = V[self.root]
            for _ in range(30):
                I = {n: 0j for n in self.order}
                for lod, node in self.load_node.items():
                    if lod in p_kw:
                        I[node] += np.conj(complex(p_kw[lod][t], q_kvar[lod][t]) * 1000.0 / 3 / V[node])
                Il = {}
                for n in reversed(self.order[1:]):
                    u, name, _ = self.parent[n]
                    Il[name] = I[n]
                    I[u] += I[n]
                new = {self.root: vtx - I[self.root] * self.ztr}
                for n in self.order[1:]:
                    u, name, zl = self.parent[n]
                    new[n] = new[u] - Il[name] * zl
                done = max(abs(new[n] - V[n]) for n in self.order) < 1e-4
                V = new
                if done:
                    break
            s = 3 * vtx * np.conj(I[self.root]) / 1000.0
            pct = {k: 100 * abs(v) / self.rating[k] for k, v in Il.items()}
            vv = np.array([abs(V[n]) * np.sqrt(3) / LV_BASE_V for n in self.order])
            out["trafo_pct"].append(100 * abs(s) / self.trafo_kva)
            out["line_pct"].append(max(pct.values()))
            out["vmin_pu"].append(float(vv.min()))
            out["vmax_pu"].append(float(vv.max()))
            busiest.append(max(pct, key=pct.get))
        out["busiest_line"] = busiest
        return out


class DPsimFeeder(Feeder):
    """The same feeder solved by DPsim itself (pip package dpsim; SP domain, NRP solver, as TWIN-REV's DPsim service).
    Node voltages come from DPsim; line currents and the transformer flow follow from them."""

    def __init__(self, archive, trafo_kva, workdir, **kw):
        super().__init__(archive, trafo_kva, **kw)
        import dpsim
        self.dp = dpsim
        os.makedirs(workdir, exist_ok=True)
        zipfile.ZipFile(archive).extractall(workdir)
        self.files = sorted(os.path.join(workdir, f) for f in os.listdir(workdir) if f.endswith(".xml"))
        os.chdir(workdir)                                                # DPsim writes its logs to ./logs
        self.sys = dpsim.CIMReader("lv").loadCIM(50, self.files, dpsim.Domain.SP, dpsim.PhaseType.Single, dpsim.GeneratorType.PVNode)
        self.k = 0

    def run(self, p_kw, q_kvar):
        dp, s = self.dp, self.sys
        out = {k: [] for k in ("trafo_pct", "line_pct", "vmin_pu", "vmax_pu")}
        out["busiest_line"] = []
        for t in range(24):
            for lod in self.load_node:
                pv, qv = (p_kw[lod][t], q_kvar[lod][t]) if lod in p_kw else (0.0, 0.0)
                s.component(lod).set_parameters(pv * 1000.0, qv * 1000.0, LV_BASE_V)
            self.k += 1
            sim = dp.Simulation(f"r{self.k % 1000}")
            sim.set_system(s)
            sim.set_time_step(1)
            sim.set_final_time(1)
            sim.set_domain(dp.Domain.SP)
            sim.set_solver(dp.Solver.NRP)
            sim.do_init_from_nodes_and_terminals(False)
            sim.run()
            V = {n: complex(np.ravel(s.node(n).attr("v").get())[0]) for n in self.order}
            I = {n: 0j for n in self.order}
            for lod, node in self.load_node.items():
                if lod in p_kw:
                    I[node] += np.conj(complex(p_kw[lod][t], q_kvar[lod][t]) * 1000.0 / 3 / (V[node] / np.sqrt(3)))
            pct, top = {}, 0j
            for n in self.order[1:]:
                u, name, zl = self.parent[n]
                il = (V[u] - V[n]) / np.sqrt(3) / zl
                pct[name] = 100 * abs(il) / self.rating[name]
                if u == self.root:
                    top += il
            top += I[self.root]
            sb = 3 * (V[self.root] / np.sqrt(3) + top * self.ztr) * np.conj(top) / 1000.0     # at the primary side of the impedance
            vv = np.abs(np.array(list(V.values()))) / LV_BASE_V
            out["trafo_pct"].append(float(100 * abs(sb) / self.trafo_kva))
            out["line_pct"].append(float(max(pct.values())))
            out["vmin_pu"].append(float(vv.min()))
            out["vmax_pu"].append(float(vv.max()))
            out["busiest_line"].append(max(pct, key=pct.get))
        return out
