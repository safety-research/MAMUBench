# Third-party notices

This repository is released under the MIT License (see [LICENSE](LICENSE)). It
also carries, or runs against, the third-party software listed below. The
remaining Python dependencies are declared in `pyproject.toml`, installed from
PyPI, and carry their own licenses.

## 1. Jinja 3.1.4 (test fixture, modified copy)

- Where: `eval/merge_queue/environment/fixture/jinja/` (the merge-queue eval's
  fixture repository; `src/jinja2/__init__.py` reports `__version__ = "3.1.4"`).
- Modifications: this is a modified copy of Jinja, not a redistribution of the
  upstream release. The checked-in tree is a subset of the Jinja2 3.1.4 sdist
  (`docs/`, `requirements/`, `tox.ini` and `PKG-INFO` are omitted; the files
  that remain are unchanged). At run time
  `eval/merge_queue/environment/fixture/builder.py` copies it into a Git
  repository, overlays the files in `fixture/repo_files/` (a `CHANGES.rst`, stub
  docs, a CI workflow and similar project files written for this eval, not taken
  from upstream), and applies the patches in `fixture/patches/`, which add a
  deliberately buggy change, and its fix, to each simulated pull request.
- Upstream: the Pallets project, https://github.com/pallets/jinja
- License: BSD-3-Clause, reproduced verbatim from the fixture's `LICENSE.txt`:

```text
Copyright 2007 Pallets

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

1.  Redistributions of source code must retain the above copyright
    notice, this list of conditions and the following disclaimer.

2.  Redistributions in binary form must reproduce the above copyright
    notice, this list of conditions and the following disclaimer in the
    documentation and/or other materials provided with the distribution.

3.  Neither the name of the copyright holder nor the names of its
    contributors may be used to endorse or promote products derived from
    this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

## 2. pi coding agent (`@earendil-works/pi-coding-agent` 0.77.0)

- How it is used: the real-pi harness (`--harness pi`) drives pinned pi 0.77.0
  processes in `--mode rpc` (`eval/_harness/pi_rpc.py`, `runner.py`; the Modal
  image and `eval/_harness/Dockerfile` pin the same version). pi is not
  vendored; it is installed from npm at run time.
- Mirrored text: `eval/_harness/_multiagent_pi/pi_exact.py` reproduces pi's
  assembled system prompt and the JSON schemas of its four built-in tools
  (`read`, `bash`, `edit`, `write`), captured from a real pi session, so that
  the simulated target sees the same framing as a real pi seat. That file's
  docstring records that it is generated output and must not be edited by hand.
  The test fixtures in `eval/personal_assistant/tests/fixtures/probe_prompts/`
  are system prompts pi 0.77.0 assembled for four seats (see that directory's
  `README.md` for the substitutions made).
- Upstream: https://github.com/earendil-works/pi (directory
  `packages/coding-agent`); author Mario Zechner.
- License: MIT. The npm package ships no separate LICENSE file; the upstream
  repository's `LICENSE` reads:

```text
MIT License

Copyright (c) 2025 Mario Zechner

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 3. Petri and the vendored auditing runtime

- Where: `eval/_harness/_multiagent_pi/petri/` (the part of Petri's target
  runtime the released runs use: the channel between the auditor seat and each
  target, the target agent, trajectory recording, and the text rendering of a
  target turn; it carries no version string), `eval/_harness/_multiagent_pi/`
  and `eval/_harness/_eval_runner.py` (the multi-agent audit runtime the evals
  import). They are derived from a fork of the upstream Petri project built on
  `inspect_ai`; that fork is not released.
- Not a dependency: no `inspect-petri` release on PyPI matches this code. The
  closest that installs with `inspect_ai` 0.3.233 (3.0.10) has no
  empty-response retry, so an empty response would reach the target as an empty
  turn, and it would add packages nothing here uses.
- Upstream: https://github.com/meridianlabs-ai/inspect_petri
- License: MIT. The upstream project's `LICENSE` reads:

```text
MIT License

Copyright (c) 2025 Kai Fronsdal
Copyright (c) 2026 Meridian Labs

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 4. Inspect AI (`inspect_ai` 0.3.233)

- How it is used: a declared dependency (`pyproject.toml`), installed from PyPI;
  not vendored. The vendored runtime above and the simulated harness are built
  on it.
- Upstream: UK AI Security Institute, https://inspect.aisi.org.uk/
- License: MIT License (per the installed distribution's `METADATA`).
