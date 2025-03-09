import argparse
import re
import shutil
import subprocess
import textwrap
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, TypeVar

T_optional = TypeVar("T_optional")


def unwrap(value: Optional[T_optional], error_message: str | None = None) -> T_optional:
    if value is None:
        if error_message is not None:
            raise ValueError(error_message)
        else:
            raise ValueError("Tried to unwrap None.")
    return value


def split_top_level(s: str) -> list[str]:
    """
    Splits the string `s` on commas that are at the top level,
    i.e. not inside any pair of parentheses () or angle brackets <>.

    For example:
        s = "typename T, std::vector<int, std::allocator<int>>"
    will yield:
        ['typename T', 'std::vector<int, std::allocator<int>>']

    Note: This implementation assumes that the input is well-formed
    with matching pairs of () and <>.
    """
    parts: list[str] = []  # List to store the top-level parts
    current: list[str] = []  # Current part being accumulated
    paren_count = 0  # Count of '(' minus ')'
    angle_count = 0  # Count of '<' minus '>'

    for char in s:
        # Check if the current char is a comma that is not nested.
        if char == "," and paren_count == 0 and angle_count == 0:
            # Append the current accumulated part to the list.
            part = "".join(current).strip()
            if part:
                parts.append(part)
            current = []  # Reset the accumulator for the next part.
        else:
            current.append(char)
            # Increase or decrease the appropriate counters.
            if char == "(":
                paren_count += 1
            elif char == ")":
                paren_count -= 1
            elif char == "<":
                angle_count += 1
            elif char == ">":
                angle_count -= 1

    part = "".join(current).strip()
    if part:
        parts.append(part)

    return parts


# RE_ARG = re.compile(r"&?([A-Za-z_]\w*)\s*(?:\[|$)")
RE_ARG = re.compile(r"&?([A-Za-z_]\w*)\s*(?:\[|=|$)")


def extract_argument_name(arg_str: str) -> str:
    """
    Given an argument declaration like 'int coo[MAX_NUM_EDGES][2]' or 'T csc',
    extract the variable name.
    """
    arg_str = arg_str.strip()
    m = RE_ARG.search(arg_str)
    if m:
        return m.group(1)
    else:
        # fallback: return the entire string stripped (this should rarely happen)
        # return arg_str
        raise ValueError(f"Could not extract argument name from: {arg_str}")


def is_reference_type(arg_str: str) -> bool:
    """
    Given an argument declaration like 'int coo[MAX_NUM_EDGES][2]' or 'T csc',
    determine if the argument is a reference type.
    """
    m = RE_ARG.search(arg_str)
    if m:
        start = m.start(1)
        return start > 0 and arg_str[start - 1] == "&"
    else:
        raise ValueError(f"Could not extract argument name from: {arg_str}")


def build_regex_pattern_from_func(self, function_name: str) -> re.Pattern:
    # pattern = re.compile(
    #     r"(template\s*<(?P<template_args>[^>]+)>\s*)?"  # Optional template declaration
    #     r"(?P<ret_type>[\w:\s\*&<>\[\]]+?)\s+"  # Return type (simplistic)
    #     + re.escape(function_name)
    #     + r"\s*\((?P<args>[^\)]*)\)",  # Argument list (everything until ')')
    #     re.MULTILINE,
    # )
    # (?:(template\s*<(?P<template_args>[^>]+)>\s+))?(?P<ret_type>[a-zA-Z_]\w*(?:\s*[&\*\s])*)\s+activation_tanh\s*\((?P<args>[^\)]*)\)
    # pattern = re.compile(
    #     r"(?:(template\s*<(?P<template_args>[^>]+)>\s+))?"
    #     r"(?P<ret_type>[a-zA-Z_]\w*(?:\s*[&\*\s])*)\s+"
    #     + re.escape(function_name)
    #     + r"\s*\((?P<args>[^\)]*)\)",
    #     re.MULTILINE,
    # )
    # (?:(template\s*<(?P<template_args>[^>]+)>\s+))?(?P<ret_type>[a-zA-Z_]\w*(?:\s*[&*])*\s+)process_graph\s*\((?P<args>[^\)]*)\)
    # pattern = re.compile(
    #     r"(?:(template\s*<(?P<template_args>[^>]+)>\s+))?"
    #     r"(?P<ret_type>[a-zA-Z_]\w*(?:\s*[&*])*\s+)"
    #     + re.escape(pattern=function_name)
    #     + r"\s*\((?P<args>[^\)]*)\)",
    #     re.MULTILINE,
    # )
    # (?:template\s*<(?P<template_args>(?s:(?:(?!template).)+))>\s+)?(?P<ret_type>[a-zA-Z_]\w*(?:\s*[&*])*\s+)pe_message_transformation\s*\((?P<args>[^\)]*)\)
    pattern = re.compile(
        r"(?:template\s*<(?P<template_args>(?s:(?:(?!template).)+))>\s+)?"
        r"(?P<ret_type>[a-zA-Z_]\w*(?:\s*[&*])*\s+)"
        + re.escape(pattern=function_name)
        + r"\s*\((?P<args>[^\)]*)\)",
        re.MULTILINE,
    )
    return pattern


