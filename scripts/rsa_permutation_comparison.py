#!/usr/bin/env python3
"""RSA dimers on a 100x100 lattice: no pre-permutation vs permutation."""

from __future__ import annotations

import csv
import math
import os
import random
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, stdev

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


L = 100
RUNS = 500
BASE_SEED = 20260524
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
FIGURES = ROOT / "figures"
LOGS = ROOT / "logs"
REPORTS = ROOT / "reports"


@dataclass
class RunResult:
    method: str
    run: int
    seed: int
    cp: float
    cj: float
    dimers_at_cp: int
    dimers_at_cj: int
    h_at_cj: int
    v_at_cj: int
    lr_at_cp: bool
    tb_at_cp: bool


class DSU:
    def __init__(self, n: int) -> None:
        self.parent = list(range(n))
        self.rank = [0] * n
        self.left = [False] * n
        self.right = [False] * n
        self.top = [False] * n
        self.bottom = [False] * n

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> int:
        ra = self.find(a)
        rb = self.find(b)
        if ra == rb:
            return ra
        if self.rank[ra] < self.rank[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        if self.rank[ra] == self.rank[rb]:
            self.rank[ra] += 1
        self.left[ra] = self.left[ra] or self.left[rb]
        self.right[ra] = self.right[ra] or self.right[rb]
        self.top[ra] = self.top[ra] or self.top[rb]
        self.bottom[ra] = self.bottom[ra] or self.bottom[rb]
        return ra

    def activate(self, idx: int, x: int, y: int, L_: int) -> None:
        self.left[idx] = x == 0
        self.right[idx] = x == L_ - 1
        self.top[idx] = y == 0
        self.bottom[idx] = y == L_ - 1

    def spans(self, idx: int) -> tuple[bool, bool]:
        r = self.find(idx)
        return self.left[r] and self.right[r], self.top[r] and self.bottom[r]


def all_edges(L_: int) -> list[tuple[int, int, str]]:
    edges: list[tuple[int, int, str]] = []
    for y in range(L_):
        base = y * L_
        for x in range(L_ - 1):
            edges.append((base + x, base + x + 1, "H"))
    for y in range(L_ - 1):
        base = y * L_
        for x in range(L_):
            edges.append((base + x, base + x + L_, "V"))
    return edges


EDGES = all_edges(L)
INCIDENT: list[list[int]] = [[] for _ in range(L * L)]
for edge_id, (a, b, _orient) in enumerate(EDGES):
    INCIDENT[a].append(edge_id)
    INCIDENT[b].append(edge_id)


def add_dimer(
    occ: list[bool], dsu: DSU, a: int, b: int, L_: int
) -> tuple[bool, bool]:
    for idx in (a, b):
        occ[idx] = True
        y, x = divmod(idx, L_)
        dsu.activate(idx, x, y, L_)

    root = dsu.union(a, b)
    for idx in (a, b):
        y, x = divmod(idx, L_)
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= nx < L_ and 0 <= ny < L_:
                nidx = ny * L_ + nx
                if occ[nidx]:
                    root = dsu.union(root, nidx)
    return dsu.spans(root)


def run_no_permutation(run_id: int, seed: int) -> tuple[RunResult, np.ndarray, np.ndarray, np.ndarray]:
    """Randomly choose the next currently legal dimer, without pre-shuffling."""
    rng = random.Random(seed)
    occ = [False] * (L * L)
    dsu = DSU(L * L)
    valid = list(range(len(EDGES)))
    pos = list(range(len(EDGES)))
    active = [True] * len(EDGES)
    orient_grid = np.zeros((L, L), dtype=np.uint8)
    percolation_grid = np.zeros((L, L), dtype=np.uint8)

    dimers = h_count = v_count = 0
    cp = math.nan
    dimers_at_cp = 0
    lr_at_cp = tb_at_cp = False

    while valid:
        slot = rng.randrange(len(valid))
        edge_id = valid[slot]
        valid[slot] = valid[-1]
        pos[valid[slot]] = slot
        valid.pop()
        active[edge_id] = False

        a, b, orient = EDGES[edge_id]
        if occ[a] or occ[b]:
            continue

        dimers += 1
        if orient == "H":
            h_count += 1
        else:
            v_count += 1
        lr, tb = add_dimer(occ, dsu, a, b, L)
        orient_grid.flat[a] = 1 if orient == "H" else 2
        orient_grid.flat[b] = 1 if orient == "H" else 2

        if math.isnan(cp) and (lr or tb):
            cp = 2 * dimers / (L * L)
            dimers_at_cp = dimers
            lr_at_cp, tb_at_cp = lr, tb
            percolation_grid = orient_grid.copy()

        for site in (a, b):
            for incident_id in INCIDENT[site]:
                if active[incident_id]:
                    remove_slot = pos[incident_id]
                    last_id = valid[-1]
                    valid[remove_slot] = last_id
                    pos[last_id] = remove_slot
                    valid.pop()
                    active[incident_id] = False

    cj = 2 * dimers / (L * L)
    result = RunResult(
        "bez_permutacji",
        run_id,
        seed,
        cp,
        cj,
        dimers_at_cp,
        dimers,
        h_count,
        v_count,
        lr_at_cp,
        tb_at_cp,
    )
    return result, np.array(occ, dtype=bool).reshape((L, L)), orient_grid, percolation_grid


def run_with_permutation(run_id: int, seed: int) -> tuple[RunResult, np.ndarray, np.ndarray, np.ndarray]:
    """Shuffle all possible dimers once, then scan the permutation."""
    rng = random.Random(seed)
    order = list(range(len(EDGES)))
    rng.shuffle(order)
    occ = [False] * (L * L)
    dsu = DSU(L * L)
    orient_grid = np.zeros((L, L), dtype=np.uint8)
    percolation_grid = np.zeros((L, L), dtype=np.uint8)

    dimers = h_count = v_count = 0
    cp = math.nan
    dimers_at_cp = 0
    lr_at_cp = tb_at_cp = False

    for edge_id in order:
        a, b, orient = EDGES[edge_id]
        if occ[a] or occ[b]:
            continue
        dimers += 1
        if orient == "H":
            h_count += 1
        else:
            v_count += 1
        lr, tb = add_dimer(occ, dsu, a, b, L)
        orient_grid.flat[a] = 1 if orient == "H" else 2
        orient_grid.flat[b] = 1 if orient == "H" else 2
        if math.isnan(cp) and (lr or tb):
            cp = 2 * dimers / (L * L)
            dimers_at_cp = dimers
            lr_at_cp, tb_at_cp = lr, tb
            percolation_grid = orient_grid.copy()

    cj = 2 * dimers / (L * L)
    result = RunResult(
        "z_permutacja",
        run_id,
        seed,
        cp,
        cj,
        dimers_at_cp,
        dimers,
        h_count,
        v_count,
        lr_at_cp,
        tb_at_cp,
    )
    return result, np.array(occ, dtype=bool).reshape((L, L)), orient_grid, percolation_grid


def summarize(values: list[float]) -> dict[str, float]:
    n = len(values)
    sd = stdev(values)
    sem = sd / math.sqrt(n)
    return {
        "n": n,
        "mean": mean(values),
        "sd": sd,
        "sem": sem,
        "min": min(values),
        "q25": float(np.quantile(values, 0.25)),
        "median": float(np.quantile(values, 0.5)),
        "q75": float(np.quantile(values, 0.75)),
        "max": max(values),
        "ci95_low": mean(values) - 1.96 * sem,
        "ci95_high": mean(values) + 1.96 * sem,
    }


def welch_t(a: list[float], b: list[float]) -> tuple[float, float]:
    ma, mb = mean(a), mean(b)
    va, vb = stdev(a) ** 2, stdev(b) ** 2
    na, nb = len(a), len(b)
    t = (ma - mb) / math.sqrt(va / na + vb / nb)
    df_num = (va / na + vb / nb) ** 2
    df_den = (va * va) / (na * na * (na - 1)) + (vb * vb) / (nb * nb * (nb - 1))
    return t, df_num / df_den


def normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def approx_p_from_t(t: float, df: float) -> float:
    # For df close to 1000 the normal approximation is more than adequate here.
    return 2.0 * (1.0 - normal_cdf(abs(t)))


def save_runs_csv(results: list[RunResult]) -> None:
    path = DATA / "rsa_500_runs_per_method.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(RunResult.__dataclass_fields__.keys()))
        writer.writeheader()
        for r in results:
            writer.writerow(r.__dict__)


def save_summary(results: list[RunResult]) -> list[dict[str, str | float]]:
    rows: list[dict[str, str | float]] = []
    for method in ("bez_permutacji", "z_permutacja"):
        subset = [r for r in results if r.method == method]
        for metric in ("cp", "cj"):
            stats = summarize([getattr(r, metric) for r in subset])
            rows.append({"method": method, "metric": metric, **stats})

        cp_mean = mean(r.cp for r in subset)
        cj_mean = mean(r.cj for r in subset)
        dp_mean = mean(r.dimers_at_cp for r in subset)
        dj_mean = mean(r.dimers_at_cj for r in subset)
        rows.append(
            {
                "method": method,
                "metric": "derived",
                "Cp/dp": cp_mean / dp_mean,
                "Cj/dj": cj_mean / dj_mean,
                "Cp/L": cp_mean / L,
                "Cj/L": cj_mean / L,
                "Cp/Cj": cp_mean / cj_mean,
            }
        )

    path = DATA / "rsa_summary_statistics.csv"
    keys = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)
    return rows


