from pathlib import Path

from synth_scaffold import SynthScaffold, unwrap
from synth_scaffold.synth_scaffold import SynthReport

DIR_CURRENT = Path(__file__).parent

design_dir = DIR_CURRENT / "synth_scaffold_vmm_tile"

data_types = ["float", "ap_fixed<32, 16>"]

data_type = "ap_fixed<32, 16>"

synth_scaffold = SynthScaffold(
    input_source_files=[
        DIR_CURRENT / "linalg.h",
    ],
    includes=[
        '"linalg.h"',
        '"ap_fixed.h"',
    ],
    output_dir=design_dir,
    target_fn="vmm_unrolled_tile",
    template_args={
        "DIM_IN": "16",
        "DIM_OUT": "8",
        "T": data_type,
    },
    unsafe_math=True,
    clock_period=5,
)
result = synth_scaffold.generate_and_run()
report: SynthReport = unwrap(result)
report.print_text_summary()
