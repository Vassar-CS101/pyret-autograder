#!/usr/bin/env python3

import json
import sys
from os.path import basename, dirname

_, input_filename, output_filename, points_filename = sys.argv

# points is dict of string -> float with keys of "wheat", filenames of
# chaffs, and names corresponding to check block names in testsuite

visibility = "visible"

with open(input_filename) as raw_f:
    raw = json.load(raw_f)

with open(points_filename) as points_f:
    points = json.load(points_f)

tests_passed = {}  # name -> bool  (keys same as for points)
tests_errored = []
chaff_names = set()
using_examplar = "examplar" in points
if using_examplar:
    assert "wheat" in points["examplar"]


def gen_error(filename, message, examplar=False):
    if examplar:
        tests_errored.append(
            {
                "name": filename,
                "score": 0,
                "max_score": points["examplar"][filename],
                "output": f"Error: {message}",
                "visibility": visibility,
            }
        )
    else:
        for name, score in points[filename].items():
            tests_errored.append(
                {
                    "name": name,
                    "score": 0,
                    "max_score": score,
                    "output": f"Error: {message}",
                    "visibility": visibility,
                }
            )


# Populate testsuite_tests
for test in raw:
    if "wheat" in test["code"]:
        if "Err" in test["result"]:
            pass
        elif len(test["result"]["Ok"]) == 0:
            pass
        else:
            something_failed = False
            for check_block in test["result"]["Ok"]:
                if not (all([t["passed"] for t in check_block["tests"]])):
                    something_failed = True
            tests_passed["wheat"] = not (something_failed)
    elif "chaff" in test["code"]:
        chaff_name = basename(test["code"]).replace(".arr", "")
        if "Err" in test["result"]:
            pass
        elif len(test["result"]["Ok"]) == 0:
            pass
        else:
            something_failed = False
            for check_block in test["result"]["Ok"]:
                if not (all([t["passed"] for t in check_block["tests"]])):
                    something_failed = True
            tests_passed[chaff_name] = something_failed
            chaff_names.add(chaff_name)
    else:
        # Test suite
        if "Err" in test["result"]:
            gen_error(
                basename(dirname(test["tests"].split(";")[1])),
                test["result"]["Err"],
            )
        else:
            for check_block in test["result"]["Ok"]:
                tests_passed[check_block["name"]] = all(
                    [t["passed"] for t in check_block["tests"]]
                )

tests_scores = []
# list("name": str,
#      "score": float,
#      "max_score": float,
#      "output": str,
#      "visibility": "after_published"

for name in tests_passed:
    # Assign points
    all_names_in_points = {
        i[0]: i[1]
        for i in {
            item
            for sublist in [i.items() for i in points.values()]
            for item in sublist
        }
    }

    if name not in all_names_in_points:
        print(f"Test {name} not in points json")
    else:
        max_score = all_names_in_points[name]
        if name in chaff_names or name == "wheat":
            if (
                "examplar" not in points
                or "num-for-full-credit" not in points["examplar"]
            ):
                # We're dealing with a chaff but aren't handling it as a
                # percentage of chaffs passed
                score = 0
                if ("wheat" in tests_passed
                        and tests_passed["wheat"]
                        and tests_passed[name]):
                    score = all_names_in_points[name]

                message = "Failed some tests in this block"
                if tests_passed[name]:
                    message = "Passed all tests in this block!"
                elif "wheat" not in tests_passed:
                    message = "Wheat errored"
                elif not tests_passed["wheat"]:
                    message = "Wheat failed"

                tests_scores.append(
                    {
                        "name": name,
                        "score": score,
                        "max_score": max_score,
                        "output": message,
                        "visibility": "visible"
                        if "on submission" in name
                        else visibility,
                    }
                )
        else:
            score = 0
            message = "Failed some tests in this block"
            if tests_passed[name]:
                score = all_names_in_points[name]
                if score == max_score:
                    message = "Passed all tests in this block!"
            tests_scores.append(
                {
                    "name": name,
                    "score": score,
                    "max_score": max_score,
                    "output": message,
                    "visibility": "visible"
                    if "on submission" in name
                    else visibility,
                }
            )

if (
    using_examplar
    and "examplar" in points
    and "num-for-full-credit" in points["examplar"]
):
    chaffs_passed, total_chaffs, total_for_100_chaffs = (
        0,
        len(chaff_names),
        points["examplar"]["num-for-full-credit"],
    )

    if "wheat" in tests_passed and tests_passed["wheat"]:
        for name in chaff_names:
            if name in tests_passed and tests_passed[name]:
                chaffs_passed += 1
        message = f"{chaffs_passed}/{total_chaffs} bugs caught; " + \
            f"need {total_for_100_chaffs} for full credit"
    else:
        message = "Wheat failed"

    tests_scores.append(
        {
            "name": "buggies",
            "score": min(total_for_100_chaffs, chaffs_passed),
            "max_score": total_for_100_chaffs,
            "output": message,
            "visibility": visibility,
        }
    )

output = {
    "stdout_visibility": "visible",
    "tests": tests_scores + tests_errored,
}

with open(output_filename, "w+") as f:
    json.dump(output, f)
