"""The four invariants the project promises, locked down as tests.

Run from the repository root:  python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from skillkit.engine import (  # noqa: E402
    _append_sheet, _new_workbook, _sheet_xml, _update_cells,
    dedupe, normalize, render_template, run_pipeline, write_outputs,
)


def rec(rid, key, value=10.0, group="G1", entity="E1", date="2026-01-01"):
    return {"id": rid, "entity": entity, "group": group, "value": value,
            "date": date, "business_key": key, "type": "structured_evidence"}


class DedupeTests(unittest.TestCase):
    def test_business_key_defines_duplicate(self):
        kept, dupes = dedupe(normalize([rec("m1", "K1"), rec("m2", "K1")]), {}, None)
        self.assertEqual(len(kept), 1)
        self.assertEqual(len(dupes), 1)
        self.assertEqual(dupes[0]["reason"], "business_key")

    def test_equal_value_is_not_a_duplicate(self):
        kept, dupes = dedupe(normalize([rec("m1", "K1", 10.0), rec("m2", "K2", 10.0)]), {}, None)
        self.assertEqual(len(kept), 2)
        self.assertEqual(dupes, [])

    def test_groups_are_isolated(self):
        kept, _ = dedupe(normalize([rec("m1", "K1", group="G1"),
                                   rec("m2", "K1", group="G2")]), {}, None)
        self.assertEqual(len(kept), 2)
        self.assertEqual(len({r["dedupe_key"] for r in kept}), 2)

    def test_rerun_with_persisted_ledger_skips_everything(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            cfg = {"dedupe": {"ledger_path": str(out / "ledger.json")}}
            first, _ = dedupe(normalize([rec("m1", "K1")]), cfg, out)
            second, dupes = dedupe(normalize([rec("m1", "K1")]), cfg, out)
            self.assertEqual(len(first), 1)
            self.assertEqual(second, [])
            self.assertEqual(len(dupes), 1)


class IdempotencyTests(unittest.TestCase):
    def test_repeated_sheet_write_never_multiplies_parts(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "t.xlsx"
            p.write_bytes(_new_workbook({"detail": [["id"], ["a"]]}))
            for i in range(4):
                _append_sheet(p, "detail", [["id"], [i]], None)
            with zipfile.ZipFile(p) as z:
                sheets = [n for n in z.namelist() if n.startswith("xl/worksheets/sheet")]
                wb = z.read("xl/workbook.xml").decode()
                rels = z.read("xl/_rels/workbook.xml.rels").decode()
                ct = z.read("[Content_Types].xml").decode()
            self.assertEqual(len(sheets), 1)
            self.assertEqual(wb.count("<sheet "), 1)
            self.assertEqual(rels.count("relationships/worksheet"), 1)
            self.assertEqual(ct.count("spreadsheetml.worksheet+xml"), 1)

    def test_repeated_cell_update_is_stable(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "t.xlsx"
            p.write_bytes(_new_workbook({"detail": [["v"], [1.0]]}))
            for _ in range(3):
                _update_cells(p, [["v"], [7.0]], None)
            with zipfile.ZipFile(p) as z:
                xml = z.read("xl/worksheets/sheet1.xml").decode()
            self.assertEqual(xml.count('<c r="A2">'), 1)
            self.assertIn("<v>7.0</v>", xml)


class BackupTests(unittest.TestCase):
    def test_every_write_creates_a_backup(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "t.xlsx"
            p.write_bytes(_new_workbook({"detail": [["a"], [1]]}))
            backups = root / "backups"
            _append_sheet(p, "detail", [["a"], [2]], backups)
            _append_sheet(p, "detail", [["a"], [3]], backups)
            self.assertEqual(len(list(backups.glob("*.bak"))), 2)
            for b in backups.glob("*.bak"):
                with zipfile.ZipFile(b) as z:
                    self.assertIsNone(z.testzip())

    def test_untouched_parts_stay_byte_identical(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "t.xlsx"
            original = _new_workbook({"detail": [["a"], [1]], "other": [["keep"], [9]]})
            p.write_bytes(original)
            with zipfile.ZipFile(p) as z:
                before = {i.filename: z.read(i.filename) for i in z.infolist()}
            _append_sheet(p, "detail", [["a"], [2]], None)
            with zipfile.ZipFile(p) as z:
                after = {i.filename: z.read(i.filename) for i in z.infolist()}
            for name in ("xl/worksheets/sheet2.xml", "docProps/app.xml", "_rels/.rels"):
                self.assertEqual(before[name], after[name])


class DryRunTests(unittest.TestCase):
    def test_dry_run_writes_only_a_change_log(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            engine = {"output": {"adapter": "xlsx", "mode": "new_report",
                                 "write_mode": "new_sheet", "path": str(out / "report.xlsx"),
                                 "sheet": "detail"}}
            notes = write_outputs(normalize([rec("m1", "K1")]), engine, out, True, {})
            self.assertTrue((out / "change-log.md").exists())
            self.assertFalse((out / "report.xlsx").exists())
            self.assertFalse((out / "report.csv").exists())
            self.assertTrue(any("dry-run" in n for n in notes))

    def test_pipeline_dry_run_has_no_external_writes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            inbox = root / "inbox"
            inbox.mkdir()
            (inbox / "records.json").write_text(json.dumps([rec("m1", "K1")]))
            cfg = {
                "engine": {
                    "input": {"adapter": "local_folder", "path": str(inbox)},
                    "output": {"adapter": "xlsx", "mode": "new_report",
                               "write_mode": "new_sheet", "path": str(root / "report.xlsx"),
                               "sheet": "detail"},
                    "notify": {"adapter": "stdout", "webhook_url": ""},
                    "dedupe": {"ledger_path": str(root / "ledger.json")},
                },
                "wizard": {"notifications": {"selected_templates": ["minimal"]},
                           "output": {"new_report": {"enabled": True,
                                                     "authorized_by": "test",
                                                     "never_overwrite_existing": True}}},
            }
            report = run_pipeline(cfg, {"slug": "test"}, root / "out", True)
            self.assertTrue(report["dry_run"])
            self.assertFalse((root / "report.xlsx").exists())
            self.assertTrue((root / "out" / "change-log.md").exists())


class TemplateTests(unittest.TestCase):
    def test_minimal_never_leaks_operational_fields(self):
        text = render_template("minimal", normalize([rec("m1", "K1")]), [], {})
        for forbidden in ("business_key", "ledger", "backup", "run.json", "duplicate"):
            self.assertNotIn(forbidden, text)

    def test_alert_only_is_silent_without_problems(self):
        self.assertEqual(render_template("alert_only", normalize([rec("m1", "K1")]), [], {"errors": []}), "")

    def test_all_four_templates_render(self):
        from skillkit.engine import TEMPLATES
        for name in TEMPLATES:
            self.assertIsInstance(render_template(name, normalize([rec("m1", "K1")]), [], {}), str)

    def test_sheet_xml_escapes_inline_strings(self):
        xml = _sheet_xml([["<script> & value"]])
        self.assertIn("&lt;script&gt;", xml)
        self.assertIn("&amp;", xml)


if __name__ == "__main__":
    unittest.main()
