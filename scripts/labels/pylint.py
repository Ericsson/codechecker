import json
import re
import subprocess


def get_severity_label_for_kind(kind: str) -> str:
    """
    Get CodeChecker severity for a pylint kind.

    There are 5 kind of message types :
      * (C) convention, for programming standard violation
      * (R) refactor, for bad code smell
      * (W) warning, for python specific problems
      * (E) error, for probable bugs in the code
      * (F) fatal, if an error occurred which prevented pylint from doing
            further processing.
    """
    severity = "UNSPECIFIED"
    if kind == "F":
        severity = "CRITICAL"
    elif kind == "E":
        severity = "HIGH"
    elif kind == "W":
        severity = "MEDIUM"
    elif kind == "R":
        severity = "STYLE"
    elif kind == "C":
        severity = "LOW"

    return f"severity:{severity}"


def main():
    """ Get CodeChecker labels for pylint analyzer. """
    out = subprocess.check_output(
        ["pylint", "--list-msgs"],
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        encoding="utf-8",
        errors="ignore")

    pattern = re.compile(r"^:(?P<name>[^ ]+) \((?P<kind>\S)(?P<id>\S+)\): .*")
    labels = {}
    for line in out.split('\n'):
        m = pattern.match(line)
        if m:
            checker_name = m.group("name")
            kind = m.group("kind")
            labels[checker_name] = [get_severity_label_for_kind(kind)]

    print(json.dumps({
        "analyzer": "pylint",
        "labels": labels
    }, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
