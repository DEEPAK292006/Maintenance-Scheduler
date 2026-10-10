# Maintenance Scheduler: Capacity-Constrained Preventive Maintenance and Asset Replacement Prioritization

A robust, dependency-free Python engineering system designed to track equipment fleets, calculate preventive maintenance dates, detect overdue machinery, triage candidates for capital replacement, and construct capacity-constrained maintenance schedules using **Earliest Deadline First (EDF)** priority queues.

Developed with clean architecture, strict object-oriented design, comprehensive automated tests, and proven $O(N \log N)$ scalability capable of scheduling **100,000 assets in ~4.3 seconds**.

---

## 1. Project Overview & Problem Statement

Modern manufacturing plants, transport fleets, and industrial facilities manage tens of thousands of operating assets. Each machine requires periodic servicing based on an operating interval. However, real-world maintenance operations face two major challenges:

1. **Finite Technician Capacity**: A facility cannot service an infinite number of machines in a single day. Daily technician bandwidth is capped at $C$ service slots.
2. **Degraded Equipment & Replacement Triaging**: Aging equipment with frequent historical breakdowns drains maintenance resources. Machines with repeated failures must be flagged for replacement, and those with higher failure intensities must be prioritized.

This system solves both challenges by ingesting asset registries, detecting overdue and near-deadline tasks, prioritizing replacement candidates using failure-rate heuristics, and generating a conflict-free daily service roster that minimizes delays using an EDF priority queue.

---

## 2. Key Features

- **Feature A: Custom Date Utilities (`date_utils.py`)**
  - Strict ISO-8601 `YYYY-MM-DD` validation and calendar parsing without external libraries.
  - Safe leap-year arithmetic and month/year boundary rollover handling.
  - Exact calculation of due dates, overdue durations, and days remaining.
- **Feature B: Asset Management Domain Model (`models.py`, `asset_manager.py`)**
  - Encapsulated `Asset` entity with computed properties preventing data inconsistency.
  - Efficient filtering and deterministic sorting by `(next_due_date, asset_id)`.
- **Feature C: Overdue Maintenance Detection**
  - Identifies all assets where `next_due_date < today`.
  - Deterministically ordered output in standard format: `OVERDUE <asset_id> <N> days`.
- **Feature D: Replacement Triaging & Urgency Prioritization (`replacement_analyzer.py`)**
  - Eligibility threshold: historical repairs $\ge 3$.
  - Generates standard output: `REPLACE <asset_id>`.
  - Estimates failure intensity (repairs/year) with minimum observation window clamping.
  - Ranks candidates by an urgency score combining failure rate and overdue status.
- **Feature E: Capacity-Constrained EDF Scheduler (`scheduler.py`)**
  - Implements Jackson's Earliest Deadline First heuristic using a min-heap (`heapq`).
  - Enforces daily technician bandwidth ($C$ assets/day).
  - Employs $O(1)$ forward pointer date allocation (no calendar loop overhead).
  - Computes exact Total Lateness and Maximum Lateness ($L_{\max}$).
- **Feature F: 30-Day Lookahead Report (`reports.py`)**
  - Identifies equipment due in the window $[today, today + 30\text{ days}]$.
- **Feature G: High-Performance Scalability (`benchmarks/benchmark_100k.py`)**
  - Benchmarked with 100,000 assets in **4.35 seconds** and only **36.5 MB** peak RAM.

---

## 3. Technology Stack & Prerequisites

- **Language**: Python 3.10+ (tested on Python 3.14 on Windows 11).
- **Dependencies**: Zero third-party dependencies (`requirements.txt` is empty).
- **Standard Library Modules**:
  - `datetime`: Calendar arithmetic (`date`, `timedelta`).
  - `heapq`: Binary min-heap priority queue implementation.
  - `unittest`: Automated unit test framework.
  - `argparse`: Command-line interface argument parsing.
  - `pathlib`: Cross-platform filesystem path resolution.
  - `tracemalloc`: Memory profiler for benchmarks.
  - `time`: High-resolution performance timer (`time.perf_counter`).
  - `typing`, `dataclasses`: Type safety and structured data containers.

---

## 4. Project Folder Structure

