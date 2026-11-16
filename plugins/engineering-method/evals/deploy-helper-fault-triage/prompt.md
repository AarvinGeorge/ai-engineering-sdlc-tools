---
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---

We are rehearsing release R-06 of the Acme billing service on the bench (a production-shaped copy, no real users). Our rule so far: every bench stop goes back through a pull request and a cross-model review before the bench re-runs. This is the 7th bench stop this release; six of them were in helper scripts, not in the product.

Today's bench run:

```
step 1  preconditions   check_disk.sh                      OK
step 2  backup          pg_dump + restore-read-back         OK
step 3  measure         count_open_invoices.sh              FAILED
        awk: syntax error at source line 1
        context is  {print $>>>  3 <<<}
        (the script runs `psql -c "SELECT count(*) FROM invoices WHERE status='open'"`
         and parses the output with awk; it only reads)
step 4..9 not run
```

Last week's run of the same file also stopped at:

```
step 8  migrate         apply_migration.sh 0042             FAILED
        ERROR: canceling statement due to lock timeout
        (writes the schema: adds a column and backfills it)
```

How should we handle each of these, and how do we stop the bench being eaten by helper faults?
