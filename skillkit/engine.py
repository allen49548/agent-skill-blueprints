#!/usr/bin/env python3
"""
Self-contained runtime for a capability skill.

Standard library only. No vendor SDKs, no third-party packages, no project-specific
vocabulary. Every deployment difference lives in config.json, produced by `setup`.

Commands:
  demo     Full pipeline on bundled sample data, zero configuration, zero credentials.
  setup    Interactive onboarding wizard; writes config.json.
  doctor   Validate config, adapters, permissions and dry-run state.
  run      Run the pipeline (dry-run by default).
  info     Show the profile and current configuration status.
  install  Install this skill into the local skills directory (--apply to write).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import os
import re
import shutil
import sys
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

PACKAGE_DIR = Path(__file__).resolve().parent
# When loaded from the repository, SKILLKIT_HOME points at the calling skill
# directory. In a built self-contained package the engine sits in that same
# directory, so the default falls back to PACKAGE_DIR. Both paths are correct.
HERE = Path(os.environ.get("SKILLKIT_HOME") or PACKAGE_DIR).resolve()
PROFILE_FILE = HERE / "profile.json"
EXAMPLE_CONFIG = HERE / "config.example.json"
CONFIG_FILE = HERE / "config.json"
DEMO_INPUT = HERE / "examples" / "demo_input.json"
INSTALL_ROOT = Path.home() / ".workbuddy" / "skills"

PLACEHOLDER = re.compile(r"^<[A-Z0-9_]+>$")
TEMPLATES = ["minimal", "compact_professional", "alert_only", "full_audit"]
ADAPTERS = {
    "input": ["local_folder", "json_file", "webhook"],
    "output": ["csv", "json", "xlsx", "artifact_export", "none"],
    "notify": ["stdout", "webhook", "none"],
}

LOG = logging.getLogger("skillkit")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

PRESET_CRONS = {
    "daily_0900": "0 9 * * *",
    "weekday_0900": "0 9 * * 1-5",
    "daily_three_rounds": "0 22,23,0 * * *",
    "monthly_1_4": "0 9 1-4 * *",
    "monthly_10": "0 9 10 * *",
    "hourly": "0 * * * *",
}


# --------------------------------------------------------------------------- helpers

def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def say(msg: str = "") -> None:
    print(msg, flush=True)


def die(msg: str) -> None:
    print("ERROR: " + msg, file=sys.stderr)
    raise SystemExit(2)


def load_json(path: Path, default=None):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        die(f"cannot read {path.name}: {exc}")


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def resolve_ref(cfg, ref: str):
    cur = cfg
    for part in ref.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None, False
        cur = cur[part]
    return cur, True


def fill_placeholders(obj, key: str = ""):
    """Replace template placeholders with safe, non-secret runtime defaults."""
    if isinstance(obj, dict):
        return {k: fill_placeholders(v, k) for k, v in obj.items()}
    if isinstance(obj, list):
        return [fill_placeholders(v, key) for v in obj]
    if isinstance(obj, str) and PLACEHOLDER.match(obj):
        k = key.lower()
        if "timezone" in k:
            return "UTC"
        if "sheet" in k:
            return "detail"
        if "template" in k:
            return "./templates/default.xlsx"
        if "dir" in k or "root" in k or "path" in k:
            return "./out"
        if "cron" in k:
            return "0 9 * * *"
        return "unset"
    return obj


# --------------------------------------------------------------------------- wizard

def ask(question: str, options: list[str], default: int, auto: bool) -> int:
    say("")
    say(question)
    for i, opt in enumerate(options, 1):
        mark = " (default)" if i == default else ""
        say(f"  [{i}] {opt}{mark}")
    if auto:
        say(f"  -> {default} (non-interactive)")
        return default
    while True:
        raw = input("  choose number: ").strip()
        if not raw:
            return default
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return int(raw)
        say("  please enter a number from the list")


def ask_text(question: str, default: str, auto: bool) -> str:
    if auto:
        say(f"  {question}: {default} (non-interactive)")
        return default
    raw = input(f"  {question} [{default}]: ").strip()
    return raw or default


def discover_groups(platform: str) -> list[dict]:
    """List every group on the selected platform.

    Platform connectors are intentionally not bundled. The built-in discovery
    returns the local drop folders that act as groups for a zero-credential run.
    A project can register a platform adapter without changing this runtime.
    """
    base = HERE / "inbox"
    if not base.exists():
        return [{"id": "local-default", "name": "local default inbox", "kind": "local_folder"}]
    found = []
    for p in sorted(base.iterdir()):
        if p.is_dir():
            found.append({"id": p.name, "name": p.name, "kind": "local_folder"})
    return found or [{"id": "local-default", "name": "local default inbox", "kind": "local_folder"}]


def cmd_setup(args) -> int:
    profile = load_json(PROFILE_FILE, {})
    cfg = fill_placeholders(load_json(EXAMPLE_CONFIG, {}))
    cfg.setdefault("wizard", {})
    cfg.setdefault("engine", {})
    w = cfg["wizard"]
    e = cfg["engine"]
    auto = args.yes

    say("=== Onboarding wizard ===")
    say("Nine steps. Every answer is written to config.json; nothing is read or sent yet.")

    # 0 preset
    preset = ask("Step 0/8  Quick start preset or fully custom?",
                 ["Quick start (recommended defaults)", "Custom, ask me everything"], 1, auto)
    use_preset = preset == 1
    w["preset"] = "daily_intake" if use_preset else "custom"
    w["mode"] = "guided"

    # 1 platform
    platform = ask("Step 1/8  Input / output platform?",
                   ["feishu", "wecom", "local_folder (no credentials, works immediately)"], 3, auto)
    platform_name = ["feishu", "wecom", "local_folder"][platform - 1]
    w.setdefault("connector", {})["platform"] = platform_name
    w["connector"]["connection_status"] = "connected" if platform_name == "local_folder" else "adapter_required"
    say("  NOTE: feishu / wecom are config options only. Group listing for a real platform")
    say("        requires a project-supplied adapter; local_folder works out of the box.")

    # 2 groups
    groups = discover_groups(platform_name)
    say("")
    say("Step 2/8  Available groups (exact ids, multi-select):")
    for i, g in enumerate(groups, 1):
        say(f"  [{i}] {g['name']}  id={g['id']}")
    if auto:
        chosen = [groups[0]["id"]]
        say(f"  -> {chosen} (non-interactive)")
    else:
        raw = input("  choose numbers separated by commas [1]: ").strip() or "1"
        chosen = []
        for token in raw.split(","):
            token = token.strip()
            if token.isdigit() and 1 <= int(token) <= len(groups):
                chosen.append(groups[int(token) - 1]["id"])
        chosen = chosen or [groups[0]["id"]]
    w["connector"]["selected_group_ids"] = chosen
    w["connector"]["group_isolation"] = "per_group"
    w["connector"]["match_by"] = "exact_id"
    w["connector"]["group_discovery"] = "list_all"
    w["connector"]["group_selection"] = "multi"

    # 3 message sources
    src_opts = ["image", "text", "link", "template_message", "card", "file",
                "feed", "api", "structured_record"]
    say("")
    say("Step 3/8  Message source types (multi-select): " + ", ".join(src_opts))
    default_src = profile.get("defaults", {}).get("message_sources", ["structured_record", "file"])
    if auto:
        sources = default_src
        say(f"  -> {sources} (non-interactive)")
    else:
        raw = input(f"  comma-separated names [{','.join(default_src)}]: ").strip()
        sources = [s.strip() for s in raw.split(",") if s.strip() in src_opts] if raw else default_src
    w["message_sources"] = sources

    # 4 output
    profile_adapter = profile.get("defaults", {}).get("output_adapter", "xlsx")
    profile_write_mode = profile.get("defaults", {}).get("write_mode", "new_sheet")
    preset_default = (4 if profile_adapter == "none" else
                      5 if profile_adapter in ("csv", "artifact_export") else
                      1 if profile_write_mode == "existing_cells" else 2)
    out_choice = ask("Step 4/8  Output target?",
                     ["Map an existing report, write into existing cells",
                      "Map an existing report, add a new sheet",
                      "Create a new report (requires explicit authorization)",
                      "Message only, no report",
                      "Artifact export (csv / json)"], preset_default if use_preset else 5, auto)
    mode_map = {1: ("existing_report", "existing_cells", "xlsx"),
                2: ("existing_report", "new_sheet", "xlsx"),
                3: ("new_report", "new_sheet", "xlsx"),
                4: ("message_only", "new_sheet", "none"),
                5: ("artifact_export", "new_sheet", "csv")}
    out_mode, write_mode, out_adapter = mode_map[out_choice]
    w.setdefault("output", {})["mode"] = out_mode
    w["output"]["existing_report"] = {"write_mode": write_mode,
                                      "sheet": "detail",
                                      "create_workbook_if_missing": False}
    new_report = {"enabled": out_mode == "new_report",
                  "requires_explicit_authorization": True,
                  "authorized_by": "onboarding-wizard" if out_mode == "new_report" else None,
                  "template": "./templates/default.xlsx",
                  "target_dir": "./out",
                  "backup_required": True,
                  "never_overwrite_existing": True}
    w["output"]["new_report"] = new_report
    if out_mode == "new_report" and not auto:
        ok = input("  You selected NEW REPORT creation. Type 'yes' to authorize: ").strip().lower()
        if ok != "yes":
            say("  Authorization not given. Falling back to an existing report with a new sheet.")
            w["output"]["mode"] = "existing_report"
            w["output"]["new_report"]["enabled"] = False
            w["output"]["new_report"]["authorized_by"] = None
            out_mode, out_adapter = "existing_report", "xlsx"

    # 5 notifications
    say("")
    say("Step 5/8  Notification templates: " + ", ".join(TEMPLATES))
    default_tpl = profile.get("defaults", {}).get("templates", ["minimal", "compact_professional"])
    if auto:
        chosen_tpl = default_tpl
        say(f"  -> {chosen_tpl} (non-interactive)")
    else:
        raw = input(f"  comma-separated names [{','.join(default_tpl)}]: ").strip()
        chosen_tpl = [s.strip() for s in raw.split(",") if s.strip() in TEMPLATES] if raw else default_tpl
    w.setdefault("notifications", {})["selected_templates"] = chosen_tpl
    w["notifications"]["template_catalog"] = TEMPLATES
    w["notifications"]["channel_binding"] = {
        "public_channel": "minimal" if "minimal" in chosen_tpl else None,
        "operator_channel": "compact_professional" if "compact_professional" in chosen_tpl else None,
    }
    w["notifications"]["delivery_whitelist"] = []
    e["notify"] = {"adapter": "stdout", "webhook_url": ""}

    # 6 schedule
    preset_names = list(PRESET_CRONS) + ["custom"]
    sched = ask("Step 6/8  When should it run?",
                preset_names + ["do not schedule yet"], 1 if use_preset else len(preset_names) + 1, auto)
    if sched <= len(preset_names):
        pname = preset_names[sched - 1]
        w.setdefault("schedule", {})["preset"] = pname
        w["schedule"]["cron"] = PRESET_CRONS.get(pname, "0 9 * * *")
        w["schedule"]["user_confirmed"] = True
    else:
        w.setdefault("schedule", {})["preset"] = "custom"
        w["schedule"]["cron"] = ""
        w["schedule"]["user_confirmed"] = False
    w["schedule"]["timezone"] = ask_text("  IANA timezone", "UTC", auto)
    w["schedule"]["custom_cron_allowed"] = True

    # 7 review
    w.setdefault("confirmation", {})
    w["confirmation"].update({"review_all_choices": True,
                              "dry_run": True,
                              "trial_run_writes_disabled": True})
    say("")
    say("Step 7/8  Review your choices")
    say(json.dumps({
        "platform": platform_name,
        "groups": chosen,
        "message_sources": sources,
        "output_mode": w["output"]["mode"],
        "write_mode": write_mode,
        "templates": chosen_tpl,
        "schedule": w["schedule"],
        "dry_run": True,
    }, indent=2, ensure_ascii=False))
    if auto:
        w["confirmation"]["user_confirmed"] = True
    else:
        ok = input("  Confirm and write config.json? [Y/n]: ").strip().lower()
        w["confirmation"]["user_confirmed"] = ok in ("", "y", "yes")
        if not w["confirmation"]["user_confirmed"]:
            say("  Aborted, nothing was written.")
            return 1

    # engine settings that make the runtime work with zero credentials
    inbox = HERE / "inbox"
    inbox.mkdir(exist_ok=True)
    if not any(inbox.glob("*.json")) and DEMO_INPUT.exists():
        shutil.copy2(DEMO_INPUT, inbox / "sample.json")
        say("  Created inbox/sample.json from bundled demo data so your first run has input.")
    e["input"] = {"adapter": "local_folder", "path": "./inbox"}
    e["output"] = {"adapter": out_adapter,
                   "mode": w["output"]["mode"],
                   "write_mode": write_mode,
                   "path": "./out/report.xlsx",
                   "sheet": "detail",
                   "anchor": "A1",
                   "csv_path": "./out/report.csv",
                   "json_path": "./out/report.json"}
    e["dedupe"] = {"key_fields": ["business_key"], "ledger_path": "./state/ledger.json"}
    e["timezone"] = w["schedule"]["timezone"]

    save_json(CONFIG_FILE, cfg)
    say("")
    say("Step 8/8  Trial run")
    say(f"  Wrote {CONFIG_FILE.name}. Run `python3 run.py doctor`, then `python3 run.py run`.")
    say("  Nothing was read, written or sent during setup.")
    return 0


# --------------------------------------------------------------------------- adapters

def read_records(engine_cfg: dict) -> tuple[list[dict], list[str]]:
    """Read raw records from the configured input adapter."""
    ic = engine_cfg.get("input", {})
    adapter = ic.get("adapter", "local_folder")
    notes: list[str] = []
    raw: list[dict] = []

    if adapter == "local_folder":
        root = (HERE / ic.get("path", "./inbox")).resolve()
        if not root.exists():
            return [], [f"input folder not found: {root.name}"]
        files = sorted([p for p in root.rglob("*")
                        if p.is_file() and p.suffix.lower() in (".json", ".jsonl")])
        if not files:
            notes.append(f"no .json/.jsonl files in {root.name}")
        for p in files:
            if p.suffix.lower() == ".jsonl":
                for line in p.read_text(encoding="utf-8").splitlines():
                    if line.strip():
                        try:
                            raw.append(json.loads(line))
                        except json.JSONDecodeError:
                            notes.append(f"skipped invalid line in {p.name}")
            else:
                data = load_json(p, None)
                if isinstance(data, list):
                    raw.extend([x for x in data if isinstance(x, dict)])
                elif isinstance(data, dict):
                    raw.append(data)
    elif adapter == "json_file":
        path = (HERE / ic.get("path", "./inbox/records.json")).resolve()
        data = load_json(path, None)
        raw = data if isinstance(data, list) else ([data] if isinstance(data, dict) else [])
    elif adapter == "webhook":
        url = ic.get("url", "")
        if not url or PLACEHOLDER.match(url):
            notes.append("webhook input needs a url")
        else:
            try:
                with urllib.request.urlopen(url, timeout=10) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                raw = data if isinstance(data, list) else [data]
            except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
                notes.append(f"webhook input failed: {exc}")
    else:
        notes.append(f"input adapter not registered: {adapter}")
    return raw, notes


def normalize(raw: list[dict]) -> list[dict]:
    out = []
    for r in raw:
        rec = {
            "id": str(r.get("id") or r.get("message_id") or ""),
            "entity": str(r.get("entity") or "unresolved"),
            "group": str(r.get("group") or "default"),
            "value": r.get("value", 0),
            "date": str(r.get("date") or ""),
            "business_key": str(r.get("business_key") or ""),
            "source_type": str(r.get("type") or r.get("source_type") or "structured_record"),
            "note": str(r.get("note") or ""),
        }
        try:
            rec["value"] = float(rec["value"])
        except (TypeError, ValueError):
            rec["value"] = 0.0
        if not rec["id"]:
            rec["id"] = hashlib.sha256(
                json.dumps(r, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:12]
        if not rec["business_key"]:
            rec["business_key"] = "|".join(
                [rec["group"], rec["entity"], rec["date"], str(rec["value"]), rec["id"]])
        rec["dedupe_key"] = rec["group"] + "|" + rec["business_key"]
        out.append(rec)
    return out


def dedupe(records: list[dict], engine_cfg: dict, out_dir: Path | None) -> tuple[list[dict], list[dict]]:
    dc = engine_cfg.get("dedupe", {})
    ledger_path = (HERE / dc.get("ledger_path", "./state/ledger.json")).resolve() if out_dir else None
    ledger = load_json(ledger_path, {}) if ledger_path else {}
    seen = set(ledger.keys())
    kept, dupes = [], []
    for r in records:
        if r["dedupe_key"] in seen:
            dupes.append({**r, "reason": "business_key",
                          "original_registered_at": ledger.get(r["dedupe_key"], now_iso())})
        else:
            kept.append(r)
            seen.add(r["dedupe_key"])
    if ledger_path:
        save_json(ledger_path, {**ledger, **{r["dedupe_key"]: now_iso() for r in kept}})
    return kept, dupes


# --------------------------------------------------------------------------- xlsx (stdlib)

def _col_letters(n: int) -> str:
    s = ""
    while n > 0:
        n, rem = divmod(n - 1, 26)
        s = chr(65 + rem) + s
    return s


def _sheet_xml(rows: list[list]) -> str:
    parts = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
             '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>']
    for i, row in enumerate(rows, 1):
        parts.append(f'<row r="{i}">')
        for j, val in enumerate(row, 1):
            ref = f"{_col_letters(j)}{i}"
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                parts.append(f'<c r="{ref}"><v>{val}</v></c>')
            else:
                parts.append(f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">'
                             f'{escape(str(val))}</t></is></c>')
        parts.append("</row>")
    parts.append("</sheetData></worksheet>")
    return "".join(parts)


def _new_workbook(sheets: dict[str, list[list]]) -> bytes:
    ct = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
          '<Default Extension="xml" ContentType="application/xml"/>',
          '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>']
    rels = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">']
    wb = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
          '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
          'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>']
    buf = __import__("io").BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for idx, (name, rows) in enumerate(sheets.items(), 1):
            ct.append(f'<Override PartName="/xl/worksheets/sheet{idx}.xml" '
                      'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>')
            rels.append(f'<Relationship Id="rId{idx}" '
                        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
                        f'Target="worksheets/sheet{idx}.xml"/>')
            safe = re.sub(r"[\\/*?:\[\]]", "_", name)[:31]
            wb.append(f'<sheet name="{escape(safe)}" sheetId="{idx}" r:id="rId{idx}"/>')
            z.writestr(f"xl/worksheets/sheet{idx}.xml", _sheet_xml(rows))
        ct.append("</Types>")
        rels.append('<Relationship Id="rIdApp" '
                    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" '
                    'Target="docProps/app.xml"/>')
        rels.append("</Relationships>")
        wb.append('</sheets><calcPr calcId="0" fullCalcOnLoad="1"/></workbook>')
        z.writestr("[Content_Types].xml", "".join(ct))
        z.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" '
                   'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
                   'Target="xl/workbook.xml"/></Relationships>')
        z.writestr("xl/workbook.xml", "".join(wb))
        z.writestr("xl/_rels/workbook.xml.rels", "".join(rels))
        z.writestr("docProps/app.xml", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
                   '<Application>skillkit</Application></Properties>')
    return buf.getvalue()


def _write_zip(path: Path, parts: dict[str, bytes]) -> None:
    tmp = path.with_suffix(".tmp.xlsx")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in parts.items():
            z.writestr(name, data)
    tmp.replace(path)


def _append_sheet(existing: Path, sheet_name: str, rows: list[list], backup_dir: Path | None) -> str:
    """Add one sheet, or replace its content if the named sheet already exists.

    Repeatable by construction: a rerun never creates a second sheet with the
    same name and never duplicates the relationship or content-type entry.
    """
    if backup_dir:
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        shutil.copy2(existing, backup_dir / (existing.name + "." + stamp + ".bak"))
    with zipfile.ZipFile(existing, "r") as z:
        parts = {i.filename: z.read(i.filename) for i in z.infolist()}
    wb = parts.get("xl/workbook.xml", b"").decode("utf-8")
    rels = parts.get("xl/_rels/workbook.xml.rels", b"").decode("utf-8")
    ct = parts.get("[Content_Types].xml", b"").decode("utf-8")
    safe = re.sub(r"[\\/*?:\[\]]", "_", sheet_name)[:31]

    # Idempotent path: the named sheet already exists, so only replace its part.
    for tag in re.findall(r"<sheet\b[^>]*/>", wb):
        nm = re.search(r'\bname="([^"]*)"', tag)
        rid_m = re.search(r'\br:id="(rId\d+)"', tag)
        if not (nm and rid_m and nm.group(1) == safe):
            continue
        rid = rid_m.group(1)
        rm = re.search(r'<Relationship\b[^>]*\bId="' + re.escape(rid)
                       + r'"[^>]*\bTarget="([^"]+)"', rels)
        if not rm:
            continue
        target = rm.group(1).lstrip("/")
        part = target if target.startswith("xl/") else "xl/" + target
        if part in parts:
            parts[part] = _sheet_xml(rows).encode("utf-8")
            _write_zip(existing, parts)
            LOG.info("sheet replaced in place: %s", part)
            return part

    # First run: add a new worksheet part with a fresh rId and sheetId.
    names = [n for n in parts if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n)]
    idx = max([int(re.search(r"(\d+)", n).group(1)) for n in names], default=0) + 1
    used = set(re.findall(r'Id="(rId\d+)"', rels))
    rid = next(f"rId{i}" for i in range(1, 999) if f"rId{i}" not in used)
    sheet_id = max([int(x) for x in re.findall(r'sheetId="(\d+)"', wb)], default=0) + 1
    wb = wb.replace("</sheets>", f'<sheet name="{escape(safe)}" sheetId="{sheet_id}" r:id="{rid}"/></sheets>')
    rels = rels.replace("</Relationships>",
                        f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/'
                        f'officeDocument/2006/relationships/worksheet" '
                        f'Target="worksheets/sheet{idx}.xml"/></Relationships>')
    ct = ct.replace("</Types>", f'<Override PartName="/xl/worksheets/sheet{idx}.xml" '
                    'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>')
    parts["xl/workbook.xml"] = wb.encode("utf-8")
    parts["xl/_rels/workbook.xml.rels"] = rels.encode("utf-8")
    parts["[Content_Types].xml"] = ct.encode("utf-8")
    parts[f"xl/worksheets/sheet{idx}.xml"] = _sheet_xml(rows).encode("utf-8")
    _write_zip(existing, parts)
    LOG.info("sheet added: sheet%d.xml", idx)
    return f"sheet{idx}.xml"


def _update_cells(existing: Path, rows: list[list], backup_dir: Path | None) -> int:
    """Surgically replace numeric cell values in the first worksheet by anchor position."""
    if backup_dir:
        backup_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(existing, backup_dir / (existing.name + "." + datetime.now().strftime("%Y%m%d%H%M%S") + ".bak"))
    with zipfile.ZipFile(existing, "r") as z:
        parts = {i.filename: z.read(i.filename) for i in z.infolist()}
    target = next((n for n in sorted(parts) if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n)), None)
    if not target:
        return 0
    xml = parts[target].decode("utf-8")
    changed = 0
    for i, row in enumerate(rows, 1):
        for j, val in enumerate(row, 1):
            if not isinstance(val, (int, float)) or isinstance(val, bool):
                continue
            ref = f"{_col_letters(j)}{i}"
            pattern = re.compile(r'(<c r="' + ref + r'"[^>]*>)(.*?)(</c>)', re.S)
            m = pattern.search(xml)
            if not m:
                continue
            inner = re.sub(r"<v>.*?</v>", f"<v>{val}</v>", m.group(2), flags=re.S)
            if "<v>" not in inner:
                inner += f"<v>{val}</v>"
            xml = xml[:m.start()] + m.group(1) + inner + m.group(3) + xml[m.end():]
            changed += 1
    parts[target] = xml.encode("utf-8")
    _write_zip(existing, parts)
    return changed


# --------------------------------------------------------------------------- output

def write_outputs(records: list[dict], engine_cfg: dict, out_dir: Path, dry_run: bool,
                  wizard: dict) -> list[str]:
    oc = engine_cfg.get("output", {})
    adapter = oc.get("adapter", "csv")
    mode = oc.get("mode", "artifact_export")
    write_mode = oc.get("write_mode", "new_sheet")
    sheet = oc.get("sheet", "detail")
    notes: list[str] = []
    rows = [["id", "entity", "group", "value", "date", "business_key", "source_type"]] + [
        [r["id"], r["entity"], r["group"], r["value"], r["date"], r["business_key"], r["source_type"]]
        for r in records]

    out_dir.mkdir(parents=True, exist_ok=True)
    if dry_run:
        (out_dir / "change-log.md").write_text(
            "# Change log (dry run)\n\n"
            f"- records: {len(records)}\n- output adapter: {adapter}\n"
            f"- output mode: {mode} / {write_mode}\n"
            f"- rows that would be written: {len(records)}\n"
            + "\n".join(f"- {r['id']} {r['entity']} {r['value']} {r['date']}" for r in records)
            + "\n", encoding="utf-8")
        return ["dry-run: wrote change-log.md only"]

    out_dir.mkdir(parents=True, exist_ok=True)
    if adapter in ("csv", "artifact_export"):
        with (out_dir / "report.csv").open("w", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerows(rows)
        notes.append("report.csv")
    if adapter in ("json", "artifact_export"):
        save_json(out_dir / "report.json", records)
        notes.append("report.json")
    if adapter == "xlsx":
        path = (HERE / oc.get("path", "./out/report.xlsx")).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        new_report = wizard.get("output", {}).get("new_report", {})
        if mode == "new_report":
            if not new_report.get("enabled") or not new_report.get("authorized_by"):
                notes.append("new_report blocked: explicit authorization missing")
            elif path.exists() and new_report.get("never_overwrite_existing", True):
                notes.append("new_report blocked: target exists and no-overwrite is on")
            else:
                path.write_bytes(_new_workbook({sheet: rows}))
                notes.append(f"{path.name} created")
        elif not path.exists():
            notes.append("xlsx target missing; no workbook created (record_without_write)")
            (out_dir / "preview.xlsx").write_bytes(_new_workbook({sheet: rows}))
            with (out_dir / "report.csv").open("w", newline="", encoding="utf-8") as fh:
                csv.writer(fh).writerows(rows)
            save_json(out_dir / "report.json", records)
            notes.append("preview.xlsx + report.csv / report.json written to run dir (target untouched)")
        elif write_mode == "new_sheet":
            added = _append_sheet(path, sheet, rows, out_dir / "backups")
            notes.append(f"{path.name}: added {added}")
        elif write_mode == "existing_cells":
            n = _update_cells(path, rows, out_dir / "backups")
            notes.append(f"{path.name}: updated {n} cells")
        else:
            notes.append(f"unknown write_mode: {write_mode}")
        # verify untouched parts still readable
        try:
            with zipfile.ZipFile(path, "r") as z:
                if z.testzip() is not None:
                    notes.append("xlsx verification failed")
        except (OSError, zipfile.BadZipFile):
            notes.append("xlsx verification skipped: target not created")
    return notes


# --------------------------------------------------------------------------- notifications

def render_template(name: str, records: list[dict], dupes: list[dict], meta: dict) -> str:
    total = sum(r["value"] for r in records)
    anomalies = [r for r in records if r["entity"] == "unresolved" or r["source_type"] == "unsupported"]
    if name == "minimal":
        lines = [f"{r['entity']}: {r['value']} ({r['date']})" for r in records]
        lines.append(f"Total: {total}")
        return "\n".join(lines)
    if name == "compact_professional":
        lines = [f"Run {meta.get('run_id', '')} | records {len(records)} | total {total}"]
        groups: dict[str, list[dict]] = {}
        for r in records:
            groups.setdefault(r["group"], []).append(r)
        for g, items in sorted(groups.items()):
            lines.append(f"[{g}] {len(items)} records, {sum(x['value'] for x in items)}")
            for r in items:
                lines.append(f"  {r['entity']} {r['value']} {r['date']}")
        if dupes:
            lines.append(f"Duplicates skipped: {len(dupes)}")
            for d in dupes:
                lines.append(f"  {d['id']} original {d['original_registered_at']} (no value added)")
        if anomalies:
            lines.append(f"Anomalies: {len(anomalies)}")
        lines.append(f"Artifacts: {meta.get('out_dir', '')}")
        return "\n".join(lines)
    if name == "alert_only":
        if not anomalies and not dupes and not meta.get("errors"):
            return ""
        lines = [f"ALERT run {meta.get('run_id', '')}"]
        lines += [f"anomaly: {r['id']} {r['entity']}" for r in anomalies]
        lines += [f"duplicate: {d['id']}" for d in dupes]
        lines += [f"error: {e}" for e in meta.get("errors", [])]
        return "\n".join(lines)
    if name == "full_audit":
        lines = [f"FULL AUDIT run {meta.get('run_id', '')}", f"generated: {now_iso()}"]
        for r in records:
            lines.append(json.dumps(r, ensure_ascii=False, sort_keys=True))
        lines.append(f"duplicates: {json.dumps(dupes, ensure_ascii=False)}")
        lines.append(f"backup dir: {meta.get('out_dir', '')}/backups")
        lines.append(f"delivery receipts: stdout only (dry_run={meta.get('dry_run')})")
        lines.append(f"idempotency key: {meta.get('run_id', '')}:{len(records)}")
        return "\n".join(lines)
    return f"unknown template: {name}"


def send_notifications(templates: list[str], records: list[dict], dupes: list[dict],
                       engine_cfg: dict, out_dir: Path, meta: dict, dry_run: bool) -> list[str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    adapter = engine_cfg.get("notify", {}).get("adapter", "stdout")
    url = engine_cfg.get("notify", {}).get("webhook_url", "")
    results = []
    for name in templates:
        text = render_template(name, records, dupes, meta)
        (out_dir / f"notification_{name}.txt").write_text(text + "\n", encoding="utf-8")
        results.append(f"{name}: rendered")
        if adapter == "stdout" and text:
            say(f"--- notification/{name} ---")
            say(text)
        if adapter == "webhook" and url and not dry_run and text:
            try:
                req = urllib.request.Request(url, data=json.dumps(
                    {"template": name, "text": text}).encode("utf-8"),
                    headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(req, timeout=10) as resp:
                    results.append(f"{name}: sent ({resp.status})")
            except (OSError, urllib.error.URLError) as exc:
                results.append(f"{name}: FAILED {exc}")
    return results


# --------------------------------------------------------------------------- pipeline

def run_pipeline(cfg: dict, profile: dict, out_dir: Path, dry_run: bool,
                 input_override: Path | None = None) -> dict:
    e = cfg.get("engine", {})
    wizard = cfg.get("wizard", {})
    if input_override is not None:
        e = {**e, "input": {"adapter": "local_folder", "path": str(input_override)}}
    raw, errors = read_records(e)
    records = normalize(raw)
    kept, dupes = dedupe(records, e, None if dry_run else out_dir)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    meta = {"run_id": run_id, "out_dir": str(out_dir), "dry_run": dry_run, "errors": errors}
    written = write_outputs(kept, e, out_dir, dry_run, wizard)
    templates = wizard.get("notifications", {}).get("selected_templates", ["minimal"])
    notices = send_notifications(templates, kept, dupes, e, out_dir, meta, dry_run)
    report = {
        "run_id": run_id,
        "generated_at": now_iso(),
        "profile": profile.get("slug", "unknown"),
        "dry_run": dry_run,
        "read": len(raw),
        "normalized": len(records),
        "kept": len(kept),
        "duplicates_skipped": len(dupes),
        "errors": errors,
        "writes": written,
        "notifications": notices,
        "templates": templates,
        "records": kept,
        "duplicates": dupes,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    save_json(out_dir / "run.json", report)
    events = [
        {"ts": now_iso(), "level": "INFO", "event": "run_complete",
         "profile": report["profile"], "run_id": run_id, "read": len(raw),
         "kept": len(kept), "duplicates": len(dupes), "dry_run": dry_run},
        {"ts": now_iso(), "level": "INFO", "event": "writes", "detail": written},
        {"ts": now_iso(), "level": "INFO", "event": "notifications", "detail": notices},
    ] + [{"ts": now_iso(), "level": "WARNING", "event": "input_note", "detail": x} for x in errors]
    (out_dir / "run.log").write_text(
        "\n".join(json.dumps(ev, ensure_ascii=False) for ev in events) + "\n",
        encoding="utf-8")
    return report


def print_report(r: dict) -> None:
    say("")
    say("=== Run summary ===")
    say(f"  profile            : {r['profile']}")
    say(f"  records read       : {r['read']}")
    say(f"  kept / duplicates  : {r['kept']} / {r['duplicates_skipped']}")
    say(f"  dry run            : {r['dry_run']}")
    say(f"  writes             : {', '.join(r['writes']) or 'none'}")
    say(f"  notifications      : {', '.join(r['notifications']) or 'none'}")
    for err in r["errors"]:
        say(f"  NOTE: {err}")
    say("")


# --------------------------------------------------------------------------- commands

def demo_config(profile: dict) -> dict:
    defaults = profile.get("defaults", {})
    adapter = defaults.get("output_adapter", "xlsx")
    if adapter == "none":
        adapter = "artifact_export"
    mode = "new_report" if adapter == "xlsx" else "artifact_export"
    return {
        "wizard": {
            "preset": "daily_intake",
            "notifications": {"selected_templates": list(TEMPLATES),
                              "template_catalog": list(TEMPLATES)},
            "output": {"mode": mode, "new_report": {
                "enabled": mode == "new_report", "authorized_by": "demo",
                "never_overwrite_existing": True, "backup_required": True}},
            "confirmation": {"dry_run": False, "user_confirmed": True},
            "schedule": {"preset": "daily_0900", "cron": PRESET_CRONS["daily_0900"],
                         "timezone": "UTC", "user_confirmed": True},
        },
        "engine": {
            "input": {"adapter": "local_folder", "path": str(DEMO_INPUT.parent)},
            "output": {"adapter": adapter, "mode": mode,
                       "write_mode": defaults.get("write_mode", "new_sheet"),
                       "path": "./demo-out/report.xlsx", "sheet": "detail"},
            "notify": {"adapter": "stdout", "webhook_url": ""},
            "dedupe": {"key_fields": ["business_key"], "ledger_path": "./state/ledger.json"},
            "timezone": defaults.get("timezone", "UTC"),
        },
    }


def cmd_demo(args) -> int:
    profile = load_json(PROFILE_FILE, {})
    if not DEMO_INPUT.exists():
        die("bundled demo data is missing: examples/demo_input.json")
    out_dir = HERE / "demo-out" / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    cfg = demo_config(profile)
    out_dir.mkdir(parents=True, exist_ok=True)
    cfg["engine"]["output"]["path"] = str(out_dir / "report.xlsx")
    cfg["engine"]["dedupe"]["ledger_path"] = str(out_dir / "ledger.json")
    say("=== Demo: zero configuration, zero credentials ===")
    say("Bundled sample data -> normalize -> dedupe -> xlsx + csv + json -> 4 templates -> run log")
    r = run_pipeline(cfg, profile, out_dir, dry_run=False, input_override=DEMO_INPUT.parent)
    if cfg["engine"]["output"]["adapter"] == "xlsx":
        # prove the csv/json adapters too
        csv_cfg = {**cfg, "engine": {**cfg["engine"],
                   "output": {**cfg["engine"]["output"], "adapter": "artifact_export"}}}
        write_outputs(r["records"], csv_cfg["engine"], out_dir, False, csv_cfg["wizard"])
    print_report(r)
    say(f"Artifacts: {out_dir}")
    return 0


def cmd_run(args) -> int:
    profile = load_json(PROFILE_FILE, {})
    cfg = load_json(CONFIG_FILE, None)
    if cfg is None:
        die("no config.json yet - run `python3 run.py setup` first")
    dry = not args.no_dry_run
    out_dir = HERE / "out" / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    r = run_pipeline(cfg, profile, out_dir, dry)
    print_report(r)
    say(f"Artifacts: {out_dir}")
    return 0


def cmd_doctor(args) -> int:
    profile = load_json(PROFILE_FILE, {})
    cfg = load_json(CONFIG_FILE, None)
    say("=== Doctor ===")
    ok = True
    say(f"  profile            : {profile.get('slug', 'missing')}")
    if cfg is None:
        say("  config.json        : MISSING (run `python3 run.py setup`)")
        return 1
    say("  config.json        : present")
    w = cfg.get("wizard", {})
    e = cfg.get("engine", {})
    refs = []
    for section in ("adapters",):
        def collect(o):
            if isinstance(o, dict):
                for k, v in o.items():
                    if k.endswith("_ref") and isinstance(v, str):
                        refs.append(v)
                    else:
                        collect(v)
            elif isinstance(o, list):
                for x in o:
                    collect(x)
        collect(cfg.get(section, {}))
    bad_refs = [r for r in refs if not resolve_ref(cfg, r)[1]]
    say(f"  config *_ref       : {len(refs)} found, {len(bad_refs)} unresolved")
    if bad_refs:
        ok = False
        say(f"    unresolved: {bad_refs}")
    say(f"  input adapter      : {e.get('input', {}).get('adapter', 'unset')}")
    say(f"  output adapter     : {e.get('output', {}).get('adapter', 'unset')}")
    oc = e.get("output", {})
    if oc.get("adapter") == "xlsx":
        target = (HERE / oc.get("path", "./out/report.xlsx")).resolve()
        say(f"  xlsx target        : {'present' if target.exists() else 'MISSING (a preview workbook and csv/json will be produced; no target workbook is created)'}")
    say(f"  templates          : {', '.join(w.get('notifications', {}).get('selected_templates', [])) or 'none'}")
    say(f"  groups             : {len(w.get('connector', {}).get('selected_group_ids', []))} selected, "
        f"isolation={w.get('connector', {}).get('group_isolation', 'unset')}")
    say(f"  dry run            : {w.get('confirmation', {}).get('dry_run', True)}")
    if not w.get("confirmation", {}).get("user_confirmed", False):
        say("  confirmation       : NOT confirmed")
        ok = False
    tz = w.get("schedule", {}).get("timezone", "")
    try:
        from zoneinfo import ZoneInfo
        ZoneInfo(tz or "UTC")
        say(f"  timezone           : {tz or 'UTC'} (valid)")
    except Exception:
        say(f"  timezone           : {tz} INVALID")
        ok = False
    for label, kind, value in (
            ("input", "input", e.get("input", {}).get("adapter", "")),
            ("output", "output", e.get("output", {}).get("adapter", "")),
            ("notify", "notify", e.get("notify", {}).get("adapter", "stdout"))):
        registered = value in ADAPTERS[kind]
        say(f"  {label} adapter reg  : {value or 'unset'} -> {'registered' if registered else 'NOT REGISTERED'}")
        if not registered:
            ok = False
    nr = w.get("output", {}).get("new_report", {})
    if nr.get("enabled") and not (nr.get("authorized_by") and nr.get("never_overwrite_existing")):
        say("  new report         : enabled but authorization incomplete")
        ok = False
    say(f"  result             : {'OK' if ok else 'ISSUES FOUND'}")
    return 0 if ok else 1


def cmd_info(args) -> int:
    profile = load_json(PROFILE_FILE, {})
    say(json.dumps(profile, indent=2, ensure_ascii=False))
    say(f"config.json present : {CONFIG_FILE.exists()}")
    say(f"demo data present   : {DEMO_INPUT.exists()}")
    return 0


THIN_RUNPY = """#!/usr/bin/env python3
# Generated entry point for a self-contained distributed skill.
import sys
from engine import main

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
"""


def cmd_install(args) -> int:
    profile = load_json(PROFILE_FILE, {})
    slug = profile.get("slug")
    if not slug:
        die("profile.json has no slug")
    dest = INSTALL_ROOT / slug
    files = ["SKILL.md", "README.md", "DESIGN.md", "config.example.json",
             "config.schema.md", "profile.json"]
    say(f"Install target: {dest}")
    say("  copies the shared engine so the installed skill runs standalone")
    if not args.apply:
        say("Dry run only. Re-run with --apply to write.")
        return 0
    dest.mkdir(parents=True, exist_ok=True)
    for name in files:
        src = HERE / name
        if src.exists():
            shutil.copy2(src, dest / name)
    ex = HERE / "examples"
    if ex.exists():
        shutil.copytree(ex, dest / "examples", dirs_exist_ok=True)
    shutil.copy2(PACKAGE_DIR / "engine.py", dest / "engine.py")
    (dest / "run.py").write_text(THIN_RUNPY, encoding="utf-8")
    say(f"Installed. Use it from {dest}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Capability skill runtime (standard library only)")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("demo", help="run the full pipeline on bundled sample data")
    p = sub.add_parser("setup", help="interactive onboarding wizard")
    p.add_argument("--yes", action="store_true", help="accept the recommended preset without prompting")
    sub.add_parser("doctor", help="validate config and adapters")
    p = sub.add_parser("run", help="run the pipeline (dry-run by default)")
    p.add_argument("--no-dry-run", action="store_true", help="allow real writes and sends")
    sub.add_parser("info", help="show profile and config status")
    p = sub.add_parser("install", help="install into the local skills directory")
    p.add_argument("--apply", action="store_true", help="actually copy files")
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        say("\nStart here: python3 run.py demo")
        return 0
    return {"demo": cmd_demo, "setup": cmd_setup, "doctor": cmd_doctor,
            "run": cmd_run, "info": cmd_info, "install": cmd_install}[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