```
maintenance_scheduler/
│
├── main.py                     # CLI entry point coordinating pipeline & reports
├── models.py                   # Domain models (Asset, ScheduledService, ScheduleResult)
├── date_utils.py               # Pure date parsing, intervals, and comparison utilities
├── asset_manager.py            # High-level collection filtering and query logic
├── scheduler.py                # Capacity-constrained EDF min-heap scheduler
├── replacement_analyzer.py     # Replacement candidate detection & urgency ranking
├── reports.py                  # Terminal formatters & tabular report generators
├── input_handler.py            # Streaming input parser with strict validation
├── config.py                   # Default operational settings and parameter dataclass
│
├── tests/                      # Automated unit test suite (42 tests, 100% pass)
│   ├── __init__.py
│   ├── test_date_utils.py
│   ├── test_asset_manager.py
│   ├── test_scheduler.py
│   ├── test_replacement_analyzer.py
│   └── test_input_validation.py
│
├── benchmarks/                 # Scalability benchmarking suite
│   ├── __init__.py
│   └── benchmark_100k.py
│
├── data/
│   └── sample_input.txt        # Verified sample dataset
│
├── README.md                   # Comprehensive project documentation
└── requirements.txt            # Zero-dependency specification
```

---

## 5. Input Format & Validation Rules

### Input Specification
```
<today_date: YYYY-MM-DD>
<number_of_assets: n>
<asset_id_1> <interval_days_1> <last_service_date_1> <repairs_1>
<asset_id_2> <interval_days_2> <last_service_date_2> <repairs_2>
...
<asset_id_n> <interval_days_n> <last_service_date_n> <repairs_n>
```

### Validation Rules & Error Handling
1. **Date Validation**: Both `today` and `last_service_date` must conform to `YYYY-MM-DD` and represent a real calendar date (e.g., `2026-02-29` is rejected because 2026 is not a leap year).
2. **Asset Count ($n$)**: Line 2 must be an integer $n \ge 0$.
3. **Record Token Count**: Exactly 4 space-separated tokens per asset line.
4. **Service Interval**: Must be an integer $> 0$.
5. **Historical Repairs**: Must be an integer $\ge 0$.
6. **Asset ID Uniqueness**: Duplicate asset IDs are rejected immediately.
7. **Premature EOF**: If the input terminates before $n$ records, an informative error is raised.

---

## 6. Mathematical & Algorithmic Explanations

### A. Next Due Date Calculation
$$\text{next\_due\_date} = \text{last\_service\_date} + \text{timedelta}(\text{interval\_days})$$
- Evaluated cleanly using calendar day offsets that automatically adjust for month lengths (28, 29, 30, 31) and leap years.

### B. Overdue Maintenance Logic
$$\text{is\_overdue} = \text{next\_due\_date} < \text{today}$$
$$\text{days\_overdue} = (\text{today} - \text{next\_due\_date}).\text{days} \quad (\text{if overdue, else } 0)$$
- **Rule**: An asset due today ($\text{next\_due\_date} == \text{today}$) is classified as **due today**, not overdue.

### C. Replacement Eligibility & Urgency Prioritization
1. **Eligibility Threshold**:
   $$\text{eligible} \iff \text{repairs} \ge 3$$
2. **Observation Period Proxy**:
   The input format records repair counts and `last_service_date`, but lacks asset age. We use elapsed time from `last_service_date` to `today` as an explicit proxy window:
   $$\text{obs\_days} = \max((\text{today} - \text{last\_service\_date}).\text{days},\; \text{min\_observation\_days})$$
   $$\text{obs\_years} = \frac{\text{obs\_days}}{365.0}$$
   $$\text{failure\_rate} = \frac{\text{repairs}}{\text{obs\_years}} \quad [\text{repairs/year}]$$
   *Note*: A minimum floor of 30 days is enforced to avoid division by zero or inflated rates for equipment serviced recently.
3. **Urgency Score**:
   To rank which replacement candidates need immediate attention:
   $$\text{urgency\_score} = \text{failure\_rate} \times (1.5 \text{ if overdue else } 1.0) + \frac{\text{days\_overdue}}{30.0}$$
   Candidates are sorted by:
   $$\text{urgency\_score (descending)} \longrightarrow \text{next\_due\_date (ascending)} \longrightarrow \text{asset\_id (alphabetical)}$$

### D. Capacity-Constrained Earliest Deadline First (EDF) Scheduling
- **Heuristic**: When scheduling tasks with deadlines, **Earliest Deadline First (EDF)** prioritizes the most imminent deadlines first. By Jackson's Rule (1955), EDF minimizes maximum lateness ($L_{\max}$) for single-machine systems with static ready times.
- **Constraints**:
  - Capacity $C$: At most $C$ machines can be serviced on any single calendar date.
  - Release Date: Routine service cannot be scheduled before $\max(\text{today}, \text{next\_due\_date})$.
- **Monotonic $O(1)$ Pointer Allocation**:
  Because assets are popped from the min-heap in non-decreasing order of $\text{next\_due\_date}$, the target service dates $\tau_j = \max(\text{today}, \text{next\_due\_date}_j)$ are monotonically non-decreasing. By maintaining a forward calendar pointer `current_slot_date` and daily count `slot_usage`, we assign dates in $O(1)$ time without searching or iterating through empty calendar days.
