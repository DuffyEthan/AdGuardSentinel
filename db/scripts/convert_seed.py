import re
import sys

# Matches a 2-line insert pattern:
# INSERT INTO impression (impression_date, impression_time, impression_clicks)
# VALUES ('2026-01-01', '00:00', 8);
HEADER_RE = re.compile(
    r"^\s*INSERT\s+INTO\s+impression\s*\(\s*impression_date\s*,\s*impression_time\s*,\s*impression_clicks\s*\)\s*;?\s*$",
    re.IGNORECASE,
)

VALUES_RE = re.compile(
    r"^\s*VALUES\s*\(\s*'(?P<d>\d{4}-\d{2}-\d{2})'\s*,\s*'(?P<t>\d{2}:\d{2})'\s*,\s*(?P<c>\d+)\s*\)\s*;\s*$",
    re.IGNORECASE,
)

NEW_INSERT_PREFIX = "INSERT INTO impression (impression_ts, impression_date, impression_time, impression_clicks)\n"

def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: py convert_seed.py <input.sql> <output.sql>")
        return 1

    inp, outp = sys.argv[1], sys.argv[2]

    out_lines = []
    expecting_values = False

    with open(inp, "r", encoding="utf-8") as f:
        for line in f:
            # Skip the old header lines entirely
            if HEADER_RE.match(line):
                expecting_values = True
                continue

            m = VALUES_RE.match(line)
            if m:
                d, t, c = m.group("d"), m.group("t"), m.group("c")
                out_lines.append(NEW_INSERT_PREFIX)
                out_lines.append(
                    f"VALUES ((('{d}'::date + '{t}'::time))::timestamptz, '{d}', '{t}', {c});\n\n"
                )
                expecting_values = False
                continue

            # If the file has extra lines (blank lines etc.), ignore safely
            if expecting_values and line.strip() == "":
                continue

            # For anything else, ignore (keeps output clean)
            # If you want to debug unexpected formats, you can print/log here.

    with open(outp, "w", encoding="utf-8", newline="\n") as f:
        f.writelines(out_lines)

    print(f"Wrote {len(out_lines)//2} rows to {outp}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