def save_comparison(results: list[RunResult]) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    for metric in ("cp", "cj"):
        a = [getattr(r, metric) for r in results if r.method == "bez_permutacji"]
        b = [getattr(r, metric) for r in results if r.method == "z_permutacja"]
        t, df = welch_t(a, b)
        rows.append(
            {
                "metric": metric,
                "mean_bez_permutacji": mean(a),
                "mean_z_permutacja": mean(b),
                "difference": mean(b) - mean(a),
                "welch_t": t,
                "welch_df": df,
                "p_approx_normal": approx_p_from_t(t, df),
            }
        )
    path = DATA / "rsa_method_comparison.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return rows


def plot_histograms(results: list[RunResult]) -> None:
    for metric, label in (("cp", "Cp - prog perkolacji"), ("cj", "Cj - jamming")):
        plt.figure(figsize=(7.2, 4.6), dpi=160)
        for method, color in (("bez_permutacji", "#2D6CDF"), ("z_permutacja", "#D9534F")):
            vals = [getattr(r, metric) for r in results if r.method == method]
            plt.hist(vals, bins=28, alpha=0.55, label=method.replace("_", " "), color=color)
        plt.xlabel("Pokrycie powierzchni")
        plt.ylabel("Liczba przebiegow")
        plt.title(label + " dla 500 przebiegow na metode")
        plt.legend()
        plt.tight_layout()
        plt.savefig(FIGURES / f"hist_{metric}.png")
        plt.close()


