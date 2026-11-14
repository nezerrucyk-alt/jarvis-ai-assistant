# -*- coding: utf-8 -*-
"""Downloads organizer: dry run, real moves, collisions, watcher diff."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from core.file_organizer import (
    FileOrganizerError,
    apply_plan,
    category_for,
    is_partial,
    new_files,
    plan,
    snapshot,
    unique_path,
)


class FileOrganizerTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="jarvis_sort_")
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def test_category_mapping(self) -> None:
        self.assertEqual(category_for("photo.JPG"), "Images")
        self.assertEqual(category_for("doc.pdf"), "Documents")
        self.assertEqual(category_for("setup.exe"), "Installers")
        self.assertEqual(category_for("archive.7z"), "Archives")
        self.assertEqual(category_for("unknown.xyz"), "Other")

    def test_partial_files(self) -> None:
        self.assertTrue(is_partial("movie.mp4.crdownload"))
        self.assertTrue(is_partial("file.PART"))
        self.assertFalse(is_partial("movie.mp4"))

    def test_plan_skips_dirs_hidden_and_partials(self) -> None:
        (self.root / "pic.png").write_text("x", encoding="utf-8")
        (self.root / "note.txt").write_text("x", encoding="utf-8")
        (self.root / ".hidden.png").write_text("x", encoding="utf-8")
        (self.root / "video.mp4.part").write_text("x", encoding="utf-8")
        (self.root / "Sub").mkdir()
        moves = plan(self.root)
        names = sorted(Path(move["source"]).name for move in moves)
        self.assertEqual(names, ["note.txt", "pic.png"])

    def test_plan_missing_folder(self) -> None:
        with self.assertRaises(FileOrganizerError):
            plan(self.root / "nope")

    def test_dry_run_does_not_move(self) -> None:
        source = self.root / "pic.png"
        source.write_text("x", encoding="utf-8")
        moves = plan(self.root)
        result = apply_plan(moves, dry_run=True)
        self.assertTrue(result["dry_run"])
        self.assertEqual(len(result["moved"]), 1)
        self.assertTrue(source.exists())

    def test_apply_moves_and_renames_collisions(self) -> None:
        first = self.root / "clip.mp4"
        first.write_text("one", encoding="utf-8")
        target_dir = self.root / "Video"
        target_dir.mkdir()
        (target_dir / "clip.mp4").write_text("occupied", encoding="utf-8")

        moves = plan(self.root)
        result = apply_plan(moves, dry_run=False)
        self.assertEqual(result["errors"], [])
        self.assertFalse(first.exists())
        self.assertTrue((target_dir / "clip (2).mp4").exists())
        self.assertEqual(
            (target_dir / "clip.mp4").read_text(encoding="utf-8"), "occupied"
        )

    def test_snapshot_and_new_files(self) -> None:
        snapshot_before = snapshot(self.root)
        fresh = self.root / "new.pdf"
        fresh.write_text("x", encoding="utf-8")
        current = snapshot(self.root)
        detected = new_files(snapshot_before, current)
        self.assertEqual([Path(path).name for path in detected], ["new.pdf"])
        self.assertEqual(new_files(current, current), [])

    def test_unique_path(self) -> None:
        target = self.root / "a.txt"
        target.write_text("x", encoding="utf-8")
        candidate = unique_path(target)
        self.assertEqual(candidate.name, "a (2).txt")


if __name__ == "__main__":
    unittest.main()