def parse_time_unit(s: str) -> float:
    match s.strip().lower():
        case "ns":
            return 1e-9
        case "us":
            return 1e-6
        case "ms":
            return 1e-3
        case "s":
            return 1.0
        case _:
            raise ValueError(f"Unknown time unit: {s}")


def parse_latency_t(s: str) -> float:
    s_number_raw, s_unit_raw = s.split()
    s_number = float(s_number_raw.strip())
    s_unit = s_unit_raw.strip().lower()
    time_unit_scaler = parse_time_unit(s_unit)
    return s_number * time_unit_scaler


@dataclass
class SynthReport:
    part: str
    flow_target: str

    module_name: str

    clock_unit: str
    target_clock_period: float
    target_clock_uncertainty: float
    achieved_clock_period: float

    @property
    def time_unit_scaler(self) -> float:
        return parse_time_unit(self.clock_unit)

    latency_worst_case: int
    latency_average_case: int
    latency_best_case: int

    latency_t_worst_case: float
    latency_t_average_case: float
    latency_t_best_case: float

    @property
    def latency_t_computed_worst_case(self) -> float:
        return (
            self.latency_worst_case * self.time_unit_scaler * self.target_clock_period
        )

    @property
    def latency_t_computed_average_case(self) -> float:
        return (
            self.latency_average_case * self.time_unit_scaler * self.target_clock_period
        )

    @property
    def latency_t_computed_best_case(self) -> float:
        return self.latency_best_case * self.time_unit_scaler * self.target_clock_period

    resources_lut_used: int
    resources_ff_used: int
    resources_dsp_used: int
    resources_bram_used: int
    resources_uram_used: int

    resources_lut_available: int
    resources_ff_available: int
    resources_dsp_available: int
    resources_bram_available: int
    resources_uram_available: int

    @property
    def resources_lut_utilization(self) -> float | None:
        if self.resources_lut_available == 0:
            return None
        return self.resources_lut_used / self.resources_lut_available

    @property
    def resources_ff_utilization(self) -> float | None:
        if self.resources_ff_available == 0:
            return None
        return self.resources_ff_used / self.resources_ff_available

    @property
    def resources_dsp_utilization(self) -> float | None:
        if self.resources_dsp_available == 0:
            return None
        return self.resources_dsp_used / self.resources_dsp_available

    @property
    def resources_bram_utilization(self) -> float | None:
        if self.resources_bram_available == 0:
            return None
        return self.resources_bram_used / self.resources_bram_available

    @property
    def resources_uram_utilization(self) -> float | None:
        if self.resources_uram_available == 0:
            return None
        return self.resources_uram_used / self.resources_uram_available

    @classmethod
    def from_report_dir(cls, report_dir: Path) -> "SynthReport":
        xml_csynth_fp = report_dir / "csynth.xml"
        if not xml_csynth_fp.exists():
            raise FileNotFoundError(f"File {xml_csynth_fp} does not exist")

        xml_csynth = ET.parse(xml_csynth_fp).getroot()

        instance_element = unwrap(xml_csynth.find(".//InstancesList/Instance"))

        module_name_element = unwrap(instance_element.find("ModuleName"))
        module_name = str(unwrap(module_name_element.text))

        xml_target_fn_fp = report_dir / f"{module_name}_csynth.xml"
        if not xml_target_fn_fp.exists():
            raise FileNotFoundError(f"File {xml_target_fn_fp} does not exist")

        xml_target_fn = ET.parse(xml_target_fn_fp).getroot()

        user_assignments = unwrap(xml_target_fn.find(".//UserAssignments"))

        part = str(unwrap(user_assignments.findtext("Part")))
        flow_target = str(unwrap(user_assignments.findtext("FlowTarget")))
        clock_unit = str(unwrap(user_assignments.findtext("unit")))
        target_clock_period = float(
            unwrap(user_assignments.findtext("TargetClockPeriod"))
        )
        target_clock_uncertainty = float(
            unwrap(user_assignments.findtext("ClockUncertainty"))
        )

        performance_est = unwrap(xml_target_fn.find(".//PerformanceEstimates"))
        summary_of_timing = unwrap(performance_est.find("SummaryOfTimingAnalysis"))
        achieved_clock_period = float(
            unwrap(summary_of_timing.findtext("EstimatedClockPeriod"))
        )

        summary_of_latency = unwrap(performance_est.find("SummaryOfOverallLatency"))
        latency_best_case = int(unwrap(summary_of_latency.findtext("Best-caseLatency")))
        latency_average_case = int(
            unwrap(summary_of_latency.findtext("Average-caseLatency"))
        )
        latency_worst_case = int(
            unwrap(summary_of_latency.findtext("Worst-caseLatency"))
        )

        latency_t_best_case = parse_latency_t(
            unwrap(summary_of_latency.findtext("Best-caseRealTimeLatency"))
        )
        latency_t_average_case = parse_latency_t(
            unwrap(summary_of_latency.findtext("Average-caseRealTimeLatency"))
        )
        latency_t_worst_case = parse_latency_t(
            unwrap(summary_of_latency.findtext("Worst-caseRealTimeLatency"))
        )

        area_estimates = unwrap(xml_target_fn.find(".//AreaEstimates"))

        resources = unwrap(area_estimates.find(".//Resources"))
        resources_lut_used = int(unwrap(resources.findtext("LUT")))
        resources_ff_used = int(unwrap(resources.findtext("FF")))
        resources_dsp_used = int(unwrap(resources.findtext("DSP")))
        resources_bram_used = int(unwrap(resources.findtext("BRAM_18K")))
        resources_uram_used = int(unwrap(resources.findtext("URAM")))

        resources_available = unwrap(area_estimates.find(".//AvailableResources"))
        resources_lut_available = int(unwrap(resources_available.findtext("LUT")))
        resources_ff_available = int(unwrap(resources_available.findtext("FF")))
        resources_dsp_available = int(unwrap(resources_available.findtext("DSP")))
        resources_bram_available = int(unwrap(resources_available.findtext("BRAM_18K")))
        resources_uram_available = int(unwrap(resources_available.findtext("URAM")))

        return cls(
            part=part,
            flow_target=flow_target,
            module_name=module_name,
            clock_unit=clock_unit,
            target_clock_period=target_clock_period,
            target_clock_uncertainty=target_clock_uncertainty,
            achieved_clock_period=achieved_clock_period,
            latency_best_case=latency_best_case,
            latency_average_case=latency_average_case,
            latency_worst_case=latency_worst_case,
            latency_t_best_case=latency_t_best_case,
            latency_t_average_case=latency_t_average_case,
            latency_t_worst_case=latency_t_worst_case,
            resources_lut_used=resources_lut_used,
            resources_ff_used=resources_ff_used,
            resources_dsp_used=resources_dsp_used,
            resources_bram_used=resources_bram_used,
            resources_uram_used=resources_uram_used,
            resources_lut_available=resources_lut_available,
            resources_ff_available=resources_ff_available,
            resources_dsp_available=resources_dsp_available,
            resources_bram_available=resources_bram_available,
            resources_uram_available=resources_uram_available,
        )

    def text_summary(self) -> str:
        txt = ""
        txt += f"Module Name: {self.module_name}\n"
        txt += f"Part: {self.part}\n"
        txt += f"Flow Target: {self.flow_target}\n"
        txt += "\n"
        txt += f"Target Clock Period: {self.target_clock_period} {self.clock_unit}\n"
        txt += f"Target Clock Uncertainty: {self.target_clock_uncertainty} {self.clock_unit}\n"
        txt += (
            f"Achieved Clock Period: {self.achieved_clock_period} {self.clock_unit}\n"
        )
        txt += "\n"
        txt += f"Best-case Latency: {self.latency_best_case}\n"
        txt += f"Average-case Latency: {self.latency_average_case}\n"
        txt += f"Worst-case Latency: {self.latency_worst_case}\n"
        txt += "\n"
        # txt += f"Best-case Latency (Time): {self.latency_t_best_case} s\n"
        # txt += f"Average-case Latency (Time): {self.latency_t_average_case} s\n"
        # txt += f"Worst-case Latency (Time): {self.latency_t_worst_case} s\n"
        txt += f"Best-case Latency (Time): {self.latency_t_computed_best_case:.2e} s\n"
        txt += f"Average-case Latency (Time): {self.latency_t_computed_average_case:.2e} s\n"
        txt += (
            f"Worst-case Latency (Time): {self.latency_t_computed_worst_case:.2e} s\n"
        )
        txt += "\n"
        txt += f"LUT Used: {self.resources_lut_used}\n"
        txt += f"FF Used: {self.resources_ff_used}\n"
        txt += f"DSP Used: {self.resources_dsp_used}\n"
        txt += f"BRAM Used: {self.resources_bram_used}\n"
        txt += f"URAM Used: {self.resources_uram_used}\n"
        txt += "\n"
        if self.resources_lut_utilization is not None:
            txt += f"LUT Utilization: {self.resources_lut_utilization:.2%}\n"
        else:
            txt += "LUT Utilization: N/A\n"
        if self.resources_ff_utilization is not None:
            txt += f"FF Utilization: {self.resources_ff_utilization:.2%}\n"
        else:
            txt += "FF Utilization: N/A\n"
        if self.resources_dsp_utilization is not None:
            txt += f"DSP Utilization: {self.resources_dsp_utilization:.2%}\n"
        else:
            txt += "DSP Utilization: N/A\n"
        if self.resources_bram_utilization is not None:
            txt += f"BRAM Utilization: {self.resources_bram_utilization:.2%}\n"
        else:
            txt += "BRAM Utilization: N/A\n"
        if self.resources_uram_utilization is not None:
            txt += f"URAM Utilization: {self.resources_uram_utilization:.2%}\n"
        else:
            txt += "URAM Utilization: N/A\n"
        return txt

    def print_text_summary(self) -> None:
        print(self.text_summary())