def plot_boxplot(results: list[RunResult]) -> None:
    labels = []
    vals = []
    for metric in ("cp", "cj"):
        for method in ("bez_permutacji", "z_permutacja"):
            labels.append(f"{metric.upper()}\n{method.replace('_', ' ')}")
            vals.append([getattr(r, metric) for r in results if r.method == method])
    plt.figure(figsize=(7.6, 4.8), dpi=160)
    plt.boxplot(vals, labels=labels, showmeans=True)
    plt.ylabel("Pokrycie powierzchni")
    plt.title("Porownanie rozkladow Cp i Cj")
    plt.tight_layout()
    plt.savefig(FIGURES / "boxplot_cp_cj.png")
    plt.close()


def plot_ratios(results: list[RunResult]) -> None:
    methods = ("bez_permutacji", "z_permutacja")
    names = ["Cp/dp", "Cj/dj", "Cp/L", "Cj/L", "Cp/Cj"]
    data = []
    for method in methods:
        subset = [r for r in results if r.method == method]
        cp_mean = mean(r.cp for r in subset)
        cj_mean = mean(r.cj for r in subset)
        dp_mean = mean(r.dimers_at_cp for r in subset)
        dj_mean = mean(r.dimers_at_cj for r in subset)
        data.append([cp_mean / dp_mean, cj_mean / dj_mean, cp_mean / L, cj_mean / L, cp_mean / cj_mean])

    x = np.arange(len(names))
    width = 0.35
    plt.figure(figsize=(8.2, 4.6), dpi=160)
    plt.bar(x - width / 2, data[0], width, label="bez permutacji", color="#2D6CDF")
    plt.bar(x + width / 2, data[1], width, label="z permutacja", color="#D9534F")
    plt.xticks(x, names)
    plt.ylabel("Wartosc")
    plt.title("Wskazniki wymagane w promptcie")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGURES / "ratios_prompt_metrics.png")
    plt.close()


