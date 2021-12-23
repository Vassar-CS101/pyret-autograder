#!/usr/bin/env python3

import json
import os
import re
import shutil
import subprocess
import sys
from os.path import basename, dirname

from prehook_lib import ImportFixer

NODE_PATH = "nodejs"
JQ = "jq"
AUTOGRADER = "/autograder"
SOURCE = f"{AUTOGRADER}/source/pyret-autograder"
PYRET_PATH = f"{AUTOGRADER}/pyret-lang/pyret-lang"
NODE_MODULES_PATH = f"{PYRET_PATH}/node_modules"
RUNNER_PATH = f"{SOURCE}/runner.js"
RESULTS = f"{AUTOGRADER}/results"
SUBMISSION = f"{AUTOGRADER}/submission"
CACHE_DIR = f"{SOURCE}/cache"
STENCIL = f"{SOURCE}/stencil"
WHEATS = f"{SOURCE}/impls/wheat"
CHAFFS = f"{SOURCE}/impls/chaff"
TESTS = f"{SOURCE}/tests"


class CompileError(Exception):
    pass


def fix_imports(path, code_path, common_dir):
    fixer = ImportFixer(path, STENCIL)
    fixer.fix_import("code", dirname(code_path), basename(code_path))
    if common_dir:
        fixer.fix_import("common", common_dir)
    fixer.finalize()


def nonempty(path):
    return os.path.exists(path) and os.path.getsize(path)


def compile_tests(test_path, error_file):
    os.chdir(PYRET_PATH)
    rel_test_path = os.path.relpath(test_path)
    compiled_tests_path = f"{dirname(rel_test_path)}/tests.js"
    args = [
        NODE_PATH,
        "build/phaseA/pyret.jarr",
        "--build-runnable",
        rel_test_path,
        "--outfile",
        compiled_tests_path,
        "--standalone-file",
        RUNNER_PATH,
        "--builtin-js-dir",
        "src/js/trove/",
        "--builtin-arr-dir",
        "src/arr/trove",
        "--compiled-dir",
        CACHE_DIR,
        "--require-config",
        "src/scripts/standalone-configA.json",
    ]
    env = {"NODE_PATH": NODE_MODULES_PATH}
    try:
        print("Compiling tests...")
        subprocess.run(args, check=True, env=env)
    except Exception as e:
        print(e, file=sys.stderr)
        raise CompileError(e)

    # Check for compile error
    if not nonempty(compiled_tests_path):
        print(
            "Check", compiled_tests_path, "for compile error", file=sys.stderr
        )
        raise CompileError("Compile error")

    return compiled_tests_path


