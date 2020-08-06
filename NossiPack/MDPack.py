from typing import List, Dict, Tuple, Callable

from Fantasy.Item import fendeconvert, value_category, fenconvert, Item
from NossiSite.base import log


def traverse_md(md: str, seek: str) -> str:
    result = ""
    level = 0
    for line in md.split("\n"):
        if line.strip().startswith("#") or level:
            current_level = len(line.strip()) - len(line.strip().lstrip("#"))
            if current_level and level >= current_level:
                level = 0
                continue
            if (
                level
                or line.strip().lstrip("#").strip(": ").upper()
                == seek.strip(": ").upper()
            ):
                if not level:
                    level = current_level
                result += line + "\n"
    return result


def split_md(lines, level=0) -> Tuple[str, Dict[str, Tuple]]:
    """
    breaks down the structure of a md text into nested tuples of a string
    of the text directly after the heading and a dictionary of all the subheadings

    :param lines: \n separated string, or a stack of lines
    (top line on top of the stack)
    :param level: the level of heading this split started and therefore should end on
    :return: a Tuple of the direct text and a dict containing recursive output
    """
    if isinstance(lines, str):
        lines = list(reversed(lines.split("\n")))  # build stack of lines
    text = ""
    children = {}
    while len(lines):
        line = lines.pop()
        if line.strip().startswith("#"):

            current_level = len(line.strip()) - len(line.lstrip("# "))
            if (
                current_level and level >= current_level
            ):  # we are on equal level or above
                lines.append(line.strip())  # push the current line back
                return text, children
            else:
                children[line.lstrip("# ").strip()] = split_md(lines, current_level)
                continue
        text += line + "\n"
    return text, children


def extract_tables(
    mdtree: Tuple[str, Dict], flash: Callable[[str], None] = None
) -> Tuple[str, Dict[str, Tuple], List[List[List[str]]]]:
    """
    traverses the output of split_md and consumes table text where possible.
    Tables are appended to a List, at the end of each tuple
    :param flash: if given, tables are processed through
    :param mdtree: output of split_md
    :return: a Tuple of the remaining direct text a dict containing children and a List of Tables
    """
    children = {}
    for child, content in mdtree[1].items():
        children[child] = extract_tables(content, flash)
    text = ""
    tables = []
    run = ""
    for line in mdtree[0].splitlines(True):
        if "|" in line:
            run += line
            continue
        elif run:
            tables.append(table(run))
            run = ""
        text += line
    if run:
        tables.append(table(run))
    if flash:
        for t in tables:
            total_table(t, flash)
    return text, children, tables


def confine_to_tables(
    mdtree: Tuple[str, Dict, List], headers=True
) -> Tuple[Dict[str, object], List[str]]:
    """
    simplifies an mdtree into just a dictionary of dictionaries.
    Makes the assumption that either children or a table can be had, and that if children exist they
    only consist of text (and are thus key values)
    :param headers: if false, headers of the tables will be cut off
    :param mdtree: output of extract_tables
    :return: Dictionary that recursively always endsin ints
    """
    result = {}
    processed = False
    errors = []

    def error(msg: str):
        errors.append(msg)
        log.info(msg)

    if mdtree[2]:
        for subtable in mdtree[2]:
            skiprow = not headers
            for row in subtable:
                if skiprow:
                    skiprow = False
                    continue
                if not row:
                    continue
                if len(row) != 2:
                    error(f"Malformed KeyValue at row '{'|'.join(row)}' in {subtable} ")
                    continue
                result[row[0]] = row[1]
                processed = True
    if mdtree[1]:
        for child, content in mdtree[1].items():
            if content[1] or content[2]:
                if processed:
                    error(f"Extraneous Subheading: '{', '.join(mdtree[1].keys())}'")
                else:
                    result[child], newerrors = confine_to_tables(content, headers)
                    errors += newerrors
            else:
                result[child] = content[0]
                processed = True

    if mdtree[0].strip():
        error(f"Extraneous Text: '{mdtree[0]}'")
    return result, errors


def table(text: str) -> List[List[str]]:
    """
    gets table from md text.
    Assumes all text is part of table and will enforce the tablewidth given in
    format row. This means non-table text will be assumed to be just the first
    column and the rest will be filled with "". Every column past the ones
    alignment was defined for will be cut.

    :param text: md text from the first to the last line of the table
    :return: list of table rows, all of uniform length
    """
    rows = [row.strip() for row in text.split("\n") if row.strip()]
    if len(rows) > 1:
        formatline = [x for x in rows[1].split("|") if "-" in x]
        length = len(formatline)
        return [split_row(rows[0], length)] + [split_row(x, length) for x in rows[2:]]
    return []


def split_row(row: str, length: int) -> List[str]:
    """
    splits the row into the given length at |, cutting and adding as needed

    :param row: md table row string
    :param length: exakt number of columns
    :return: List of the first length table cells
    """
    split = [x.strip() for x in row.split("|")]
    if len(split) > length and row.startswith("|"):
        split = split[1:]
    # fill jagged edges with empty strings and cut tolength
    return (split + [""] * (length - len(split)))[:length]


def total_table(table_input, flash):
    try:
        if table_input[-1][0].lower() in Item.total_row_marker:
            trackers = [[0, ""] for _ in range(len(table_input[0]) - 1)]
            for row in table_input[1:-1]:
                for i in range(len(trackers)):
                    r = row[i + 1].strip().lower()
                    if "," in r:
                        flash(f"',' in {r} should not be there")
                        continue
                    if r:
                        try:
                            if not trackers[i][1]:
                                trackers[i][1] = value_category(r)
                            trackers[i][0] += fenconvert(r)
                        except Exception as e:
                            flash(
                                str(e.args)
                                + f" {r} cannot be processed by a totalling table"
                            )
            for i, t in enumerate(trackers):
                table_input[-1][i + 1] = fendeconvert(t[0], t[1])
    except:
        flash(
            "tabletotal failed for " + "\n".join("\t".join(row) for row in table_input)
        )
