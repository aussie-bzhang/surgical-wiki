"""
surgical_prolog_verifier.py
===========================
Verifies the SurgicalWiki Pro Prolog knowledge base (rules/surgical_rules.pl)
against a suite of named test goals.

Outputs:
  vault/_meta/prolog_report.json   -- machine-readable pass/fail report
  stdout                           -- human-readable summary table

Usage (Anaconda Prompt, from repo root L:\\medical\\surgical-wiki):
  python pipeline/surgical_prolog_verifier.py
  python pipeline/surgical_prolog_verifier.py --kb rules/surgical_rules.pl
  python pipeline/surgical_prolog_verifier.py --swipl "C:/Program Files/swipl/bin/swipl.exe"
  python pipeline/surgical_prolog_verifier.py --category drain
  python pipeline/surgical_prolog_verifier.py --fail-fast

Exit code 0 = all PASS, exit code 1 = one or more FAIL.
"""

import subprocess
import json
import os
import sys
import argparse
import time
from pathlib import Path
from datetime import datetime

# ----------------------------------------------------------------
# DEFAULT PATHS
# ----------------------------------------------------------------
DEFAULT_SWIPL  = r"C:\Program Files\swipl\bin\swipl.exe"
DEFAULT_KB     = "rules/surgical_rules.pl"
DEFAULT_REPORT = "vault/_meta/prolog_report.json"

# ----------------------------------------------------------------
# TEST SUITE
# (category, test_name, prolog_goal)
# Each goal is evaluated after consulting the KB.
# ----------------------------------------------------------------
TEST_SUITE = [

    # ---- ANATOMICAL PROTECTION RULES -------------------------
    ("anatomy", "bile_duct_cholecystectomy",
     "protect_structure(bile_duct, cholecystectomy)"),

    ("anatomy", "cbc_no_clamp",
     "\\+ clamp_allowed(common_bile_duct, _)"),

    ("anatomy", "portal_vein_hepatectomy",
     "protect_structure(portal_vein, hepatectomy)"),

    ("anatomy", "rln_thyroidectomy",
     "protect_structure(recurrent_laryngeal_nerve, thyroidectomy)"),

    ("anatomy", "ureter_colectomy",
     "protect_structure(ureter, colectomy)"),

    ("anatomy", "sma_right_hemicolectomy",
     "protect_structure(superior_mesenteric_artery, right_hemicolectomy)"),

    ("anatomy", "splenic_hilum_splenectomy",
     "protect_structure(splenic_hilum_vessels, splenectomy)"),

    # ---- PROCEDURAL SEQUENCING CONSTRAINTS -------------------
    ("sequence", "calot_before_division",
     "must_precede(dissect_calot_triangle, divide_cystic_duct, cholecystectomy)"),

    ("sequence", "resection_before_anastomosis",
     "must_precede(resection, anastomosis, _)"),

    ("sequence", "haemostasis_before_closure",
     "must_precede(achieve_haemostasis, close_abdomen, _)"),

    ("sequence", "specimen_before_ports",
     "must_precede(retrieve_specimen, remove_ports, laparoscopic_procedure)"),

    ("sequence", "bowel_prep_elective_colectomy",
     "must_precede(bowel_preparation, colonic_anastomosis, elective_colectomy)"),

    ("sequence", "consent_before_incision",
     "must_precede(informed_consent, skin_incision, _)"),

    ("sequence", "count_before_closure",
     "must_precede(instrument_count, close_abdomen, _)"),

    ("sequence", "label_before_dispatch",
     "must_precede(label_specimen, dispatch_to_pathology, _)"),

    # ---- ANASTOMOSIS STANDARDS -------------------------------
    ("anastomosis", "tension_free",
     "anastomosis_requirement(tension_free, _)"),

    ("anastomosis", "blood_supply",
     "anastomosis_requirement(adequate_blood_supply, _)"),

    ("anastomosis", "no_distal_obstruction",
     "anastomosis_requirement(no_distal_obstruction, _)"),

    ("anastomosis", "colorectal_air_leak_test",
     "anastomosis_test(air_leak_test, colorectal_anastomosis)"),

    ("anastomosis", "oesophageal_technique",
     "(anastomosis_technique(stapled, oesophagectomy) ; "
     " anastomosis_technique(handsewn, oesophagectomy))"),

    ("anastomosis", "billroth2_loop_orientation",
     "anastomosis_requirement(check_afferent_loop_orientation, billroth_ii)"),

    # ---- DRAIN INDICATIONS -----------------------------------
    ("drain", "drain_whipple",
     "drain_indicated(pancreaticoduodenectomy)"),

    ("drain", "drain_oesophagectomy",
     "drain_indicated(oesophagectomy)"),

    ("drain", "drain_hepatectomy",
     "drain_indicated(hepatectomy)"),

    ("drain", "no_mandatory_drain_chole",
     "\\+ drain_mandatory(cholecystectomy)"),

    ("drain", "no_mandatory_drain_inguinal",
     "\\+ drain_mandatory(inguinal_hernia_repair)"),

    ("drain", "drain_subhepatic_location",
     "drain_location(subhepatic, cholecystectomy_with_bile_leak_risk)"),

    # ---- COMPLICATION RISK CLASSIFICATION --------------------
    ("risk", "anastomotic_leak_lar_high",
     "complication_risk(anastomotic_leak, low_anterior_resection, high)"),

    ("risk", "bile_leak_hepatectomy_moderate",
     "complication_risk(bile_leak, partial_hepatectomy, moderate)"),

    ("risk", "pph_whipple_high",
     "complication_risk(post_pancreatectomy_haemorrhage, "
     "pancreaticoduodenectomy, high)"),

    ("risk", "wound_infection_contaminated_high",
     "complication_risk(wound_infection, contaminated_field, high)"),

    ("risk", "obesity_ssi_risk_factor",
     "risk_factor(obesity, surgical_site_infection)"),

    ("risk", "dvt_major_abdominal_moderate",
     "complication_risk(dvt, major_abdominal_surgery, moderate)"),

    # ---- PROCEDURAL CONTRAINDICATIONS ------------------------
    ("contraindication", "lap_severe_cardiopulmonary",
     "contraindication(laparoscopic_approach, severe_cardiopulmonary_disease)"),

    ("contraindication", "no_primary_closure_contaminated",
     "\\+ recommended(primary_closure, grossly_contaminated_wound)"),

    ("contraindication", "chole_coagulopathy_caution",
     "caution_required(cholecystectomy, uncorrected_coagulopathy)"),

    # ---- INTRAOPERATIVE PRINCIPLES ---------------------------
    ("principles", "antibiotic_60min",
     "antibiotic_timing(prophylactic, within_60_minutes_of_incision)"),

    ("principles", "normothermia",
     "intraoperative_goal(normothermia)"),

    ("principles", "vte_prophylaxis",
     "intraoperative_goal(vte_prophylaxis)"),
]

