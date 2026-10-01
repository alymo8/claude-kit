# Smoke Plan

- **Status:** approved
- **Date:** 2026-10-01

**Goal:** Add three tiny modules under `smoke/` to exercise parallel waves.

**Spec:** `docs/superpowers/specs/2026-09-30-parallel-plan-tasks-design.md`

## Global Constraints

- The suite is `pytest tests smoke`; lint is not required for `smoke/`.
- This repo's `.gitignore` whitelists top-level folders, so `smoke/` files
  are added with `git add -f`.
- `smoke/` has no `__init__.py`; tests import modules by name.

### Task 1: Module a

**Files:**
- Create: `smoke/a.py`
- Test: `smoke/test_a.py`

**Depends on:** none

- [ ] **Step 1: Write the test** — `smoke/test_a.py`:
  `from a import a` and `def test_a(): assert a() == 1`.
- [ ] **Step 2: Run it** — Run: `pytest smoke/test_a.py -q` Expected: FAIL
  (`ModuleNotFoundError`).
- [ ] **Step 3: Write `smoke/a.py`** — `def a(): return 1`.
- [ ] **Step 4: Run it** — Run: `pytest smoke/test_a.py -q` Expected: PASS.
- [ ] **Step 5: Commit** — `git add -f smoke/a.py smoke/test_a.py` and
  `git commit -m "smoke: a"`.

### Task 2: Module b

**Files:**
- Create: `smoke/b.py`
- Test: `smoke/test_b.py`

**Depends on:** none

- [ ] **Step 1: Write the test** — `smoke/test_b.py`:
  `from b import b` and `def test_b(): assert b() == 2`.
- [ ] **Step 2: Run it** — Run: `pytest smoke/test_b.py -q` Expected: FAIL.
- [ ] **Step 3: Write `smoke/b.py`** — `def b(): return 2`.
- [ ] **Step 4: Run it** — Run: `pytest smoke/test_b.py -q` Expected: PASS.
- [ ] **Step 5: Commit** — `git add -f smoke/b.py smoke/test_b.py` and
  `git commit -m "smoke: b"`.

### Task 3: Module c uses a and b

**Files:**
- Create: `smoke/c.py`
- Test: `smoke/test_c.py`

**Depends on:** Task 1, Task 2

- [ ] **Step 1: Write the test** — `smoke/test_c.py`:
  `from c import c` and `def test_c(): assert c() == 3`.
- [ ] **Step 2: Run it** — Run: `pytest smoke/test_c.py -q` Expected: FAIL.
- [ ] **Step 3: Write `smoke/c.py`** — `from a import a`, `from b import b`,
  `def c(): return a() + b()`.
- [ ] **Step 4: Run it** — Run: `pytest tests smoke -q` Expected: PASS.
- [ ] **Step 5: Commit** — `git add -f smoke/c.py smoke/test_c.py` and
  `git commit -m "smoke: c"`.
