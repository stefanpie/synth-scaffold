<img src="./branding/logo_synthscaffold.svg" alt="SynthScaffold Logo" width="100%">
<hr>

**SynthScaffold** is a tool for synthesizing non-top-level functions to enable fast prototyping and debugging in high-level synthesis (HLS). It currently supports Vitis HLS and has been tested with Vitis HLS 2024.1.

**SynthScaffold** also allows for design space exploration by easily parameterizing the target function.


## Motivation

In complex hierarchical HLS designs, users often implement different parts of a design as separate functions, sometimes with template arguments. However, analyzing how these functions synthesize can be cumbersome. The common approaches—either synthesizing the entire design or manually creating a wrapper for each function—are time-consuming, error-prone, and require significant manual effort. This is especially true when a user wants to also explore the design space of a function by varying things like parallelism, buffer sizes, trip counts, and more.

## Solution

SynthScaffold streamlines this process by allowing users to synthesize individual functions without modifying the full design.

The tool works as follows:

1. The user specifies: the target function, source files to search, additional includes or defines, and template arguments (if needed)
2. SynthScaffold automatically generates a top-level wrapper that mirrors the target function’s arguments and template parameters.
3. It runs HLS synthesis on this wrapper and outputs a synthesis report.

Note 1: To model array arguments as on-chip buffers (1-cycle latency), SynthScaffold uses the Vivado flow for HLS synthesis, eliminating the need to scaffold internal buffer arrays and copy data between the top-level wrapper args and internal buffer arrays.

Note 2: To ensure that the target function is scaffolded correctly, the `#pragma HLS INLINE off` directive should be added to the target function. SynthScaffold will automatically add this directive to the synthesis script as well but it is good practice for the user to also add the pargma explicitly to the source code of the target function.

## Installation

```bash
pip install git+https://github.com/stefanpie/synth-scaffold
```

```bash
uv add git+https://github.com/stefanpie/synth-scaffold
```

## Examples

### Example 1: Synthesizing a Simple Function

Lets say I have the following target function I would like to synthesize located in `design_sources/activation_functions.h`:

```cpp
// <other code...>

template <typename T>
T activation_tanh(T x) {
#pragma HLS INLINE off
#pragma HLS PIPELINE
    if constexpr (is_ap_fixed_v<T>) {
        T out = hls::tanh(x);
        T out_fixed = (hls::signbit(x) != hls::signbit(out)) ? T(-out) : out;
        return out_fixed;
    } else {
        return std::tanh(x);
    }
}

// <other code...>
```

I can setup SynthScaffold to synthesize this function as follows:

```python
from synth_scaffold import SynthScaffold, SynthReport, unwrap

DIR_CURRENT = Path(__file__).parent
input_source_files = [
    *(DIR_CURRENT / "design_sources").rglob("*"),
]

run_name = "synth_scaffold__tanh"
s = SynthScaffold(
    input_source_files=input_source_files,
    includes=[
        '"activations_functions.h"',
        '"ap_fixed.h"',
    ],
    output_dir=DIR_CURRENT / run_name,
    target_fn="activation_tanh",
    template_args={
        "T": "ap_fixed<16, 8>",
    },
)
result = s.generate_and_run()
assert result is not None
report: SynthReport = unwrap(result)
report.print_text_summary()
```

If successful, a printed synthesis report will be displayed.

```txt
Module Name: activation_tanh_ap_fixed_16_8_5_3_0_s
Part: xczu9eg-ffvb1156-2-e
Flow Target: vivado

Target Clock Period: 5.0 ns
Target Clock Uncertainty: 1.35 ns
Achieved Clock Period: 3.421 ns

Best-case Latency: 59
Average-case Latency: 59
Worst-case Latency: 59

Best-case Latency (Time): 2.95e-07 s
Average-case Latency (Time): 2.95e-07 s
Worst-case Latency (Time): 2.95e-07 s

LUT Used: 6297
FF Used: 5778
DSP Used: 2
BRAM Used: 0
URAM Used: 0

LUT Utilization: 2.30%
FF Utilization: 1.05%
DSP Utilization: 0.08%
BRAM Utilization: 0.00%
URAM Utilization: N/A
```

### Example 1: Synthesizing a Complex Function + Design Space Exploration

Lets say I have the following target function I would like to synthesize located in `design_sources/graph_processing.h`:

```cpp
// <other code...>

template <int MAX_NUM_NODES,
          int MAX_NUM_EDGES,
          int GUESS_NUM_NODES,
          int GUESS_NUM_EDGES,
          int GUESS_IN_DEGREE,
          int GUESS_OUT_DEGREE>
void process_graph(int num_nodes,
                   int num_edges,
                   int coo[MAX_NUM_EDGES][2],
                   int in_degree[MAX_NUM_NODES],
                   int out_degree[MAX_NUM_NODES],
                   int csr_offsets[MAX_NUM_NODES],
                   int csr[MAX_NUM_EDGES],
                   int csc_offsets[MAX_NUM_NODES],
                   int csc[MAX_NUM_EDGES]) {
    // <function implementation>
}

// <other code...>
```

This function is more complex as it has multiple arguments, some of which are arrays, as well as multiple template arguments.

I can setup SynthScaffold to synthesize this function as follows:

```python
from synth_scaffold import SynthScaffold, SynthReport, unwrap

DIR_CURRENT = Path(__file__).parent
input_source_files = [
    *(DIR_CURRENT / "design_sources").rglob("*"),
]

run_name = "synth_scaffold__process_graph"
s = SynthScaffold(
    input_source_files=input_source_files,
    includes=[
        '"graph_processing.h"',
    ],
    output_dir=DIR_CURRENT / run_name,
    target_fn="process_graph",
    template_args={
        "MAX_NUM_NODES": "128",
        "MAX_NUM_EDGES": "128",
        "GUESS_NUM_NODES": "32",
        "GUESS_NUM_EDGES": "68",
        "GUESS_IN_DEGREE": "2",
        "GUESS_OUT_DEGREE": "2",
    },
)
result = s.generate_and_run()
assert result is not None
report: SynthReport = unwrap(result)
report.print_text_summary()
```

If successful, a printed synthesis report will be displayed as before.

Moreso, since SynthScaffold lets us quicly paramaterize the function, we can easily run the same function with different parameters do a design space exploration over the number of nodes, edges, in-degree, and out-degree.

```python
from synth_scaffold import SynthScaffold, SynthReport, unwrap

DIR_CURRENT = Path(__file__).parent
input_source_files = [
    *(DIR_CURRENT / "design_sources").rglob("*"),
]

configs = [
    {
        "MAX_NUM_NODES": "500"
        "MAX_NUM_EDGES": "1000"
        "GUESS_NUM_NODES": str(i),
        "GUESS_NUM_EDGES": str(i * 2),
        "GUESS_IN_DEGREE": "2",
        "GUESS_OUT_DEGREE": "2",
    }
    for i in range(50, 500, 50)
]

latencies = []

for i, config in enumerate(configs):
    run_name = f"synth_scaffold__process_graph__{i}"
    s = SynthScaffold(
        input_source_files=input_source_files,
        includes=[
            '"graph_processing.h"',
        ],
        output_dir=DIR_CURRENT / run_name,
        target_fn="process_graph",
        template_args=config,
    )
    result = s.generate_and_run()
    assert result is not None
    report: SynthReport = unwrap(result)
    latencies.append((
        report.latency_t_computed_best_case,
        report.latency_t_computed_average_case,
        report.latency_t_computed_worst_case
    ))

# Print the latencies
for i in range(len(configs)):
    print(f"Num Nodes = {configs[i]['GUESS_NUM_NODES']}, Latency = {latencies[i]}")

# Plot the latencies
fig, ax = plt.subplots()
ax.plot([int(config["GUESS_NUM_NODES"]) for config in configs], [latency[1] for latency in latencies], label="Average Case Latency")
ax.fill_between([int(config["GUESS_NUM_NODES"]) for config in configs], [latency[0] for latency in latencies], [latency[2] for latency in latencies], alpha=0.2, label="Best/Worst Case Latency")
ax.set_xlim(0, max([int(config["GUESS_NUM_NODES"]) for config in configs]))
ax.set_ylim(0, max([latency[2] for latency in latencies]) * 1.1)
ax.set_xlabel("Number of Nodes")
ax.set_ylabel("Latency (s)")
ax.set_title("Latency vs Number of Nodes")
fig.tight_layout()
fig.savefig(DIR_CURRENT / "latency_vs_num_nodes.png")
```