- **Lateness Metrics**:
  $$\text{lateness}_i = \max(0,\; (\text{scheduled\_date}_i - \text{due\_date}_i).\text{days})$$
  $$\text{Total Lateness} = \sum_{i=1}^M \text{lateness}_i$$
  $$\text{Maximum Lateness } (L_{\max}) = \max_{1 \le i \le M} (\text{lateness}_i)$$
- **Heuristic vs. Global Optimality**:
  While EDF is optimal for minimizing $L_{\max}$ in simple unconstrained single-server models, minimizing total lateness under multi-capacity discrete days is generally NP-hard. EDF is therefore used as an efficient, deterministic, high-throughput heuristic.

---

## 7. How to Run the Program

### Running with Sample Input File
```powershell
python maintenance_scheduler/main.py maintenance_scheduler/data/sample_input.txt
```

**Standard Output**:
```
OVERDUE A101 42 days
REPLACE A102
```

### Running the Interactive Streamlit Web Dashboard
```powershell
streamlit run maintenance_scheduler/app.py
```
Or with Python:
```powershell
python -m streamlit run maintenance_scheduler/app.py
```
The web dashboard opens at `http://localhost:8501`, featuring:
- Live KPI cards, overdue queue, and replacement prioritization.
- Capacity-constrained timeline visualization and daily volume charts.
- File upload, text input, and live 100,000-asset benchmark execution directly in the browser!

### Running with Detailed Analytical Reports
```powershell
python maintenance_scheduler/main.py maintenance_scheduler/data/sample_input.txt --detailed
```

### Reading from Standard Input (stdin)
```powershell
Get-Content maintenance_scheduler/data/sample_input.txt | python maintenance_scheduler/main.py
```

### Configuring Daily Technician Capacity & Horizon
```powershell
# Set capacity to 2 assets/day, lookahead horizon to 30 days
python maintenance_scheduler/main.py maintenance_scheduler/data/sample_input.txt --capacity 2 --horizon 30 --detailed

# Schedule all assets without horizon cutoffs
python maintenance_scheduler/main.py maintenance_scheduler/data/sample_input.txt --all --detailed
```

---

## 8. Walkthrough of the Sample Dataset

### Sample Input (`data/sample_input.txt`)
```
2026-10-09
3
A101 180 2026-03-01 1
A102 90 2026-08-01 3
A103 365 2026-01-15 0
```

### Step-by-Step Verification:
1. **Asset A101**:
   - $\text{Last Service}: \text{2026-03-01}$, $\text{Interval}: 180\text{ days}$.
   - $\text{Next Due Date}: \text{2026-03-01} + 180 = \text{2026-08-28}$.
   - $\text{Today}: \text{2026-10-09}$.
   - $\text{Overdue Days}: \text{2026-10-09} - \text{2026-08-28} = 42\text{ days}$.
   - Output: `OVERDUE A101 42 days`.
2. **Asset A102**:
   - $\text{Last Service}: \text{2026-08-01}$, $\text{Interval}: 90\text{ days}$.
   - $\text{Next Due Date}: \text{2026-08-01} + 90 = \text{2026-10-30}$.
   - $\text{Repairs}: 3 \ge 3 \implies$ Replacement Candidate.
   - Output: `REPLACE A102`.
   - Days remaining until due: $\text{2026-10-30} - \text{2026-10-09} = 21\text{ days}$ (due within 30 days).
3. **Asset A103**:
   - $\text{Last Service}: \text{2026-01-15}$, $\text{Interval}: 365\text{ days}$.
   - $\text{Next Due Date}: \text{2027-01-15}$.
   - $\text{Repairs}: 0 < 3 \implies$ Not a replacement candidate; not overdue.

---

## 9. Automated Testing Suite

The project includes 42 automated unit tests across 5 test modules using Python's built-in `unittest` framework:

```powershell
python -m unittest discover -s maintenance_scheduler/tests -v
```

### Test Coverage Highlights:
- `test_date_utils.py`: Leap year handling (Feb 29), month-end and year rollovers, impossible dates (`2026-02-29`), due today vs overdue, 30-day boundaries.
- `test_asset_manager.py`: Overdue asset sorting, deterministic tie-breakers on identical due dates, 30-day lookahead filter.
- `test_replacement_analyzer.py`: Boundary verification at 2, 3, and 4 repairs, observation window clamping, urgency score ordering.
- `test_scheduler.py`: Daily capacity capping (1, 2, 5 assets/day), min-heap EDF dispatching, lateness calculations, invalid capacity rejection (`ValueError`).
- `test_input_validation.py`: Missing tokens, extra tokens, duplicate asset IDs, non-positive intervals, negative repairs, malformed dates.

