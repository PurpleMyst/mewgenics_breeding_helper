## Version 2.0.0 - ENS Architecture

### Major Changes

- New `mewgenics_breeding` package with PMF-based breeding simulation
- ENS (Expected Net Stats) scoring architecture replacing legacy math
- Universals & Target Builds system with OR-probability synergy calculations
- New room types: HEALTH and MUTATION for disorder/defect cats
- Room optimizer refactored with RoomAllocator and AnnealingWorker class
- Overview tab showing favorable trait distribution
- mewgenics_scorer refactored to use breeding package as backend
- KinshipManager replaced with pedigree blob CoI lookup

### Bug Fixes

- Class passive favoring now uses is_class_passive (was is_class_active)
- Build synergy calculation rewritten with proper OR-math
- Various UI fixes for room config and stimulation handling

---

## Version 2.0.1 - Bugfix Release

This is a bugfix release addressing a small issue:

- **Fix**: Resolve 0 breeding pairs bug by extracting CachingScorer
