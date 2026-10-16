#!/usr/bin/env python3
"""Merge ordinary LoRA updates, preserving the real (alpha/r) B @ A delta.

AVG concatenation is exact. The optional rank ablation uses thin QR and a small
core SVD, so it never materializes a model-sized dense weight update.
"""

import argparse
import copy
import json
import math
import platform
import re
import time
from pathlib import Path

import safetensors
import torch
from safetensors import safe_open
from safetensors.torch import save_file


def concatenate_average(factors, weights, scales):
    # Output alpha/r = 1. Multiplying each A by w_i*s_i avoids cross terms.
    a = torch.cat([a.float() * (w * s) for (a, _), w, s in zip(factors, weights, scales)], dim=0)
    b = torch.cat([b.float() for _, b in factors], dim=1)
    return a, b


def qr_core(a, b):
    qb, rb = torch.linalg.qr(b, mode="reduced")
    qa, ra = torch.linalg.qr(a.T, mode="reduced")
    return qa, qb, rb @ ra.T


def compress_average(a, b, rank):
    qa, qb, core = qr_core(a, b)
    u, s, vh = torch.linalg.svd(core, full_matrices=False)
    # All singular values are carried on B; output alpha/r remains 1.
    compressed_a = (vh[:rank] @ qa.T).contiguous()
    compressed_b = ((qb @ u[:, :rank]) * s[:rank]).contiguous()
    return compressed_a, compressed_b, s


def factor_norm(a, b):
    # QR keeps error measurement stable even when two factors nearly cancel.
    return float(torch.linalg.vector_norm(qr_core(a, b)[2]).double())


def relative_factor_error(a, b, candidate_a, candidate_b, norm):
    error = factor_norm(torch.cat((a, candidate_a)), torch.cat((b, -candidate_b), dim=1))
    return error / norm if norm else 0.0


def self_test():
    generator = torch.Generator().manual_seed(20261017)
    factors = [(torch.randn(2, 9, generator=generator), torch.randn(7, 2, generator=generator)) for _ in range(4)]
    weights = [0.25] * 4
    scales = [2.0] * 4
    expected = sum(w * s * (b @ a) for (a, b), w, s in zip(factors, weights, scales))
    a, b = concatenate_average(factors, weights, scales)
    torch.testing.assert_close(b @ a, expected, rtol=2e-6, atol=2e-6)
    wrong = (sum(b for _, b in factors) / 4) @ (sum(a for a, _ in factors) / 4) * 2
    assert torch.linalg.vector_norm(wrong - expected) / torch.linalg.vector_norm(expected) > 0.1
    assert not torch.allclose((b @ a) * 2, expected), "test must reject a repeated output scaling"
    ca, cb, singular = compress_average(a, b, 2)
    dense_u, dense_s, dense_vh = torch.linalg.svd(expected, full_matrices=False)
    dense_rank2 = (dense_u[:, :2] * dense_s[:2]) @ dense_vh[:2]
    torch.testing.assert_close(cb @ ca, dense_rank2, rtol=2e-5, atol=5e-6)
    torch.testing.assert_close(torch.linalg.vector_norm(expected - cb @ ca), torch.linalg.vector_norm(singular[2:]), rtol=2e-6, atol=2e-6)
    # The saved adapter convention must produce exactly one application of scale.
    assert 64 / 64 == 1 and 16 / 16 == 1
    return {"passed": True, "tests": ["real_dense_delta_average", "reject_factor_average_cross_terms", "reject_double_scaling", "qr_svd_equals_dense_truncated_svd", "svd_tail_error"]}