class SynthScaffold:
    def __init__(
        self,
        input_source_files: list[Path],
        output_dir: Path,
        target_fn: str,
        includes: list[str] = [],
        template_args: dict[str, str | int] = {},
        defines: dict[str, str] = {},
        part: str = "xczu9eg-ffvb1156-2-e",
        unsafe_math: bool = False,
        clock_period: float = 5.0,
    ) -> None:
        self.target_fn = target_fn
        self.includes = includes
        self.input_source_files = input_source_files
        self.output_dir = output_dir
        self.template_args = template_args
        self.defines = defines

        self.part = part
        self.unsafe_math = unsafe_math
        self.clock_period = clock_period

        # check that all the source files exist
        for file in self.input_source_files:
            if not file.exists():
                raise FileNotFoundError(f"File {file} does not exist")

    def generate(self) -> None:
        synth_wrapper_cpp = ""

        for include in self.includes:
            synth_wrapper_cpp += f"#include {include}\n"
        if self.includes:
            synth_wrapper_cpp += "\n\n"

        for define in self.defines:
            synth_wrapper_cpp += f"#define {define} ({self.defines[define]})\n"
        if self.defines:
            synth_wrapper_cpp += "\n\n"

        for template_arg, value in self.template_args.items():
            synth_wrapper_cpp += f"#define {template_arg} {value}\n"
        if len(self.template_args) > 0:
            synth_wrapper_cpp += "\n\n"

        # parse out the target function data from source files
        target_fn_match = None
        target_fn_pattern = build_regex_pattern_from_func(self, self.target_fn)
        for fp in self.input_source_files:
            source_txt = fp.read_text()
            source_txt = "\n".join(
                line
                for line in source_txt.splitlines()
                if not line.strip().startswith("//")
            )
            match = target_fn_pattern.search(source_txt)
            if match:
                target_fn_match = match
                break

        if target_fn_match is None:
            raise ValueError(
                f"Could not find target function {self.target_fn} in any of the source files"
            )

        # extract the target function signature
        target_fn_template_args = target_fn_match.group("template_args")
        target_fn_ret_type = target_fn_match.group("ret_type").strip()
        if not target_fn_ret_type:
            raise ValueError("Could not find return type for target function")
        target_fn_args = target_fn_match.group("args").strip()
        if not target_fn_args:
            raise ValueError("Could not find arguments for target function")

        template_args_list = (
            split_top_level(target_fn_template_args) if target_fn_template_args else []
        )
        template_args_map = {}
        for idx, template_arg in enumerate(iterable=template_args_list):
            data_template_arg: dict[str, str | int] = {}
            data_template_arg["index"] = idx
            data_template_arg["name"] = extract_argument_name(template_arg)
            template_args_map[template_arg] = data_template_arg

        for template_arg, template_arg_data in template_args_map.items():
            # check to see if user pased in the template argument data
            if template_arg_data["name"] not in self.template_args:
                raise ValueError(
                    f"Missing user defined template argument data for: {template_arg_data['name']}"
                )

        function_args_list: list[str] = split_top_level(target_fn_args)
        function_args_map = {}
        for idx, function_arg in enumerate(iterable=function_args_list):
            data_function_arg: dict[str, str | int] = {}
            data_function_arg["index"] = idx
            data_function_arg["name"] = extract_argument_name(arg_str=function_arg)
            data_function_arg["is_reference"] = is_reference_type(arg_str=function_arg)
            function_args_map[function_arg] = data_function_arg

        # ----------------------------------------------------------------------
        # Generate the scaffolded top-level function.
        # The new function will have a name like <target_fn>_scaffold.
        scaffold_fn_name = "scaffold_fn"
        scaffold_fn_code = ""
        scaffold_fn_code += f"{target_fn_ret_type} {scaffold_fn_name}(\n"
        for i, arg in enumerate(function_args_list):
            scaffold_fn_code += " " * 4 + arg
            if i < len(function_args_list) - 1:
                scaffold_fn_code += ","
            scaffold_fn_code += "\n"
        scaffold_fn_code += ") {\n"

        scaffold_fn_code += f"    #pragma HLS TOP name = {scaffold_fn_name}\n"

        scaffold_fn_code += "\n\n"

        for arg in function_args_list:
            var_name = extract_argument_name(arg)
            is_reference = is_reference_type(arg)
            # scaffold_fn_code += f"    auto local_{var_name} = {var_name};\n"
            if is_reference:
                scaffold_fn_code += f"    auto &local_{var_name} = {var_name};\n"
            else:
                scaffold_fn_code += f"    auto local_{var_name} = {var_name};\n"

        scaffold_fn_code += "\n\n"

        # call the target function with the local variables
        function_call_txt = ""
        function_call_txt += f"{self.target_fn}"
        if target_fn_template_args:
            function_call_txt += "<\n"
            for data in sorted(template_args_map.values(), key=lambda x: x["index"]):
                arg_name = str(data["name"])
                arg_index = int(data["index"])
                function_call_txt += " " * 4 + f"{arg_name}"
                if arg_index < len(template_args_map) - 1:
                    function_call_txt += ", "
                function_call_txt += "\n"
            function_call_txt += ">"
        function_call_txt += "(\n"
        for data in sorted(function_args_map.values(), key=lambda x: x["index"]):
            arg_name = str(data["name"])
            arg_index = int(data["index"])
            function_call_txt += " " * 4 + f"local_{arg_name}"
            if arg_index < len(function_args_map) - 1:
                function_call_txt += ", "
            function_call_txt += "\n"
        function_call_txt += ");"

        if target_fn_ret_type != "void":
            scaffold_fn_code += f"    auto result = {textwrap.indent(function_call_txt, prefix=' ' * 4)[4:]}\n"
            scaffold_fn_code += "    return result;\n"
        else:
            scaffold_fn_code += f"{textwrap.indent(function_call_txt, ' ' * 4)}\n"

        scaffold_fn_code += "\n\n"

        scaffold_fn_code += "}\n"

        synth_wrapper_cpp += scaffold_fn_code

        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)

        self.output_dir.mkdir(parents=True, exist_ok=True)

        synth_wrapper_cpp_fp = self.output_dir / "scaffold.cpp"
        synth_wrapper_cpp_fp.write_text(synth_wrapper_cpp)

        tcl_script_txt = ""
        tcl_script_txt += "open_project -reset synth_scaffold_project\n"
        tcl_script_txt += "\n\n"
        tcl_script_txt += f"add_files {synth_wrapper_cpp_fp}\n"
        tcl_script_txt += "\n\n"
        tcl_script_txt += "set_top scaffold_fn\n"
        tcl_script_txt += "\n\n"
        tcl_script_txt += 'open_solution -reset -flow_target vivado "solution_csynth"\n'
        tcl_script_txt += f"set_part {{{self.part}}}\n"
        tcl_script_txt += (
            f"create_clock -period {self.clock_period} -name clk_default\n"
        )
        if self.unsafe_math:
            tcl_script_txt += "config_compile -unsafe_math_optimizations\n"
        tcl_script_txt += "\n\n"
        tcl_script_txt += f"set_directive_inline -off {self.target_fn}\n"
        tcl_script_txt += "\n\n"
        tcl_script_txt += "csynth_design\n"
        tcl_script_txt += "\n\n"
        tcl_script_txt += "exit\n"

        tcl_script_fp = self.output_dir / "csynth.tcl"
        tcl_script_fp.write_text(tcl_script_txt)

        for fp in self.input_source_files:
            fp_dst = self.output_dir / fp.name
            fp_dst.write_text(fp.read_text())

    def run(self, verbose: bool = False) -> SynthReport | None:
        tcl_script_fp = self.output_dir / "csynth.tcl"
        if not tcl_script_fp.exists():
            raise FileNotFoundError(f"File {tcl_script_fp} does not exist")

        bin_match = shutil.which("vitis_hls")
        if bin_match is None:
            raise FileNotFoundError("Could not find the Vitis HLS binary")

        args = [
            bin_match,
            "csynth.tcl",
            "-l",
            "csynth.log",
        ]

        p = subprocess.run(
            args,
            cwd=self.output_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=-1,
        )

        if verbose:
            print(f"Return Code: {p.returncode}")
            print(f"Log Path: {self.output_dir / 'csynth.log'}")

        flow_log_fp: Path = (
            self.output_dir
            / "synth_scaffold_project"
            / "solution_csynth"
            / ".autopilot"
            / "db"
            / "autopilot.flow.log"
        )
        flow_log_fp_str: str | None = str(flow_log_fp) if flow_log_fp.exists() else None
        if verbose:
            print(f"Autopilot Flow Log: {flow_log_fp_str}")

        report_dir: Path = (
            self.output_dir
            / "synth_scaffold_project"
            / "solution_csynth"
            / "syn"
            / "report"
        )
        report_dir_str: str | None = str(report_dir) if report_dir.exists() else None
        if verbose:
            print(f"Report Dir: {report_dir_str}")

        if report_dir.exists():
            return SynthReport.from_report_dir(report_dir)
        else:
            return None

    def generate_and_run(self, verbose: bool = False) -> None | SynthReport:
        self.generate()
        result = self.run(verbose=verbose)
        return result


