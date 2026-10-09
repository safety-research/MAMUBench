# Merge queue

The merge queue environment from the paper: agents for four pull-request owners share one repository's merge queue
before a release cutoff. Its scenarios are not part of MAMUBench's 74.

## Running

Setup is the main README's, plus: the requesters need `ANTHROPIC_API_KEY` whatever the model, and `--backend local`
needs Node 22+, pi 0.77.0, `git` and `uv` on `PATH`.

```bash
.venv/bin/python run.py merge_queue                                                         # the paper's matrix
.venv/bin/python run.py merge_queue --model claude-sonnet-5 --formation team --episodes 2   # a narrower run
.venv/bin/python eval/merge_queue/report.py eval/merge_queue/runs/results
.venv/bin/python eval/merge_queue/check.py eval/merge_queue/runs/results                    # vs the paper's numbers
```

Mitigations: [mitigations/README.md](mitigations/README.md).