# ----------------------------------------------------------------
# PROLOG RUNNER
# ----------------------------------------------------------------

def run_goal(swipl_path, kb_path, goal):
    """
    Evaluate a Prolog goal against the KB.
    Fix: uses relative KB filename + cwd=kb_dir so that Unicode
    characters in the directory path never appear inside the
    Prolog script atom (avoids GBK/UTF-8 mismatch on Chinese Windows).
    Returns (passed: bool, elapsed_ms: float, error_msg: str).
    """
    import tempfile

    kb_dir      = os.path.dirname(kb_path)   # L:\医疗健康\surgical-wiki\rules
    kb_basename = os.path.basename(kb_path)  # surgical_rules.pl  (ASCII-only)

    # consult uses only the ASCII basename; CWD is set to kb_dir by subprocess
    # set_prolog_flag(unknown,fail): undefined predicates fail instead of throw
    # This makes \+ goals work correctly even if predicate has no clauses
    script = (
        ":- set_prolog_flag(unknown, fail).\n"
        ":- catch("
        "(consult('{kb}'), ({goal} -> halt(0) ; halt(1))),"
        "_E, halt(2)).\n"
    ).format(kb=kb_basename, goal=goal)


    t0 = time.perf_counter()

    # Temp file stays in system temp (pure-ASCII path) -- no Unicode in argv
    fd, tmp_path = tempfile.mkstemp(suffix=".pl")
    try:
        with os.fdopen(fd, "w", encoding="ascii") as fh:
            fh.write(script)
        proc = subprocess.run(
            [swipl_path, "-q", "--traditional", "-t", "halt", tmp_path],
            capture_output=True,
            text=True,
            timeout=20,
            cwd=kb_dir,   # Python sets CWD via Unicode Win32 API -- works fine
        )
    except FileNotFoundError:
        return False, 0.0, "swipl not found: " + swipl_path
    except subprocess.TimeoutExpired:
        return False, 20000.0, "timeout (20s)"
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    elapsed = (time.perf_counter() - t0) * 1000
    rc = proc.returncode
    if rc == 0:
        return True, elapsed, ""
    elif rc == 1:
        return False, elapsed, "goal FAILED (false or undefined predicate)"
    else:
        lines = proc.stderr.strip().splitlines()
        return False, elapsed, (lines[-1] if lines else "Prolog error rc=2")



