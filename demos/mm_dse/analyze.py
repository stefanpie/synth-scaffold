from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

DIR_CURRENT = Path(__file__).parent

df: pd.DataFrame = pd.read_csv(DIR_CURRENT / "latency_results.csv")

df_float = df[df["data_type"] == "float"]
df_fixed = df[df["data_type"].str.contains("ap_fixed")]


# plt.figure(figsize=(10, 6))
# plt.scatter(
#     df_float["block_size_in"] * df["block_size_out"],
#     df_float["latency"],
#     c="blue",
#     alpha=0.5,
# )
# plt.title("Latency vs Block Size")
# plt.xlabel("Block Size (in * out)")
# plt.ylabel("Latency (s)")

# plt.grid()
# plt.savefig("latency_vs_block_size_scatter.png")

# fig, ax = plt.subplots(figsize=(10, 6))
# ax.scatter(
#     df["block_size_in"] * df["block_size_out"],
#     df["latency"],
#     c="blue",
#     alpha=0.5,
# )
# ax.set_title("Latency vs Block Size")
# ax.set_xlabel("Block Size (in * out)")
# ax.set_ylabel("Latency (s)")
# ax.grid(zorder=0, which="major", linestyle="--")
# ax.grid(zorder=0, which="minor", linestyle=":")
# ax.minorticks_on()
# ax.set_axisbelow(True)
# ax.set_xlim(left=0, right=max(df["block_size_in"] * df["block_size_out"]) + 1)
# ax.set_yscale("log")

# fig.tight_layout()
# fig.savefig(DIR_CURRENT / "latency_vs_block_size_scatter.png")

fig, axs = plt.subplots(1, 2, figsize=(20, 6))

for ax, df, label in zip(axs, [df_float, df_fixed], ["float", "fixed"]):
    ax.scatter(
        df["block_size_in"] * df["block_size_out"],
        df["latency"],
        c="blue",
        alpha=0.5,
    )
    ax.set_title("Latency vs Block Size - " + label)
    ax.set_xlabel("Block Size (in * out)")
    ax.set_ylabel("Latency (s)")
    ax.grid(zorder=0, which="major", linestyle="--")
    ax.grid(zorder=0, which="minor", linestyle=":")
    ax.minorticks_on()
    ax.set_axisbelow(True)
    ax.set_xlim(left=0, right=max(df["block_size_in"] * df["block_size_out"]) + 1)
    ax.set_yscale("log")

fig.tight_layout()
fig.savefig(DIR_CURRENT / "latency_vs_block_size_scatter_split.png")

# make a single plot with both data types
fig, ax = plt.subplots(figsize=(10, 6))

for df, label in zip([df_float, df_fixed], ["float", "fixed"]):
    ax.scatter(
        df["block_size_in"] * df["block_size_out"],
        df["latency"],
        alpha=0.5,
        label=label,
    )
ax.set_title("Latency vs Block Size")
ax.set_xlabel("Block Size (in * out)")
ax.set_ylabel("Latency (s)")
ax.grid(zorder=0, which="major", linestyle="--")
ax.grid(zorder=0, which="minor", linestyle=":")
ax.minorticks_on()
ax.set_axisbelow(True)
ax.set_xlim(left=0, right=max(df["block_size_in"] * df["block_size_out"]) + 1)
ax.set_yscale("log")
ax.legend()
fig.tight_layout()
fig.savefig(DIR_CURRENT / "latency_vs_block_size_scatter_both.png")
