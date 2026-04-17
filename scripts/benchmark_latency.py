"""
Benchmark end-to-end latency for one inspection side.

Usage:
    python scripts/benchmark_latency.py --side1 path/to/cam1.png path/to/cam2.png
    python scripts/benchmark_latency.py --side1 path/to/cam1.png path/to/cam2.png --runs 20
    python scripts/benchmark_latency.py --mock --runs 10

The script measures only the processing time (OCR + compare + decision),
matching the <1 second / side target from docs/plan.md.
"""
from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path

# Ensure project root is on sys.path when run directly
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.api.deps import build_container
from src.domain.enums import InspectionSide
from src.domain.models import CaptureInput, SideInspectionInput


def _load_capture(path: str, camera_id: str) -> CaptureInput:
    p = Path(path)
    content = p.read_bytes()
    suffix = p.suffix.lower()
    media_type = "image/png" if suffix == ".png" else "image/jpeg"
    return CaptureInput(
        filename=p.name,
        content=content,
        media_type=media_type,
        camera_id=camera_id,
    )


def _mock_capture(camera_id: str) -> CaptureInput:
    """Minimal 1×1 white PNG for benchmarking without real images."""
    blank_png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
        b"\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18"
        b"\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    return CaptureInput(
        filename=f"{camera_id}_mock.png",
        content=blank_png,
        media_type="image/png",
        camera_id=camera_id,
    )


def run_benchmark(
    cam1: CaptureInput,
    cam2: CaptureInput,
    template_id: str,
    runs: int,
) -> None:
    container = build_container()

    # Ensure template exists and is approved
    try:
        container.template_service.get_approved_template(template_id)
    except LookupError:
        print(
            f"[ERROR] Template '{template_id}' not found or not approved.\n"
            "Upload and approve a template first, then re-run the benchmark."
        )
        sys.exit(1)

    latencies_ms: list[float] = []

    for i in range(runs):
        scan_job_id = f"BENCH_{i:04d}"
        container.inspection_orchestrator.start_scan_job(
            scan_job_id=scan_job_id,
            template_id=template_id,
        )
        inspection_input = SideInspectionInput(
            side=InspectionSide.SIDE1,
            captures=[cam1, cam2],
        )

        t0 = time.perf_counter()
        container.inspection_orchestrator.inspect_side1(scan_job_id, inspection_input)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        latencies_ms.append(elapsed_ms)
        print(f"  run {i + 1:>3}/{runs}  {elapsed_ms:7.1f} ms")

    print("\n--- Benchmark Results ---")
    print(f"  runs   : {runs}")
    print(f"  min    : {min(latencies_ms):.1f} ms")
    print(f"  max    : {max(latencies_ms):.1f} ms")
    print(f"  mean   : {statistics.mean(latencies_ms):.1f} ms")
    print(f"  median : {statistics.median(latencies_ms):.1f} ms")
    if runs >= 2:
        print(f"  stdev  : {statistics.stdev(latencies_ms):.1f} ms")

    target_ms = 1000.0
    passed = statistics.median(latencies_ms) <= target_ms
    status = "PASS ✓" if passed else "FAIL ✗"
    print(f"\n  Target (<{target_ms:.0f} ms median): {status}")
    sys.exit(0 if passed else 1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark inspection side latency.")
    parser.add_argument("--template-id", default="BENCHMARK_TEMPLATE", help="Approved template ID to use.")
    parser.add_argument("--runs", type=int, default=10, help="Number of benchmark runs.")
    parser.add_argument("--mock", action="store_true", help="Use mock images (no real camera files needed).")
    parser.add_argument("--side1", nargs=2, metavar=("CAM1", "CAM2"), help="Paths to cam1 and cam2 images.")
    args = parser.parse_args()

    if args.mock:
        cam1 = _mock_capture("cam1")
        cam2 = _mock_capture("cam2")
    elif args.side1:
        cam1 = _load_capture(args.side1[0], "cam1")
        cam2 = _load_capture(args.side1[1], "cam2")
    else:
        parser.error("Provide --mock or --side1 <cam1_path> <cam2_path>")

    run_benchmark(cam1=cam1, cam2=cam2, template_id=args.template_id, runs=args.runs)


if __name__ == "__main__":
    main()
