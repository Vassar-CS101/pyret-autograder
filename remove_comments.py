#!/usr/bin/env python3

import os
import re
import sys

import pyparsing

data = ""
filename = sys.argv[1]

try:
    with open(filename, "a+", encoding="utf-8") as first:
        first.write("\n")

    with open(filename, "r", encoding="utf-8") as fin:
        data = fin.read()

        multiline_comment = pyparsing.nestedExpr("#|", "|#").suppress()
        data = multiline_comment.transformString(data)

        data = re.sub(r"use context.*\n", "\n", data)

        # Remove comments, but not if it might have the end of an enclosing
        # docstring.
        data = re.sub(r"#\s*\n", "\n", data)
        data = re.sub(r"#.*[^\`\"]\n", "\n", data)

        data = re.sub(r"include image\n", "include tables\n", data)
        data = re.sub(r"include lists\n", "\n", data)
        data = re.sub(r"->\s*Image\s*:", ":", data)
        table_pattern = r"include shared-gdrive\(\s*\"dcic-2021\"," + \
            r"\s*\"1wyQZj_L0qqV9Ekgr9au6RX2iqt2Ga8Ep\"\s*\)"
        num_occur = len(re.findall(table_pattern, data, flags=re.DOTALL))
        if num_occur > 1:
            data = re.sub(
                table_pattern, "", data, count=num_occur - 1, flags=re.DOTALL
            )
        data = re.sub("use context essentials2021", "", data)

    os.remove(filename)
    with open(filename, "w", encoding="utf-8") as output:
        if "provide *" not in data:
            output.write("provide *\n")
        if "provide-types *" not in data:
            output.write("provide-types *\n")
        if "include essentials2021" not in data:
            output.write("include essentials2021\n")

        output.write(data)
except FileNotFoundError:
    print(f"ERROR: File {filename} not found.", file=sys.stderr)
