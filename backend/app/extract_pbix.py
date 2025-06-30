# backend/app/extract_pbix.py
r"""
Extraction d’un .pbix avec pbi-tools (mode RAW).

• pbi-tools.exe --extract … -modelSerialization Raw
• On lit le JSON du modèle et on renvoie tables, mesures, relations, pages.
• Si aucun modèle → on renvoie quand même les pages (thin report).
"""
import subprocess, tempfile, json, shutil, uuid, os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

DEFAULT_PATH = r"C:\Users\lmoothery\AppData\Local\pbi-tools.exe"


class PBIToolsMissing(RuntimeError):
    ...


def _pbi_tools_path() -> str:
    exe = os.getenv("PBITOOLS_PATH", DEFAULT_PATH)
    if not Path(exe).is_file():
        raise PBIToolsMissing(f"pbi-tools introuvable : {exe}")
    return exe


# ------------------------------------------------------------------
def _find_model_file(tmp: Path) -> Path | None:
    model_dir = tmp / "Model"

    dbjson = model_dir / "database.json"
    if dbjson.is_file():
        return dbjson

    for f in model_dir.glob("DataModelSchema*"):
        if f.is_file():
            return f

    for pat in ("*.tmdl", "*.bim"):
        res = list(tmp.rglob(pat))
        if res:
            return res[0]
    return None


def _extract_pages(tmp: Path):
    pages = []
    for lf in (tmp / "Report" / "Layout").glob("*.json"):
        lay = json.load(open(lf, encoding="utf-8", errors="ignore"))
        pages.append(
            {
                "name": lay.get("name", lf.stem),
                "visuals": [
                    {
                        "type": v.get("visualType"),
                        "fields": v.get("config", {}).get("dataRoles", []),
                    }
                    for v in lay.get("visualContainers", [])
                ],
            }
        )
    return pages


# ------------------------------------------------------------------
def extract_spec(pbix_path: str) -> dict:
    exe = _pbi_tools_path()
    tmp = Path(tempfile.mkdtemp(prefix="pbix_extract_"))

    try:
        proc = subprocess.run(
            [
                exe, "extract", pbix_path,
                "-extractFolder", str(tmp),
                "-mode", "Auto",
                "-modelSerialization", "Raw",
            ],
            capture_output=True, text=True
        )
        if proc.returncode != 0:
            raise RuntimeError(f"pbi-tools erreur :\n{proc.stderr.strip()}")

        pages = _extract_pages(tmp)

        model_path = _find_model_file(tmp)
        if model_path is None:
            # thin report
            return {
                "id": str(uuid.uuid4()),
                "tables": [],
                "measures": [],
                "pages": pages,
                "relations": [],
                "note": "Thin report – modèle hébergé dans le Service Power BI",
            }

        with open(model_path, encoding="utf-8-sig", errors="ignore") as f:
            model = json.load(f)

        tables = [t["name"] for t in model["model"]["tables"]]
        measures = [
            {"table": t["name"], "name": m["name"], "expr": m["expression"]}
            for t in model["model"]["tables"]
            for m in t.get("measures", [])
        ]
        relations = model["model"].get("relationships", [])

        return {
            "id": str(uuid.uuid4()),
            "tables": tables,
            "measures": measures,
            "pages": pages,
            "relations": relations,
        }

    finally:
        shutil.rmtree(tmp, ignore_errors=True)
