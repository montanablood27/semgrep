import re
from pathlib import Path
from typing import Dict
from typing import List
from typing import Set
from typing import Tuple

from semgrep.error import SemgrepError
from semgrep.rule import Rule
from semgrep.rule_match import RuleMatch
from semgrep.util import print_msg

SPLIT_CHAR = "\n"


def _get_lines(path: Path) -> List[str]:
    contents = path.read_text()
    lines = contents.split(SPLIT_CHAR)
    return lines


def _get_match_context(rule_match: RuleMatch) -> Tuple[int, int, int, int]:
    start_obj = rule_match.start
    start_line = start_obj.get("line", 1) - 1  # start_line is 1 indexed
    start_col = start_obj.get("col", 1) - 1  # start_col is 1 indexed
    end_obj = rule_match.end
    end_line = end_obj.get("line", 1) - 1  # end_line is 1 indexed
    end_col = end_obj.get("col", 1) - 1  # end_line is 1 indexed
    return start_line, start_col, end_line, end_col


def _modify_file(rule_match: RuleMatch, fix: str) -> None:
    p = Path(rule_match.path)
    lines = _get_lines(p)

    # get the start and end points
    start_obj = rule_match.start
    start_line = start_obj.get("line", 1) - 1  # start_line is 1 indexed
    start_col = start_obj.get("col", 1) - 1  # start_col is 1 indexed
    end_obj = rule_match.end
    end_line = end_obj.get("line", 1) - 1  # end_line is 1 indexed
    end_col = end_obj.get("col", 1) - 1  # end_line is 1 indexed

    # break into before, to modify, after
    before_lines = lines[:start_line]
    before_on_start_line = lines[start_line][:start_col]
    after_on_end_line = lines[end_line][end_col + 1 :]  # next char after end of match
    modified_lines = (before_on_start_line + fix + after_on_end_line).splitlines()
    after_lines = lines[end_line + 1 :]  # next line after end of match
    contents_after_fix = before_lines + modified_lines + after_lines

    contents_after_fix_str = SPLIT_CHAR.join(contents_after_fix)
    p.write_text(contents_after_fix_str)


def _regex_replace(
    rule_match: RuleMatch, from_str: str, to_str: str, count: int = 1
) -> None:
    """
    Use a regular expression to autofix.
    Replaces from_str to to_str, starting from the left,
    exactly `count` times.
    """
    path = Path(rule_match.path)
    lines = _get_lines(path)

    start_line, _, end_line, _ = _get_match_context(rule_match)

    before_lines = lines[:start_line]
    after_lines = lines[end_line + 1 :]

    match_context = lines[start_line : end_line + 1]

    fix = re.sub(from_str, to_str, "\n".join(match_context), count)

    modified_context = fix.splitlines()

    modified_contents = before_lines + modified_context + after_lines
    path.write_text(SPLIT_CHAR.join(modified_contents))


def apply_fixes(rule_matches_by_rule: Dict[Rule, List[RuleMatch]]) -> None:
    """
        Modify files in place for all files with findings from rules with an
        autofix configuration
    """
    modified_files: Set[Path] = set()

    for _, rule_matches in rule_matches_by_rule.items():
        for rule_match in rule_matches:
            fix = rule_match.fix
            fix_regex = rule_match.fix_regex
            filepath = rule_match.path
            if fix:
                try:
                    _modify_file(rule_match, fix)
                    modified_files.add(filepath)
                except Exception as e:
                    raise SemgrepError(f"unable to modify file {filepath}: {e}")
            elif fix_regex:
                regex = fix_regex.get("regex")
                replacement = fix_regex.get("replacement")
                count = fix_regex.get("count", 0)
                if not regex or not replacement:
                    raise SemgrepError(
                        "'regex' and 'replacement' values required when using 'fix-regex'"
                    )
                try:
                    count = int(count)
                except ValueError:
                    raise SemgrepError(
                        "optional 'count' value must be an integer when using 'fix-regex'"
                    )
                try:
                    _regex_replace(rule_match, regex, replacement, count)
                    modified_files.add(filepath)
                except Exception as e:
                    raise SemgrepError(
                        f"unable to use regex to modify file {filepath} with fix '{fix}': {e}"
                    )
    num_modified = len(modified_files)
    print_msg(
        f"Successfully modified {num_modified} file{'s' if num_modified > 1 else ''}."
    )
