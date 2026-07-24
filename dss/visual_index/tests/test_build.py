import importlib.util
import json
import pathlib
import sqlite3
import tempfile
import time
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "dss" / "visual_index" / "build.py"
SPEC = importlib.util.spec_from_file_location("visual_index_build", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ValparaiVisualIndexTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.output = pathlib.Path(cls.temp.name)
        started = time.perf_counter()
        cls.bundle = MODULE.Builder(ROOT / "dss" / "sites" / "valparai", cls.output).run()
        cls.elapsed = time.perf_counter() - started
        cls.db = sqlite3.connect(cls.output / "site_index.sqlite")

    @classmethod
    def tearDownClass(cls):
        cls.db.close()
        cls.temp.cleanup()

    def test_build_is_complete_and_fast(self):
        report = json.loads((self.output / "build_report.json").read_text())
        self.assertEqual(report["integrity"], "ok")
        self.assertEqual(report["sources"], 7)
        self.assertEqual(report["events"], 13_592)
        self.assertEqual(report["georeferenced_events"], 13_577)
        self.assertEqual(report["effort_rows"], 229)
        self.assertEqual(report["measurements"], 580)
        self.assertGreaterEqual(report["ready_views"], 8)
        self.assertLess(self.elapsed, 3.0)

    def test_duplicate_upstream_keys_do_not_drop_source_rows(self):
        expected = {
            "zenodo-7008315": 3741,
            "zenodo-11903722": 879,
            "zenodo-13910696": 638,
            "zenodo-10077040": 3684,
            "zenodo-7060430": 2473,
            "zenodo-7457732": 2177,
        }
        actual = dict(
            self.db.execute(
                "SELECT source_id,COUNT(*) FROM events GROUP BY source_id"
            ).fetchall()
        )
        self.assertEqual(actual, expected)

    def test_common_and_scientific_names_resolve_to_one_entity(self):
        row = self.db.execute(
            """SELECT canonical_name,display_name,COUNT(*)
               FROM events JOIN entities USING(entity_id)
               WHERE canonical_name='Bos gaurus'"""
        ).fetchone()
        self.assertEqual(row[0], "Bos gaurus")
        self.assertEqual(row[1], "Gaur")
        self.assertGreater(row[2], 750)
        aliases = self.db.execute(
            "SELECT COUNT(*) FROM entity_aliases WHERE alias_key IN ('gaur','bos gaurus')"
        ).fetchone()[0]
        self.assertEqual(aliases, 2)

    def test_plot_rows_join_to_real_locations(self):
        joined = self.db.execute(
            """SELECT COUNT(*) FROM events
               WHERE source_id='zenodo-10077040' AND cell_id IS NOT NULL"""
        ).fetchone()[0]
        self.assertEqual(joined, 3684)

    def test_effort_is_not_inferred_from_presence(self):
        sources = self.db.execute(
            "SELECT DISTINCT source_id FROM effort ORDER BY source_id"
        ).fetchall()
        self.assertEqual(sources, [("zenodo-7060430",)])
        georeferenced = self.db.execute(
            "SELECT COUNT(*) FROM effort WHERE cell_id IS NOT NULL"
        ).fetchone()[0]
        self.assertGreater(georeferenced, 200)

    def test_evidence_classes_and_source_capabilities_are_explicit(self):
        classes = self.db.execute(
            "SELECT evidence_class,COUNT(*) FROM events GROUP BY evidence_class"
        ).fetchall()
        self.assertEqual(classes, [("observed", self.bundle["build"]["events"])])
        capabilities = json.loads(
            self.db.execute(
                "SELECT capabilities_json FROM sources WHERE source_id='zenodo-7060430'"
            ).fetchone()[0]
        )
        self.assertIn("mappable", capabilities)
        self.assertIn("has_effort", capabilities)

    def test_every_probe_has_a_declared_visual(self):
        questions = json.loads(
            (ROOT / "dss" / "sites" / "valparai" / "questions.json").read_text()
        )["questions"]
        views = {item["view_id"]: item for item in self.bundle["views"]}
        for question in questions:
            with self.subTest(question=question["id"]):
                self.assertIn(question["first_visual"], views)
        self.assertEqual(views["donor_coverage_and_gate_map"]["availability"], "partial")
        self.assertEqual(views["value_of_information_map"]["availability"], "blocked")

    def test_preview_is_a_real_visual_artifact(self):
        preview = self.output / "preview.png"
        self.assertTrue(preview.is_file())
        self.assertGreater(preview.stat().st_size, 30_000)

    def test_interactive_filter_query_is_immediate(self):
        entity_id = self.db.execute(
            "SELECT entity_id FROM entity_aliases WHERE alias_key='lion tailed macaque'"
        ).fetchone()[0]
        started = time.perf_counter()
        rows = self.db.execute(
            """SELECT cell_id,COUNT(*),MIN(event_date),MAX(event_date)
               FROM events WHERE entity_id=? AND cell_id IS NOT NULL
               GROUP BY cell_id ORDER BY COUNT(*) DESC""",
            (entity_id,),
        ).fetchall()
        elapsed = time.perf_counter() - started
        self.assertGreater(len(rows), 10)
        self.assertLess(elapsed, 0.1)


if __name__ == "__main__":
    unittest.main()
