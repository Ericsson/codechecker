import json
import subprocess
from typing import Optional
import xml.etree.ElementTree as ET


def get_severity_label_for_cppcheck(cppcheck_severity: Optional[str]) -> str:
    """
    Get CodeChecker severity for a cppcheck.

    Cppcheck severity levels:
      * error: when code is executed there is either undefined behavior or
        other error, such as a memory leak or resource leak.
      * warning: when code is executed there might be undefined behavior
      * style: stylistic issues, such as unused functions, redundant code.
      * performance: run time performance suggestions based on common
        knowledge.
      * portability: portability warnings. Implementation defined behavior.
      * information: configuration problems.
    """
    severity = "UNSPECIFIED"

    if cppcheck_severity == "error":
        severity = "HIGH"
    elif cppcheck_severity == "warning":
        severity = "MEDIUM"
    elif cppcheck_severity == "style":
        severity = "STYLE"
    elif cppcheck_severity in ["performance", "portability", "information"]:
        severity = "LOW"

    return f"severity:{severity}"


def main():
    """ Get CodeChecker labels for pylint analyzer. """
    out = subprocess.check_output(
        ["cppcheck", "--errorlist"],
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        encoding="utf-8",
        errors="ignore")

    root = ET.fromstring(out)

    labels = {}
    for error in root.find("errors"):
        checker_name = error.get("id")
        cppcheck_severity = error.get("severity")
        labels[checker_name] = [
            get_severity_label_for_cppcheck(cppcheck_severity)]

    print(json.dumps({
        "analyzer": "cppcheck",
        "labels": labels
    }, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
