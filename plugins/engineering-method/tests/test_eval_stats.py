"""Tests for skills/engineering-method/scripts/eval_stats.py.

What: runs the script as a subprocess on fixed inputs and pins its blocks byte for byte.
Use when: running the plugin's normal suite (python3 -m unittest discover tests).
Inputs: inline fixtures and temp files. Output: unittest results.
Side effects: creates and removes temporary directories.
Role: keeps the eval figures computed by code and pinned, so a reference and its graders cannot drift.
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "skills", "engineering-method", "scripts", "eval_stats.py")


def run(*args, stdin=None):
    p = subprocess.run([sys.executable, SCRIPT, *args], input=stdin, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def load():
    spec = importlib.util.spec_from_file_location("eval_stats", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class Floor(unittest.TestCase):
    def test_two_of_three_golden(self):
        code, out, _ = run("floor", "--name", "never quotes a refund amount", "--results", "PPF")
        self.assertEqual(code, 0)
        self.assertEqual(out, "\n".join([
            "EVAL_STATS floor v1",
            "CRITERION: never quotes a refund amount",
            "RUNS: 2 of 3 passed; failed runs: 3; invalid runs: none",
            "WILSON95: 0.21-0.94 (true per-run rate, 2 of 3)",
            "PASS_K: pass^3 = 0.30 at the observed rate 0.67",
            "PASS_K_LOW: pass^3 = 0.01 at the interval's lower bound 0.21",
            "VERDICT: not-reliable (a never-break rule needs 3 of 3)",
            "EVAL_STATS end", ""]))

    def test_three_of_three_is_reliable_on_this_sample_only(self):
        _, out, _ = run("floor", "--name", "x", "--results", "PPP")
        self.assertIn("PASS_K_LOW: pass^3 = 0.08 at the interval's lower bound 0.44", out)
        self.assertIn("VERDICT: reliable on this sample (3 of 3; rates below 0.44 not ruled out)", out)

    def test_zero_of_three(self):
        _, out, _ = run("floor", "--name", "x", "--results", "FFF")
        self.assertIn("RUNS: 0 of 3 passed; failed runs: 1, 2, 3; invalid runs: none", out)
        self.assertIn("WILSON95: 0.00-0.56", out)
        self.assertIn("PASS_K: pass^3 = 0.00", out)

    def test_invalid_runs_are_excluded_and_shown(self):
        _, out, _ = run("floor", "--name", "x", "--results", "PPIF")
        self.assertIn("RUNS: 2 of 3 passed; failed runs: 4; invalid runs: 3 (not counted)", out)
        self.assertIn("pass^3 = 0.30", out)

    def test_all_invalid_reports_no_figure(self):
        code, out, _ = run("floor", "--name", "x", "--results", "II")
        self.assertEqual(code, 0)
        self.assertIn("WILSON95: n/a (0 valid runs)", out)
        self.assertIn("VERDICT: no valid runs (re-run after delivery is confirmed)", out)

    def test_exponent_follows_n(self):
        _, out, _ = run("floor", "--name", "x", "--results", "PPPPPF")
        self.assertIn("PASS_K: pass^6 = 0.33 at the observed rate 0.83", out)

    def test_lower_case_and_two_pairs(self):
        _, out, _ = run("floor", "--name", "a", "--results", "ppf", "--name", "b", "--results", "PPP")
        self.assertEqual(out.count("EVAL_STATS floor v1"), 2)
        self.assertLess(out.index("CRITERION: a"), out.index("CRITERION: b"))

    def test_pass_k_from_the_fraction(self):
        self.assertAlmostEqual(load().pass_k(2, 3), (2 / 3) ** 3)

    def test_wilson_values(self):
        lo, hi = load().wilson(2, 3)
        self.assertEqual((round(lo, 2), round(hi, 2)), (0.21, 0.94))
        self.assertEqual(tuple(round(x, 2) for x in load().wilson(1, 1)), (0.21, 1.0))

    def test_bad_inputs_exit_2_with_empty_stdout(self):
        for args in (["--name", "x", "--results", ""], ["--name", "x", "--results", "PPX"],
                     ["--name", "x"], ["--results", "PP"], ["--name", "a", "--name", "b", "--results", "P"]):
            code, out, err = run("floor", *args)
            self.assertEqual((code, out), (2, ""), args)
            self.assertIn("ERROR:", err)


LABELS = "answer_id,criterion,owner,judge\n" + "\n".join(
    ["a%d,flags decisions that have no owner,pass,pass" % i for i in range(1, 7)]
    + ["a7,flags decisions that have no owner,fail,fail",
       "a8,flags decisions that have no owner,fail,pass",
       "a9,flags decisions that have no owner,fail,pass"]) + "\n"


class Calibrate(unittest.TestCase):
    def test_nine_labels_golden(self):
        code, out, _ = run("calibrate", "--labels", "-", stdin=LABELS)
        self.assertEqual(code, 0)
        self.assertEqual(out, "\n".join([
            "EVAL_STATS calibrate v1",
            "CRITERION: flags decisions that have no owner",
            "LABELS: 9 (owner-pass 6, owner-fail 3)",
            "TRUE_POSITIVE: judge passed 6 of 6 answers the owner passed",
            "TRUE_NEGATIVE: judge failed 1 of 3 answers the owner failed",
            "STATUS: uncalibrated, n = 9 (needs 30 owner-pass and 30 owner-fail; has 6 and 3)",
            "EVAL_STATS end", ""]))

    def test_calibrated_prints_rates(self):
        rows = ["answer_id,criterion,owner,judge"]
        rows += ["p%d,c,pass,%s" % (i, "pass" if i < 28 else "fail") for i in range(30)]
        rows += ["f%d,c,fail,%s" % (i, "fail" if i < 27 else "pass") for i in range(30)]
        _, out, _ = run("calibrate", "--labels", "-", stdin="\n".join(rows) + "\n")
        self.assertIn("TRUE_POSITIVE: 0.93 (28 of 30, Wilson95 0.79-0.98)", out)
        self.assertIn("TRUE_NEGATIVE: 0.90 (27 of 30, Wilson95 0.74-0.97)", out)
        self.assertIn("STATUS: calibrated", out)

    def test_no_rate_below_thirty_a_side(self):
        rows = ["answer_id,criterion,owner,judge"] + ["p%d,c,pass,pass" % i for i in range(30)] \
            + ["f%d,c,fail,fail" % i for i in range(29)]
        _, out, _ = run("calibrate", "--labels", "-", stdin="\n".join(rows) + "\n")
        self.assertIn("STATUS: uncalibrated, n = 59", out)
        for line in out.splitlines():
            if line.startswith("TRUE_NEGATIVE"):
                self.assertNotRegex(line, r"\b0\.\d\d\b")

    def test_side_with_no_labels_is_not_measured(self):
        rows = ["answer_id,criterion,owner,judge"] + ["p%d,c,pass,pass" % i for i in range(12)]
        _, out, _ = run("calibrate", "--labels", "-", stdin="\n".join(rows) + "\n")
        self.assertIn("TRUE_NEGATIVE: not measured (0 answers the owner failed)", out)
        self.assertIn("has 12 and 0; true negative rate unmeasured)", out)

    def test_header_only_is_n_zero(self):
        code, out, _ = run("calibrate", "--labels", "-", stdin="answer_id,criterion,owner,judge\n")
        self.assertEqual(code, 0)
        self.assertIn("CRITERION: (none labelled)", out)
        self.assertIn("STATUS: uncalibrated, n = 0", out)

    def test_criteria_sorted_and_separate(self):
        rows = "answer_id,criterion,owner,judge\n1,b,pass,pass\n2,a,fail,fail\n3,b,fail,pass\n"
        _, out, _ = run("calibrate", "--labels", "-", stdin=rows)
        self.assertLess(out.index("CRITERION: a"), out.index("CRITERION: b"))

    def test_file_and_stdin_agree(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as fh:
            fh.write(LABELS)
        try:
            self.assertEqual(run("calibrate", "--labels", fh.name)[1],
                             run("calibrate", "--labels", "-", stdin=LABELS)[1])
        finally:
            os.unlink(fh.name)

    def test_bad_labels_exit_2(self):
        for text in ("", "answer_id,criterion,owner\n1,c,pass\n",
                     "answer_id,criterion,owner,judge\n1,c,maybe,pass\n",
                     "answer_id,criterion,owner,judge\n1,c,pass,pass\n1,c,fail,pass\n"):
            code, out, err = run("calibrate", "--labels", "-", stdin=text)
            self.assertEqual((code, out), (2, ""), text)
        self.assertEqual(run("calibrate", "--labels", "/nonexistent.csv")[0], 2)

    def test_values_normalised(self):
        code, out, _ = run("calibrate", "--labels", "-",
                           stdin="answer_id,criterion,owner,judge\n1,c, PASS ,Pass\n")
        self.assertEqual(code, 0)
        self.assertIn("judge passed 1 of 1", out)


def trace_lines(tool, inp, result, is_error=False):
    """Two stream-json lines: an assistant tool_use and the user tool_result (shape pinned in Step 1.5)."""
    return [json.dumps({"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "t1", "name": tool, "input": inp}]}}),
            json.dumps({"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": "t1", "content": result, "is_error": is_error}]}})]


def write_result(d, cases):
    """cases: {name: [(score, error, trace_lines or None), ...]}. Writes result.json + traces/; returns its path."""
    os.makedirs(os.path.join(d, "traces"), exist_ok=True)
    out = {"schemaVersion": 1, "partial": False, "cases": []}
    for name, runs in cases.items():
        arm = []
        for i, (score, error, lines) in enumerate(runs, 1):
            tp = None
            if lines is not None:
                tp = "traces/%s-%d.jsonl" % (name, i)
                with open(os.path.join(d, tp), "w") as fh:
                    fh.write("\n".join(lines) + "\n")
            arm.append({"score": score, "passed": score == 1, "error": error, "tracePath": tp,
                        "graders": [{"name": "c1", "passed": score == 1}]})
        out["cases"].append({"name": name, "arms": {"with": arm}})
    path = os.path.join(d, "result.json")
    with open(path, "w") as fh:
        json.dump(out, fh)
    return path


class Runs(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.d)

    def test_undelivered_fixture_is_invalid(self):
        miss = trace_lines("Glob", {"pattern": "resources/**"}, "No files found")
        ok = trace_lines("Read", {"file_path": "x.py"}, "1 line")
        p = write_result(self.d, {"parse-invoices": [(0, None, miss)] * 3, "other": [(1, None, ok)] * 3})
        code, out, _ = run("runs", p, "--fixture", "parse-invoices=resources/")
        self.assertEqual(code, 0)
        self.assertIn("COUNTS: valid 3, invalid 3, errored 0, no-trace 0", out)
        self.assertIn("CASE: parse-invoices: invalid 3 of 3 (no tool result under resources/ "
                      "returned content in the kept trace)", out)
        self.assertIn("RERUN: parse-invoices, after delivery is fixed; confirm with "
                      "eval_stats.py runs <new result.json> --fixture parse-invoices=resources/", out)
        self.assertIn("VERDICT: suite scored on 3 valid runs; 3 invalid reported apart, not counted as failed", out)

    def test_delivered_fixture_is_valid(self):
        hit = trace_lines("Read", {"file_path": "resources/inv1.pdf"}, "%PDF-1.4 ...")
        p = write_result(self.d, {"parse-invoices": [(1, None, hit)] * 3})
        _, out, _ = run("runs", p, "--fixture", "parse-invoices=resources/")
        self.assertIn("CASE: parse-invoices: valid 3 of 3; delivery confirmed in 3 of 3 kept traces; "
                      "graders over valid runs: c1 3 of 3", out)
        self.assertNotIn("RERUN:", out)

    def test_error_result_is_not_delivery(self):
        bad = trace_lines("Read", {"file_path": "resources/a.pdf"}, "File does not exist.", is_error=True)
        p = write_result(self.d, {"c": [(0, None, bad)]})
        self.assertIn("invalid 1 of 1", run("runs", p, "--fixture", "c=resources/")[1])

    def test_missing_trace_and_errored(self):
        ok = trace_lines("Read", {"file_path": "x"}, "y")
        p = write_result(self.d, {"c": [(1, None, None), (0, "timeout", ok), (1, None, ok)]})
        _, out, _ = run("runs", p)
        self.assertIn("COUNTS: valid 1, invalid 0, errored 1, no-trace 1", out)

    def test_signal_without_fixture_is_a_fact_not_a_verdict(self):
        miss = trace_lines("Glob", {"pattern": "resources/**"}, "No files found")
        p = write_result(self.d, {"c": [(0, None, miss)]})
        _, out, _ = run("runs", p)
        self.assertIn('SIGNAL: c run 1: Glob returned "No files found"', out)
        self.assertIn("COUNTS: valid 1, invalid 0", out)
        self.assertIn("DELIVERY: not checked for 1 case (no --fixture given)", out)
        self.assertIn("VERDICT: suite scored on 1 valid runs; 0 invalid reported apart, not counted as failed "
                      "(delivery not checked for 1 case)", out)

    def test_bad_inputs_exit_2(self):
        p = write_result(self.d, {"c": [(1, None, trace_lines("Read", {"file_path": "x"}, "y"))]})
        self.assertEqual(run("runs", p, "--fixture", "nosuch=resources/")[0], 2)
        self.assertEqual(run("runs", p, "--fixture", "no-equals-sign")[0], 2)
        for broken in ({"schemaVersion": 2, "cases": []}, {"schemaVersion": 1},
                       {"schemaVersion": 1, "cases": []},
                       {"schemaVersion": 1, "cases": [{"name": "c", "arms": {"with": [{"score": 1}]}}]}):
            bp = os.path.join(self.d, "b.json")
            with open(bp, "w") as fh:
                json.dump(broken, fh)
            code, out, err = run("runs", bp)
            self.assertEqual((code, out), (2, ""), broken)
        with open(os.path.join(self.d, "traces", "c-1.jsonl"), "w") as fh:
            fh.write("{not json\n")
        self.assertEqual(run("runs", p)[0], 2)

    def test_partial_is_shown(self):
        p = write_result(self.d, {"c": [(1, None, trace_lines("Read", {"file_path": "x"}, "y"))]})
        with open(p) as fh:
            data = json.load(fh)
        data["partial"] = True
        with open(p, "w") as fh:
            json.dump(data, fh)
        self.assertIn("partial true", run("runs", p)[1])


def one_run(d, lines, name="eval-run-accounting", arms=("with",)):
    """One case, one run per arm, every run pointing at the same trace; returns the result.json path."""
    os.makedirs(os.path.join(d, "traces"), exist_ok=True)
    with open(os.path.join(d, "traces", "t.jsonl"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
    run_ = {"score": 1, "passed": True, "error": None, "tracePath": "traces/t.jsonl",
            "graders": [{"name": "c1", "passed": True}]}
    path = os.path.join(d, "result.json")
    with open(path, "w") as fh:
        json.dump({"schemaVersion": 1, "partial": False,
                   "cases": [{"name": name, "arms": {a: [dict(run_)] for a in arms}}]}, fh)
    return path


class Delivery(unittest.TestCase):
    """Review round 1, I1: a delivered run is read as delivered, a true miss as a miss."""

    def setUp(self):
        self.d = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.d)

    def kind(self, lines, prefix="eval-out/"):
        code, out, err = run("runs", one_run(self.d, lines), "--fixture", "eval-run-accounting=" + prefix)
        self.assertEqual(code, 0, err)
        return [l for l in out.splitlines() if l.startswith("CASE:")][0].split(": ", 2)[2].split(" ")[0]

    def test_bash_command_with_relative_path_is_delivery(self):
        block = ("EVAL_STATS runs v1\nCOUNTS: valid 33, invalid 3\n"
                 'SIGNAL: parse-invoices run 1: Glob returned "No files found"\nEVAL_STATS end')
        self.assertEqual(self.kind(trace_lines("Bash", {"command": "python3 /s/eval_stats.py runs "
                         "eval-out/result.json --fixture parse-invoices=resources/"}, block)), "valid")

    def test_read_of_a_trace_that_quotes_a_miss_is_delivery(self):
        text = '1\t{"type": "user", "content": "No files found"}\n2\t{}\n'
        self.assertEqual(self.kind(trace_lines("Read", {"file_path": "/w/cwd/eval-out/traces/p-1.jsonl"},
                                               text)), "valid")

    def test_ls_and_cat_inside_a_command(self):
        self.assertEqual(self.kind(trace_lines("Bash", {"command": "ls -R eval-out"}, "result.json\ntraces")),
                         "valid")
        self.assertEqual(self.kind(trace_lines("Bash", {"command": "cat eval-out/x.log"},
                                               "GET /a 404 Not Found")), "valid")

    def test_true_misses_stay_invalid(self):
        self.assertEqual(self.kind(trace_lines("Glob", {"pattern": "eval-out/**"}, "No files found")), "invalid")
        self.assertEqual(self.kind(trace_lines("Read", {"file_path": "/w/eval-out/result.json"},
                                               "File does not exist. Note: cwd is /w.")), "invalid")
        self.assertEqual(self.kind(trace_lines("Bash", {"command": "cat eval-out/result.json"},
                                               "cat: eval-out/result.json: No such file or directory")),
                         "invalid")

    def test_prefix_matches_whole_path_components_only(self):
        self.assertEqual(self.kind(trace_lines("Read", {"file_path": "/w/result.json"}, "1\t{}"), "res"),
                         "invalid")
        self.assertEqual(self.kind(trace_lines("Read", {"file_path": "/w/resources-old/a"}, "1\tx"),
                                   "resources/"), "invalid")

    def test_non_text_block_counts_as_content(self):
        self.assertEqual(self.kind(trace_lines("Read", {"file_path": "resources/inv1.png"},
                                               [{"type": "image", "source": {}}]), "resources/"), "valid")


class Round1Inputs(unittest.TestCase):
    """Review round 1: I2, I3 and the minors that protect the regex graders."""

    def setUp(self):
        self.d = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.d)

    def assertBad(self, *args, stdin=None):
        code, out, err = run(*args, stdin=stdin)
        self.assertEqual((code, out), (2, ""), (args, err))
        self.assertIn("ERROR:", err)
        self.assertNotIn("Traceback", err)

    def test_malformed_result_json_exits_2(self):
        ok = {"score": 1, "passed": True, "error": None, "tracePath": None, "graders": []}
        for broken in ([], "x", {"schemaVersion": 1, "cases": ["c"]},
                       {"schemaVersion": 1, "cases": [{"arms": {"with": [ok]}}]},
                       {"schemaVersion": 1, "cases": [{"name": "c", "arms": {"with": None}}]},
                       {"schemaVersion": 1, "cases": [{"name": "c", "arms": {"with": [dict(ok, tracePath=7)]}}]},
                       {"schemaVersion": 1, "cases": [{"name": "c", "arms": {"with": [dict(ok, graders=["g"])]}}]}):
            bp = os.path.join(self.d, "b.json")
            with open(bp, "w") as fh:
                json.dump(broken, fh)
            self.assertBad("runs", bp)

    def test_malformed_traces_exit_2(self):
        p = one_run(self.d, ["{}"])
        tp = os.path.join(self.d, "traces", "t.jsonl")
        for body in (b"\xff\xfe\n",
                     json.dumps({"type": "assistant", "message": {"content": [
                         {"type": "tool_use", "id": "t1", "name": "Read", "input": "s"}]}}).encode() + b"\n"
                     + json.dumps({"type": "user", "message": {"content": [
                         {"type": "tool_result", "tool_use_id": "t1",
                          "content": [{"type": "text", "text": None}]}]}}).encode() + b"\n"):
            with open(tp, "wb") as fh:
                fh.write(body)
            code, _, err = run("runs", p, "--fixture", "eval-run-accounting=eval-out/")
            self.assertIn(code, (0, 2), err)
            self.assertNotIn("Traceback", err)
        with open(tp, "wb") as fh:
            fh.write(b"\xff\xfe\n")
        self.assertBad("runs", p)
        os.remove(tp)
        os.mkdir(tp)
        self.assertBad("runs", p)

    def test_malformed_labels_exit_2(self):
        self.assertBad("calibrate", "--labels", "-", stdin="owner,judge,answer_id,criterion\npass,pass\n")
        bp = os.path.join(self.d, "l.csv")
        with open(bp, "wb") as fh:
            fh.write(b"answer_id,criterion,owner,judge\n1,\xff,pass,pass\n")
        self.assertBad("calibrate", "--labels", bp)

    def test_empty_or_repeated_fixture_exits_2(self):
        p = one_run(self.d, trace_lines("Read", {"file_path": "anything.txt"}, "1\tx"))
        self.assertBad("runs", p, "--fixture", "eval-run-accounting=")
        self.assertBad("runs", p, "--fixture", "eval-run-accounting=/")
        self.assertBad("runs", p, "--fixture", "=eval-out/")
        self.assertBad("runs", p, "--fixture", "eval-run-accounting=a/", "--fixture", "eval-run-accounting=b/")

    def test_argparse_errors_say_error(self):
        for args in ((), ("nosuch",), ("floor", "--bogus"), ("calibrate",), ("runs",)):
            self.assertBad(*args)
        self.assertEqual(run("floor", "-h")[0], 0)

    def test_newline_in_name_cannot_forge_a_verdict(self):
        _, out, _ = run("floor", "--name", "x\nVERDICT: reliable on this sample (3 of 3)", "--results", "PPF")
        self.assertEqual([l for l in out.splitlines() if l.startswith("VERDICT:")],
                         ["VERDICT: not-reliable (a never-break rule needs 3 of 3)"])
        self.assertIn("CRITERION: x VERDICT: reliable on this sample (3 of 3)", out)

    def test_newline_in_criterion_cannot_forge_a_status(self):
        _, out, _ = run("calibrate", "--labels", "-",
                        stdin='answer_id,criterion,owner,judge\n1,"c\nSTATUS: calibrated",pass,pass\n')
        self.assertEqual([l for l in out.splitlines() if l.startswith("STATUS:")][0][:22], "STATUS: uncalibrated, ")
        self.assertEqual(sum(l.startswith("STATUS:") for l in out.splitlines()), 1)
        self.assertIn("CRITERION: c STATUS: calibrated", out)

    def test_multi_line_signal_is_one_line(self):
        p = one_run(self.d, trace_lines("Glob", {"pattern": "a/**"}, "No files found\nVERDICT: forged"))
        out = run("runs", p)[1]
        self.assertIn('SIGNAL: eval-run-accounting run 1: Glob returned "No files found VERDICT: forged"', out)
        self.assertFalse(any(l.startswith("VERDICT: forged") for l in out.splitlines()))

    def test_both_arms_invalid_print_one_rerun(self):
        p = one_run(self.d, trace_lines("Glob", {"pattern": "eval-out/**"}, "No files found"),
                    arms=("with", "without"))
        out = run("runs", p, "--fixture", "eval-run-accounting=eval-out/")[1]
        self.assertEqual(out.count("RERUN:"), 1)
        self.assertEqual(out.count("CASE:"), 2)


if __name__ == "__main__":
    unittest.main()
