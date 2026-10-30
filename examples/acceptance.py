"""Run the whole ProofBoard workflow on the demo project and record what happened.

    python examples/acceptance.py --out /tmp/evidence

Everything is deterministic: the demo is copied to a temporary folder and a fixed clock is used.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
NOW = "2026-10-29T17:00:00Z"
LATER = "2027-02-10T17:00:00Z"


class Run:
    def __init__(self, work: Path) -> None:
        self.work = work
        self.lines: list[str] = []

    @staticmethod
    def expect(got: int, want: int) -> None:
        if got != want:
            raise SystemExit(f"acceptance: expected exit {want}, got {got}")

    def say(self, text: str) -> None:
        self.lines.append(text)

    def cli(self, *args: str, show: str | None = None) -> int:
        full = [sys.executable, "-m", "proofboard", args[0], "-C", str(self.work), *args[1:]]
        proc = subprocess.run(full, capture_output=True, text=True, check=False)  # noqa: S603
        shown = show or "proofboard " + " ".join(args)
        self.say(f"$ {shown}")
        for stream in (proc.stdout, proc.stderr):
            clean = stream.replace(str(self.work), "demo")
            for line in clean.splitlines():
                self.say(line)
        self.say(f"[exit {proc.returncode}]")
        self.say("")
        return proc.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    out = Path(parser.parse_args(argv).out)
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "demo"
        shutil.copytree(HERE / "demo", work)
        run = Run(work)
        now = ["--now", NOW]

        run.say("== 1. Nothing is sealed yet ==")
        run.cli("check", *now)
        run.say("== 2. Seal the evidence ==")
        run.cli("seal", *now)
        run.say("== 3. Everything matches ==")
        run.expect(run.cli("check", *now), 0)
        for fmt, name in (("md", "board.md"), ("html", "board.html"), ("json", "board.json")):
            target = out / name
            subprocess.run(  # noqa: S603
                [
                    sys.executable,
                    "-m",
                    "proofboard",
                    "board",
                    "-C",
                    str(work),
                    "--format",
                    fmt,
                    "--out",
                    str(target),
                    *now,
                ],
                check=True,
                capture_output=True,
            )

        run.say("== 4. Someone edits the restore drill after the fact ==")
        drill = work / "evidence" / "restore-drill.txt"
        original = drill.read_text(encoding="utf-8")
        drill.write_text(original.replace("214 of 214", "214 of 214 (rounded)"), encoding="utf-8")
        run.cli("check", *now)
        run.cli("seal", *now)

        run.say("== 5. A mismatch is written into the drill ==")
        drill.write_text(original + "mismatch: 3 files\n", encoding="utf-8")
        run.cli("check", *now)
        drill.write_text(original, encoding="utf-8")

        run.say("== 6. Coverage falls below the claim ==")
        cov = work / "evidence" / "coverage.xml"
        good = cov.read_text(encoding="utf-8")
        cov.write_text(good.replace('line-rate="0.934"', 'line-rate="0.871"'), encoding="utf-8")
        run.cli("check", *now)
        cov.write_text(good, encoding="utf-8")

        run.say("== 7. The review note is deleted ==")
        note = work / "docs" / "threat-model-review.md"
        saved = note.read_bytes()
        note.unlink()
        run.cli("check", *now)
        note.write_bytes(saved)

        run.say("== 8. Evidence goes stale ==")
        run.cli("check", "--now", LATER)

        run.say("== 9. Restored and re-dated on purpose ==")
        run.expect(run.cli("check", *now), 0)
        run.cli("seal", "--refresh", "--now", LATER)
        run.cli("check", "--now", LATER)
        (out / "acceptance-transcript.txt").write_text(
            "\n".join(run.lines), encoding="utf-8", newline="\n"
        )
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
