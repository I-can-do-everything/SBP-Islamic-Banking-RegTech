# Evidence

Scripts and captured output that prove what the bug register says.

| File | What it is |
|---|---|
| `probe_prototype.py` | Calls each backend function with small realistic inputs and prints the result or error. Each line is labelled with the bug ID it shows. |
| `run_probe.sh` | Copies the backend to a temporary folder, patches only BUG-001 in the copy so the files can load, and runs the probe. The real code is not touched. |
| `probe_output_2026-11-06.txt` | Output of the probe on commit `e96988c`, Python 3.13. |

Lines labelled `control` are working features, included to show the probe itself is sound (for example `compute_hash` gives the correct SHA-256 of `abc`).

To re-run (needs `pydantic`, `pydantic-settings`, `python-dotenv` and `openpyxl` installed):

```bash
docs/evidence/run_probe.sh
```

Once fixes are applied, the same probes become automated tests in `backend/tests/`, and the fix log records the before and after output.
