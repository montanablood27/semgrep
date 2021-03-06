from subprocess import CalledProcessError

import pytest


@pytest.mark.parametrize(
    "filename", ["invalid_python.py",],
)
def test_rule_parser__failure__error_messages(run_semgrep_in_tmp, snapshot, filename):
    with pytest.raises(CalledProcessError) as excinfo:
        run_semgrep_in_tmp(
            config="rules/eqeq-python.yaml",
            target_name=f"bad/{filename}",
            output_format="text",
            stderr=True,
        )
    snapshot.assert_match(excinfo.value.output, "error.txt")


@pytest.mark.parametrize(
    "filename", ["invalid_python.py",],
)
def test_rule_parser__failure__error_messages_verbose(
    run_semgrep_in_tmp, snapshot, filename
):
    with pytest.raises(CalledProcessError) as excinfo:
        run_semgrep_in_tmp(
            config="rules/eqeq-python.yaml",
            target_name=f"bad/{filename}",
            options=["--verbose"],
            output_format="text",
            stderr=True,
        )

    # Hack to ignore timing in verbose mode
    output = "\n".join(excinfo.value.output.split("\n")[9:])
    snapshot.assert_match(output, "error.txt")