def plot_configuration(grid: np.ndarray, title: str, path: Path) -> None:
    from matplotlib.colors import ListedColormap

    cmap = ListedColormap(["white", "#2D6CDF", "#D9534F"])
    plt.figure(figsize=(6, 6), dpi=180)
    plt.imshow(grid, cmap=cmap, interpolation="nearest", vmin=0, vmax=2)
    plt.title(title)
    plt.xticks([])
    plt.yticks([])
    legend_handles = [
        plt.Rectangle((0, 0), 1, 1, color="#2D6CDF", label="dimer poziomy"),
        plt.Rectangle((0, 0), 1, 1, color="#D9534F", label="dimer pionowy"),
    ]
    plt.legend(handles=legend_handles, loc="lower center", bbox_to_anchor=(0.5, -0.08), ncol=2)
    plt.tight_layout()
    plt.savefig(path)
    plt.close()


def main() -> None:
    for directory in (DATA, FIGURES, LOGS, REPORTS):
        directory.mkdir(exist_ok=True)

    results: list[RunResult] = []
    example_grids: dict[str, np.ndarray] = {}
    funcs = {
        "bez_permutacji": run_no_permutation,
        "z_permutacja": run_with_permutation,
    }

    log_path = LOGS / "dziennik_symulacji.md"
    with log_path.open("w", encoding="utf-8") as log:
        log.write("# Dziennik symulacji RSA: permutacja vs bez permutacji\n\n")
        log.write(f"- L = {L}\n- przebiegi na metode = {RUNS}\n- seed bazowy = {BASE_SEED}\n")
        log.write("- hard boundary condition, dimery poziome i pionowe\n\n")

        for method, func in funcs.items():
            log.write(f"## {method}\n\n")
            for run_id in range(1, RUNS + 1):
                seed = BASE_SEED + (0 if method == "bez_permutacji" else 1_000_000) + run_id
                result, _occ_grid, orient_grid, percolation_grid = func(run_id, seed)
                results.append(result)
                if run_id == 1:
                    example_grids[f"jamming_{method}"] = orient_grid
                    example_grids[f"perkolacja_{method}"] = percolation_grid
                if run_id % 50 == 0:
                    log.write(f"- ukonczono {run_id}/{RUNS}; ostatnie Cp={result.cp:.4f}, Cj={result.cj:.4f}\n")

    save_runs_csv(results)
    save_summary(results)
    save_comparison(results)
    plot_histograms(results)
    plot_boxplot(results)
    plot_ratios(results)
    for name, grid in example_grids.items():
        stage, method = name.split("_", 1)
        plot_configuration(
            grid,
            f"Konfiguracja {stage}, {method.replace('_', ' ')}, przebieg 1",
            FIGURES / f"konfiguracja_{stage}_{method}.png",
        )

    print(f"Saved {len(results)} run results.")
    print(DATA / "rsa_500_runs_per_method.csv")
    print(DATA / "rsa_summary_statistics.csv")
    print(DATA / "rsa_method_comparison.csv")


if __name__ == "__main__":
    main()