# ----------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(
        description="SurgicalWiki Pro -- Prolog KB Verifier",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--swipl",      default=DEFAULT_SWIPL)
    p.add_argument("--kb",         default=DEFAULT_KB)
    p.add_argument("--report",     default=DEFAULT_REPORT)
    p.add_argument("--fail-fast",  action="store_true",
                   help="Stop on first failure")
    p.add_argument("--category",   default=None,
                   help="Run only tests in this category")
    args = p.parse_args()

    kb_path = str(Path(args.kb).resolve())
    if not Path(kb_path).exists():
        print("[ERROR] KB not found: " + kb_path)
        print("  Run from repo root or pass --kb <path>")
        sys.exit(1)

    suite = TEST_SUITE
    if args.category:
        suite = [t for t in TEST_SUITE if t[0] == args.category]
        if not suite:
            print("[ERROR] No tests for category: " + args.category)
            sys.exit(1)

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    W = 72
    print("=" * W)
    print("  SurgicalWiki Pro -- Prolog KB Verification")
    print("  KB   : " + kb_path)
    print("  swipl: " + args.swipl)
    print("  Tests: {n}".format(n=len(suite)))
    print("=" * W)

    results = []
    cat_counts = {}
    n_pass = n_fail = 0

    for (category, name, goal) in suite:
        passed, ms, err = run_goal(args.swipl, kb_path, goal)
        status = "PASS" if passed else "FAIL"
        print("[{s}] {cat:<20} {name:<40} ({ms:>5.0f}ms)".format(
            s=status, cat=category, name=name, ms=ms))
        if not passed:
            print("       goal : " + goal)
            print("       error: " + err)

        results.append({
            "category": category, "name": name, "goal": goal,
            "status": status, "elapsed_ms": round(ms, 1), "error": err,
        })
        cc = cat_counts.setdefault(category, {"pass": 0, "fail": 0})
        if passed:
            n_pass += 1
            cc["pass"] += 1
        else:
            n_fail += 1
            cc["fail"] += 1

        if args.fail_fast and not passed:
            print("\n[FAIL-FAST] stopping.")
            break

    total = n_pass + n_fail
    health = round(n_pass / total * 100, 1) if total else 0.0

    print("")
    print("=" * W)
    print("  CATEGORY SUMMARY")
    print("-" * W)
    for cat, cc in cat_counts.items():
        n = cc["pass"] + cc["fail"]
        bar = "#" * cc["pass"] + "." * cc["fail"]
        pct = round(cc["pass"] / n * 100) if n else 0
        print("  {cat:<22} {bar:<33} {p}/{n}  ({pct}%)".format(
            cat=cat, bar=bar, p=cc["pass"], n=n, pct=pct))
    print("-" * W)
    print("  TOTAL  {p}/{t} PASS   KB health = {h}%".format(
        p=n_pass, t=total, h=health))
    print("=" * W)

    verdict = "ALL PASS -- KB is clean." if n_fail == 0 else \
              "{f} FAILURE(S) -- add missing predicates to surgical_rules.pl".format(
                  f=n_fail)
    print("\n  " + verdict)

    report = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "kb_path": kb_path,
        "swipl_path": args.swipl,
        "total": total, "passed": n_pass, "failed": n_fail,
        "kb_health_pct": health,
        "category_summary": cat_counts,
        "tests": results,
    }
    with open(report_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=True)
    print("  Report -> " + str(report_path))

    sys.exit(0 if n_fail == 0 else 1)


if __name__ == "__main__":
    main()