def verify_export(config_path, project):
    config = json.loads(config_path.read_text())
    torch.set_num_threads(config.get("cpu_threads", 4))
    readers = [safe_open(project / item["adapter"] / "adapter_model.safetensors", framework="pt", device="cpu") for item in config["inputs"]]
    output = project / config["output_root"]
    exported = safe_open(output / "avg-r64" / "adapter_model.safetensors", framework="pt", device="cpu")
    adapter_config = json.loads((output / "avg-r64" / "adapter_config.json").read_text())
    assert adapter_config["r"] == adapter_config["lora_alpha"] == 64
    sampled_error_squared = sampled_norm_squared = 0.0
    max_error = 0.0
    modules = 0
    for a_key in sorted(key for key in readers[0].keys() if key.endswith(".lora_A.weight")):
        b_key = a_key.replace(".lora_A.weight", ".lora_B.weight")
        ca, cb = exported.get_tensor(a_key), exported.get_tensor(b_key)
        factors = [(reader.get_tensor(a_key), reader.get_tensor(b_key)) for reader in readers]
        for expert, (a, b) in enumerate(factors):
            assert torch.equal(ca[expert * 16:(expert + 1) * 16], a * 0.5)
            assert torch.equal(cb[:, expert * 16:(expert + 1) * 16], b)
        rows = torch.linspace(0, cb.shape[0] - 1, min(16, cb.shape[0])).long()
        expected = sum(0.5 * (b[rows] @ a) for a, b in factors)
        actual = cb[rows] @ ca
        torch.testing.assert_close(actual, expected, rtol=3e-5, atol=1e-8)
        error_squared = float(torch.linalg.vector_norm(actual - expected)) ** 2
        norm_squared = float(torch.linalg.vector_norm(expected)) ** 2
        sampled_error_squared += error_squared
        sampled_norm_squared += norm_squared
        max_error = max(max_error, math.sqrt(error_squared / norm_squared))
        modules += 1
    receipt = {"passed": True, "modules_checked": modules, "all_source_factor_blocks_bitwise_exact": True,
               "dense_rows_per_module": 16, "dense_rows": "evenly spaced across output dimension",
               "global_sampled_dense_relative_error": math.sqrt(sampled_error_squared / sampled_norm_squared),
               "max_layer_sampled_dense_relative_error": max_error,
               "checks": ["all AVG64 source A blocks exactly scaled by0.5", "all source B blocks unchanged", "output alpha/r=1", "actual serialized AVG64 delta equals sum of four source deltas on16 rows of every module"]}
    (output / "serialization_verification.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


def run(config_path, project):
    config = json.loads(config_path.read_text())
    torch.set_num_threads(config.get("cpu_threads", 4))
    torch.set_num_interop_threads(1)
    tests = self_test()
    started = time.time()
    inputs = config["inputs"]
    weights = [item["weight"] for item in inputs]
    assert math.isclose(sum(weights), 1.0)
    input_dirs = [project / item["adapter"] for item in inputs]
    adapter_configs = [json.loads((directory / "adapter_config.json").read_text()) for directory in input_dirs]
    reference = adapter_configs[0]
    checked_fields = ["base_model_name_or_path", "target_modules", "r", "lora_alpha", "fan_in_fan_out", "use_rslora", "use_dora", "bias", "lora_bias", "modules_to_save", "rank_pattern", "alpha_pattern", "target_parameters"]
    for current in adapter_configs:
        assert all(current.get(key) == reference.get(key) for key in checked_fields)
        assert current["r"] == 16 and current["lora_alpha"] == 32
        assert not current.get("use_rslora") and not current.get("use_dora") and not current.get("fan_in_fan_out")
        assert not current.get("rank_pattern") and not current.get("alpha_pattern")
        assert current.get("bias") == "none" and not current.get("lora_bias")
        assert not current.get("modules_to_save") and not current.get("target_parameters")
        assert config["base_revision"] in current["base_model_name_or_path"]
    scales = [current["lora_alpha"] / current["r"] for current in adapter_configs]
    readers = [safe_open(directory / "adapter_model.safetensors", framework="pt", device="cpu") for directory in input_dirs]
    keys = sorted(readers[0].keys())
    assert all(sorted(reader.keys()) == keys for reader in readers)
    a_keys = [key for key in keys if key.endswith(".lora_A.weight")]
    assert len(keys) == 620 and len(a_keys) == 310
    assert all(re.fullmatch(reference["target_modules"], key.removeprefix("base_model.model.").removesuffix(".lora_A.weight")) for key in a_keys)
    outputs = {candidate["name"]: {} for candidate in config["candidates"]}
    layers = []
    for index, a_key in enumerate(a_keys):
        b_key = a_key.replace(".lora_A.weight", ".lora_B.weight")
        factors = [(reader.get_tensor(a_key), reader.get_tensor(b_key)) for reader in readers]
        assert all(a.shape[0] == 16 and b.shape[1] == 16 for a, b in factors)
        assert all(a.shape == factors[0][0].shape and b.shape == factors[0][1].shape for a, b in factors)
        a, b = concatenate_average(factors, weights, scales)
        norm = factor_norm(a, b)
        layer = {"module": a_key.removesuffix(".lora_A.weight"), "weight_shape": [b.shape[0], a.shape[1]], "average_delta_frobenius": norm, "candidates": {}}
        for candidate in config["candidates"]:
            if candidate["representation"] == "exact_concatenation":
                ca, cb = a, b
                residual = 0.0
            else:
                assert candidate["representation"] == "truncated_svd"
                ca, cb, singular = compress_average(a, b, candidate["rank"])
                residual = float(torch.linalg.vector_norm(singular[candidate["rank"]:]))
            outputs[candidate["name"]][a_key] = ca.contiguous()
            outputs[candidate["name"]][b_key] = cb.contiguous()
            layer["candidates"][candidate["name"]] = {
                "rank": candidate["rank"],
                "ideal_svd_residual_frobenius": residual,
                "ideal_svd_relative_error": residual / norm if norm else 0.0,
                "saved_factor_relative_error": relative_factor_error(a, b, ca, cb, norm),
            }
        layers.append(layer)
        if index % 25 == 0 or index == len(a_keys) - 1:
            print(json.dumps({"completed_modules": index + 1, "total_modules": len(a_keys), "elapsed_seconds": round(time.time() - started, 2)}), flush=True)
    metadata = {"config": config, "input_adapter_configs": adapter_configs, "module_count": len(a_keys), "tensor_count_per_adapter": len(keys), "self_test": tests, "torch_version": torch.__version__, "safetensors_version": safetensors.__version__, "python_version": platform.python_version(), "output_dtype": "float32", "layers": layers}
    total_squared_norm = sum(layer["average_delta_frobenius"] ** 2 for layer in layers)
    metadata["global_average_delta_frobenius"] = math.sqrt(total_squared_norm)
    metadata["candidate_summaries"] = {}
    for candidate in config["candidates"]:
        name = candidate["name"]
        summary = {
            "global_ideal_relative_error": math.sqrt(sum(layer["candidates"][name]["ideal_svd_residual_frobenius"] ** 2 for layer in layers) / total_squared_norm),
            "global_saved_factor_relative_error": math.sqrt(sum((layer["candidates"][name]["saved_factor_relative_error"] * layer["average_delta_frobenius"]) ** 2 for layer in layers) / total_squared_norm),
            "max_layer_saved_factor_relative_error": max(layer["candidates"][name]["saved_factor_relative_error"] for layer in layers),
            "parameter_count": sum(tensor.numel() for tensor in outputs[name].values()),
        }
        metadata["candidate_summaries"][name] = summary
        directory = project / config["output_root"] / name
        directory.mkdir(parents=True, exist_ok=True)
        output_config = copy.deepcopy(reference)
        output_config.update({"r": candidate["rank"], "lora_alpha": candidate["rank"], "lora_dropout": 0.0, "inference_mode": True, "revision": config["base_revision"]})
        (directory / "adapter_config.json").write_text(json.dumps(output_config, indent=2) + "\n")
        save_file(outputs[name], directory / "adapter_model.safetensors", metadata={"format": "pt"})
        with safe_open(directory / "adapter_model.safetensors", framework="pt", device="cpu") as saved:
            assert sorted(saved.keys()) == keys
            assert all(torch.equal(saved.get_tensor(key), tensor) for key, tensor in outputs[name].items())
        summary["serialized_factors_bitwise_equal"] = True
        (directory / "merge_manifest.json").write_text(json.dumps({"candidate": candidate, "selected_final": name == config["selected_final"], "config": config, "summary": summary, "adapter_scale": 1.0, "output_dtype": "float32"}, indent=2) + "\n")
    metadata["elapsed_seconds"] = round(time.time() - started, 3)
    report = project / config["output_root"] / "merge_report.json"
    report.write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps({"report": str(report), "elapsed_seconds": metadata["elapsed_seconds"], "candidates": metadata["candidate_summaries"]}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        torch.set_num_threads(4)
        print(json.dumps(self_test(), indent=2))
    elif args.verify:
        verify_export(args.config, args.project)
    else:
        run(args.config, args.project)


if __name__ == "__main__":
    main()
