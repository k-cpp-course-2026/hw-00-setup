import subprocess
import sys
import json
import pathlib
from os import environ
import difflib


def update_score(db_path, student, problem_id, score):
    import sqlite3

    conn = sqlite3.connect(db_path)
    try:


        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS results (
                student    TEXT    NOT NULL,
                problem_id INTEGER NOT NULL,
                status     BOOLEAN DEFAULT NULL,
                PRIMARY KEY (problem_id, student)
            )
            """
        )

        conn.execute(
            """
            INSERT INTO results (student, problem_id, status)
            VALUES (?, ?, ?)
            ON CONFLICT(student, problem_id)
            DO UPDATE SET status = excluded.status
            """,
            (student, problem_id, score),
        )


        conn.commit()
    finally:
        conn.close()
    

def print_diff(expected, actual):
    print(f"--- Test FAILED ---")
    diff = difflib.unified_diff(
        expected.splitlines(keepends=True),
        actual.splitlines(keepends=True),
        fromfile="expected",
        tofile="actual",
    )
    sys.stdout.writelines(diff)
    print()

def run_case(binary, case_dir, case_name, timeout=5):
    inp = (case_dir / f"{case_name}.in").read_text()
    expected = (case_dir / f"{case_name}.testout").read_text()
    try:
        result = subprocess.run(
            [binary], input=inp, capture_output=True,
            text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return False, "timeout"

    actual = result.stdout
    ok = actual == expected
    diff_output = ""
    if not ok:
        diff_output = "".join(difflib.unified_diff(
            expected.splitlines(keepends=True),
            actual.splitlines(keepends=True),
            fromfile="expected",
            tofile="actual"
        ))

    return ok, diff_output


def main():
    if len(sys.argv) < 3:
        print("Usage: run_tests.py <binary> <cases_dir>")
        sys.exit(2)

    binary = sys.argv[1]
    cases_dir = pathlib.Path(sys.argv[2])

    results = []
    all_passed = True

    for in_file in sorted(cases_dir.glob("*.in")):
        name = in_file.stem
        ok, diff_output = run_case(binary, cases_dir, name)
        if not ok:
            print(diff_output)
            all_passed = False
        results.append({"test": name, "passed": ok})

    print(json.dumps({"solved": all_passed, "results": results}, indent=2))


    if "SAVE_SCORE_DB" in environ:
        if len(sys.argv) < 5:
            print("Usage: run_tests.py <binary> <cases_dir> <student> <problem_id>")
            sys.exit(2)

        student = sys.argv[3]
        problem_id = sys.argv[4]
        
        print(f'Student: {student}')
        print(f'Problem id: {problem_id}')

        update_score(environ["SAVE_SCORE_DB"], student, problem_id, all_passed)

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()