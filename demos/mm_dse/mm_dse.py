import json
import multiprocessing
import shutil
from hashlib import md5
from pathlib import Path

import pandas as pd

from synth_scaffold import SynthScaffold, unwrap
from synth_scaffold.synth_scaffold import SynthReport

DIR_CURRENT = Path(__file__).parent

DIR_RUNS = DIR_CURRENT / "synth_scaffold_all_tests"
if DIR_RUNS.exists():
    shutil.rmtree(DIR_RUNS)
DIR_RUNS.mkdir()

N_JOBS = 38

block_sizes_in = [1, 2, 4, 8, 16]
block_sizes_out = [1, 2, 4, 8, 16]
data_types = ["float", "ap_fixed<32, 16>"]

design_sapce = []
for in_size in block_sizes_in:
    for out_size in block_sizes_out:
        for data_type in data_types:
            combo = (in_size, out_size, data_type)
            if combo not in design_sapce:
                design_sapce.append(combo)


def run_synth_scaffold(
    block_size_in: int,
    block_size_out: int,
    data_type: str,
):
    design_config_hash = md5(
        f"{block_size_in}_{block_size_out}_{data_type}".encode()
    ).hexdigest()

    design_dir = DIR_RUNS / design_config_hash

    synth_scaffold = SynthScaffold(
        input_source_files=[
            DIR_CURRENT / "linalg.h",
        ],
        includes=[
            '"linalg.h"',
            '"ap_fixed.h"',
        ],
        output_dir=design_dir,
        target_fn="linear",
        template_args={
            "in_size": "64",
            "out_size": "32",
            "BLOCK_SIZE_IN_": block_size_in,
            "BLOCK_SIZE_OUT_": block_size_out,
            "T": data_type,
        },
        unsafe_math=True,
        clock_period=5,
    )
    result = synth_scaffold.generate_and_run()
    report: SynthReport = unwrap(result)
    latency_avg = report.latency_t_computed_average_case

    # write config and results to file
    data = {
        "block_size_in": block_size_in,
        "block_size_out": block_size_out,
        "data_type": data_type,
        "latency": latency_avg,
    }

    json_path = design_dir / "data.json"
    json_path.write_text(json.dumps(data, indent=4))

    return report.latency_t_computed_average_case


with multiprocessing.Pool(N_JOBS) as pool:
    results = pool.starmap(
        run_synth_scaffold,
        design_sapce,
        chunksize=1,
    )

df = pd.DataFrame(columns=["block_size_in", "block_size_out", "data_type", "latency"])

for config, result in zip(design_sapce, results):
    block_size_in, block_size_out, data_type = config
    df = pd.concat(
        [
            df,
            pd.DataFrame(
                {
                    "block_size_in": [block_size_in],
                    "block_size_out": [block_size_out],
                    "data_type": [data_type],
                    "latency": [result],
                }
            ),
        ]
    )

df.to_csv(DIR_CURRENT / "latency_results.csv", index=False)
