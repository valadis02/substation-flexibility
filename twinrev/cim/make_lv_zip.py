"""Usage: python3 make_lv_zip.py <cim-grid-data>/IEEE_EU_LV/IEEE_EU_LV_reduced cel3_lv.zip

Public IEEE European LV test feeder (NEPLAN CIM export, dpsim-simulator/cim-grid-data) packaged for the TWIN-REV DSO
pipeline as cell 3: loads PQ1..PQ55 renamed lod_01..lod_55 (dpsv matches profiles to DPsim names by prefix, so PQ1
would also catch PQ10..PQ19), SV saved as _SSH (NEPLAN CIM16 has no SSH)."""
import re, sys, zipfile, os
src, out = sys.argv[1], sys.argv[2]
name = "cel3_lv"
files = {f.split("_")[-1].split(".")[0]: os.path.join(src, f) for f in os.listdir(src) if f.endswith(".xml")}
eq = open(files["EQ"], encoding="utf-8").read()
def ren(m):
    return re.sub(r"(<cim:IdentifiedObject\.name>)PQ(\d+)(</cim:IdentifiedObject\.name>)",
                  lambda n: f"{n.group(1)}lod_{int(n.group(2)):02d}{n.group(3)}", m.group(0))
eq2, n = re.subn(r"<cim:EnergyConsumer [^>]*>.*?</cim:EnergyConsumer>", ren, eq, flags=re.S)
print("EnergyConsumer blocks:", n, "renamed:", len(re.findall(r">lod_\d\d<", eq2)))
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr(f"{name}_EQ.xml", eq2)
    z.write(files["TP"], f"{name}_TP.xml")
    z.write(files["SV"], f"{name}_SSH.xml")
print("wrote", out)
