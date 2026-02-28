#!/usr/bin/env python3
"""
Generate a validation report for pull requests.
Combines output from validate_dataset.py and check_duplicates.py into a
formatted Markdown comment suitable for posting to a GitHub PR.
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run_check(script: str) -> tuple[int, str]:
    result = subprocess.run(
        [sys.executable, script],
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    return result.returncode, output.strip()


def main():
    scripts_dir = Path(__file__).parent

    print("Running validation checks...")

    val_code, val_output = run_check(str(scripts_dir / "validate_dataset.py"))
    dup_code, dup_output = run_check(str(scripts_dir / "check_duplicates.py"))

    val_status = "✅ Passed" if val_code == 0 else "❌ Failed"
    dup_status = "✅ Passed" if dup_code == 0 else "❌ Failed"
    overall_status = "✅ All checks passed" if (val_code == 0 and dup_code == 0) else "❌ One or more checks failed"

    report = f"""## 🔍 Data Validation Report

**Generated**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
**Overall Status**: {overall_status}

---

### Schema & Field Validation — {val_status}

<details>
<summary>Click to expand output</summary>

```
{val_output}
```

</details>

---

### Duplicate Detection — {dup_status}

<details>
<summary>Click to expand output</summary>

```
{dup_output}
```

</details>

---
*This report is generated automatically by the data-validation workflow.*
"""

    # Print for logs
    print(report)

    # Write to file for GitHub Actions to pick up
    report_path = Path("validation_report.md")
    with open(report_path, "w") as f:
        f.write(report)
    print(f"\nReport written to {report_path}")

    # Set GitHub Actions output
    output_file = os.environ.get("GITHUB_OUTPUT")
    if output_file:
        with open(output_file, "a") as f:
            f.write(f"validation_passed={'true' if val_code == 0 and dup_code == 0 else 'false'}\n")

    # Exit with failure if any check failed
    sys.exit(0 if (val_code == 0 and dup_code == 0) else 1)


if __name__ == "__main__":
    main()
