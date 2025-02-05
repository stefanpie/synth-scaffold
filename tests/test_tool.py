from pathlib import Path

from synth_scaffold.synth_scaffold import SynthScaffold, unwrap

DIR_CURRENT: Path = Path(__file__).parent

input_source_files = [
    *(DIR_CURRENT / "test_sources").rglob("*"),
]


def test_tool_0():
    test_name = "synth_scaffold_test_0"
    s = SynthScaffold(
        input_source_files=input_source_files,
        includes=[
            '"gnnbuilder_neo_lib.h"',
            '"ap_fixed.h"',
            '"hls_stream.h"',
        ],
        output_dir=DIR_CURRENT / test_name,
        target_fn="pe_message_transformation",
        template_args={
            "T": "ap_fixed<16, 8>",
            "GraphParams": "GraphParams<128, 128, 32, 68, 2, 2>",
            "PEParams": "PEParams<16, 8>",
            "NUM_FEATURES": "16",
            "op_message_transformation": "op_message_transformation__simple_conv<ap_fixed<16, 8>, 16>",
        },
    )
    result = s.generate_and_run()
    assert result is not None
    report = unwrap(result)
    report.print_text_summary()


def test_tool_1():
    test_name = "synth_scaffold_test_1"
    s = SynthScaffold(
        input_source_files=input_source_files,
        includes=[
            '"gnnbuilder_neo_activations.h"',
            '"ap_fixed.h"',
        ],
        output_dir=DIR_CURRENT / test_name,
        target_fn="activation_tanh",
        template_args={
            "T": "ap_fixed<16, 8>",
        },
    )
    result = s.generate_and_run()
    assert result is not None
    report = unwrap(result)
    report.print_text_summary()


def test_tool_2():
    test_name = "synth_scaffold_test_2"
    s = SynthScaffold(
        input_source_files=input_source_files,
        includes=[
            '"gnnbuilder_neo_graph_processing.h"',
        ],
        output_dir=DIR_CURRENT / test_name,
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
    report = unwrap(result)
    report.print_text_summary()