def run(code_path, test_path, common_dir):
    # Make sure cache dir exists
    print("Making sure cache dir exists...")
    if not os.path.exists(CACHE_DIR):
        os.mkdir(CACHE_DIR)

    # Make a directory for the job
    job_name = f"{basename(code_path)};{basename(test_path)}"
    job_path = f"{RESULTS}/{job_name}"
    print("Making directory for the job at", job_path)
    os.mkdir(job_path)

    # Copy tests into the job directory
    copied_test_path = f"{job_path}/tests.arr"
    print("Copying tests into the job directory at " + copied_test_path)
    shutil.copy(test_path, copied_test_path)
    test_path = copied_test_path

    if "wheat" in code_path or "chaff" in code_path:
        try:
            data = ""
            with open(test_path, "r", encoding="utf-8") as test:
                data = test.read()

            with open(test_path, "w", encoding="utf-8") as test:
                test.write("provide *\n")
                test.write("provide-types *\n")
                test.write(
                    'include file("' + os.path.relpath(code_path) + '")\n'
                )

                data = re.sub(r"provide.*[\n]", "", data)
                data = re.sub(
                    r'include my-gdrive\("hw.code-ignore.arr"\)', "", data
                )
                test.write(data)
        except Exception as ex:
            print(
                "Error while adding include to wheat or chaff!",
                file=sys.stderr,
            )
            print(ex)

    def report_error(error):
        with open(f"{job_path}/results.json", "w") as output:
            error = {
                "code": code_path,
                "tests": test_path,
                "result": {"Err": error},
            }
            output.write(json.dumps(error))

    # Fix test imports for this job
    print("Fixing test imports for this job...")
    fix_imports(test_path, code_path, common_dir)

    error_output = f"{job_path}/error.txt"
    with open(error_output, "a") as error:
        # Compile test file
        try:
            compiled_tests_path = compile_tests(test_path, error)
        except CompileError as e:
            print(
                f"Compilation failed: {code_path} {test_path}",
                file=sys.stderr,
            )
            print(e, file=sys.stderr)
            report_error("😫 Pyret error. Check that all names " +
                         "match those given in the assignment and " +
                         "functions take the right arguments.")
            return

        # Assume a timeout occurs
        report_error("Timeout")

        # Run tests on code
        output_path = f"{job_path}/raw.json"
        with open(output_path, "w") as output:
            print("Running tests on code...")
            args = [NODE_PATH, compiled_tests_path]
            env = {"NODE_PATH": NODE_MODULES_PATH}
            try:
                subprocess.run(
                    args, check=True, stdout=output, stderr=error, env=env
                )
            except Exception:
                print("Error: Failure running tests on code", file=sys.stderr)

    if nonempty(error_output):
        with open(error_output, "r", encoding="utf-8") as error:
            error_text = error.read()
            if "memory" in error_text:
                print("Out of memory error occurred.", file=sys.stderr)
                report_error("🤯 Out of memory error")
            else:
                print("Runtime error occurred.", file=sys.stderr)
                print(error_text, file=sys.stderr)
                report_error("🥺 Runtime error. Check that your code works " +
                             "on code.pyret.org. If so, try resubmitting.")

    if nonempty(output_path):
        # Write out results
        args = [
            JQ,
            "--compact-output",
            "--arg",
            "code",
            code_path,
            "--arg",
            "test",
            test_path,
            '{ code: $code, tests: $test, result: {Ok: (. |= map(select(.loc | contains("tests.arr"))))} }',
            output_path,
        ]
        with open(f"{job_path}/results.json", "w") as output:
            print("Writing results for this job...")
            with open(error_output, "a") as error:
                subprocess.run(args, check=True, stdout=output, stderr=error)

    if not nonempty(error_output):
        os.remove(error_output)
        os.remove(compiled_tests_path)


if __name__ == "__main__":
    os.chdir(AUTOGRADER)
    if os.path.exists(RESULTS):
        shutil.rmtree(RESULTS)
    os.mkdir(RESULTS)

    student_common_path = ""
    student_code_path = ""
    student_test_path = ""
    for root, _, files in os.walk(SUBMISSION):
        for f in files:
            if "common" in f:
                student_common_path = os.path.join(root, f)
            if "code" in f:
                student_code_path = os.path.join(root, f)
            if "tests" in f:
                student_test_path = os.path.join(root, f)
    # assert student_common_path and student_code_path and student_test_path
    student_common_dir = dirname(student_common_path)

    os.chdir(SOURCE)  # FIXME: is this needed?

    # Printing paths for debugging
    print("COMMON PATH:", student_common_path)
    print("CODE PATH:", student_code_path)
    print("TEST PATH:", student_test_path)

    # Fix import statements in student's common file
    if student_common_path:
        print("Fixing import statements in student's common file...")
        fix_imports(student_common_path, student_code_path, SUBMISSION)

    # Fix import statements in student's code file
    print("Fixing import statements in student's code file...")
    fix_imports(student_code_path, student_code_path, SUBMISSION)

    # Run tests against student code
    for root, _, files in os.walk(TESTS):
        print("Running test suite against student code...")
        for f in files:
            if f not in ["README", "README.md", ".gitkeep"]:
                test = os.path.join(root, f)
                run(student_code_path, test, student_common_dir)

    # Run wheats against student tests
    for root, _, files in os.walk(WHEATS):
        print("Running wheats against student tests...")
        for f in files:
            if f not in ["README", "README.md", ".gitkeep"]:
                wheat = os.path.join(root, f)
                fix_imports(wheat, wheat, dirname(wheat))
                run(wheat, student_test_path, student_common_dir)

    # Run chaffs against student tests
    for root, _, files in os.walk(CHAFFS):
        print("Running chaffs against student tests...")
        for f in files:
            if f not in ["README", "README.md", ".gitkeep"]:
                chaff = os.path.join(root, f)
                fix_imports(chaff, chaff, dirname(chaff))
                run(chaff, student_test_path, student_common_dir)