**Execution Result**:
```
Ran 42 tests in 0.005s
OK
```

---

## 10. Performance Benchmark (100,000 Assets)

To verify real-world enterprise scalability, the project includes an automated benchmark generating 100,000 synthetic assets with randomized intervals, past service dates, and repair histories.

### Running the Benchmark:
```powershell
python maintenance_scheduler/benchmarks/benchmark_100k.py
```

### Actual Benchmark Results:
```
======================================================================
MAINTENANCE SCHEDULER PERFORMANCE BENCHMARK (N = 100,000 ASSETS)
======================================================================
Configuration:
  - Dataset Size           : 100,000 assets
  - Daily Capacity (C)     : 250 assets/day
  - Scheduling Horizon (H) : 60 days
  - Python Version         : 3.14.2
----------------------------------------------------------------------
[Phase 1] Asset generation & model instantiation : 2.4558 s
[Phase 2] Overdue detection & sorting (O(N log N)) : 0.2166 s (72,480 overdue)
[Phase 3] Replacement triaging & ranking           : 0.3170 s (24,982 candidates)
[Phase 4] Capacity-constrained EDF scheduling      : 1.3558 s (82,702 scheduled)
======================================================================
BENCHMARK EXECUTION RESULTS & METRICS
======================================================================
Total Wall-Clock Time          : 4.3454 seconds
Total Throughput               : 23,013.0 assets/second
Peak Memory Allocated          : 36.46 MB
Total Assets Processed         : 100,000
Overdue Assets Identified      : 72,480
Replacement Candidates Flagged : 24,982
Total Services Scheduled       : 82,702
Schedule Calendar Days Used    : 331 days
Aggregate Schedule Lateness    : 27,756,225 days
Maximum Asset Lateness (L_max) : 470 days
======================================================================
Status: BENCHMARK PASSED (O(N log N) processing verified under standard memory limits).
```

### Complexity Analysis:
| Operation | Time Complexity | Space Complexity | Notes |
| :--- | :--- | :--- | :--- |
| **Input Parsing & Validation** | $O(N)$ | $O(N)$ | Single-pass streaming validation |
| **Overdue Identification & Sort** | $O(N \log N)$ | $O(N)$ | Timsort deterministic ordering |
| **Replacement Analysis & Urgency** | $O(K \log K)$ | $O(K)$ | $K \le N$ replacement candidates |
| **EDF Min-Heap Initialization** | $O(M)$ | $O(M)$ | Bottom-up linear heapify ($M \le N$) |
| **EDF Extraction & Scheduling** | $O(M \log M)$ | $O(M)$ | Min-heap pops + $O(1)$ date pointer advancement |
| **Total System Pipeline** | $\mathbf{O(N \log N)}$ | $\mathbf{O(N)}$ | $\sim 23,000\text{ assets/sec}$ |

---

## 11. Known Assumptions & Future Improvements

1. **Failure Rate Proxy**:
   - The input schema records historical repairs and last service date, but not overall machine installation date. The elapsed window between last service and today is used as a heuristic proxy.
   - *Future Work*: Integrate full maintenance log timestamp streams or Weibull reliability models if full machine operational lifespans are supplied.
2. **Homogeneous Technician Skills**:
   - The scheduler assumes each service occupies 1 generic capacity slot.
   - *Future Work*: Extend to multi-skill technician routing with job duration variances ($p_j > 1$).
3. **Non-Preemption**:
   - Services assigned to a date cannot be split across multiple days.

---

## 12. Verification Checklist

- [x] Python only (.py files, Python 3.10+ standard library).
- [x] Zero external dependencies (empty `requirements.txt`).
- [x] Custom date utility (`date_utils.py`) with leap-year and boundary tests.
- [x] Asset model (`models.py`) with computed properties.
- [x] Overdue maintenance detection formatted as `OVERDUE <asset_id> <N> days`.
- [x] Replacement detection formatted as `REPLACE <asset_id>` for repairs $\ge 3$.
- [x] Failure rate calculation with minimum observation window.
- [x] Urgency ranking rule combining failure rate and overdue status.
- [x] Capacity-constrained EDF scheduler using `heapq` and daily capacity counters.
- [x] Total lateness and maximum lateness calculation.
- [x] Report of assets due within 30 days.
- [x] Input handler supporting files, stdin, and thorough input validation.
- [x] Sample input produces exact required outputs (`OVERDUE A101 42 days`, `REPLACE A102`).
- [x] 42 automated unit tests covering all required cases.
- [x] 100,000-asset performance benchmark measured in under 5 seconds.
- [x] Complete README documenting all aspects of the system.