def main(args=None) -> bool:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Output directory for the generated scaffold",
    )
    parser.add_argument(
        "--target-fn",
        type=str,
        required=True,
        help="Name of the target function to synthesize",
    )
    parser.add_argument(
        "--input-source-files",
        type=Path,
        nargs="+",
        required=True,
        help="Input source files to synthesize",
    )
    parser.add_argument(
        "--includes",
        type=str,
        nargs="+",
        default=[],
        help="Include directives to add to the generated scaffold",
    )
    parser.add_argument(
        "--template-args",
        type=str,
        nargs="+",
        default=[],
        help="Template arguments to add to the generated scaffold",
    )
    parser.add_argument(
        "--defines",
        type=str,
        nargs="+",
        default=[],
        help="Defines to add to the generated scaffold",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print verbose output",
    )

    args: argparse.Namespace = parser.parse_args(args)

    input_source_files = [Path(fp) for fp in args.input_source_files]
    includes = args.includes
    template_args = {}
    for arg in args.template_args:
        key, value = arg.split("=")
        template_args[key] = value
    defines = {}
    for define in args.defines:
        key, value = define.split("=")
        defines[key] = value

    synth_scaffold = SynthScaffold(
        input_source_files=input_source_files,
        output_dir=args.output_dir,
        target_fn=args.target_fn,
        includes=includes,
        template_args=template_args,
        defines=defines,
    )

    result = synth_scaffold.generate_and_run(verbose=args.verbose)
    if result is not None:
        result.print_text_summary()
        return True
    else:
        print("Synthesis failed.")
        return False


if __name__ == "__main__":
    main()
