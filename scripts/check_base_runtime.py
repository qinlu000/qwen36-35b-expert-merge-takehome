"""CPU-only checks of the fixed Base runtime; never load model weights."""

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-metadata", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    os.environ.update(CUDA_VISIBLE_DEVICES="", HF_HUB_OFFLINE="1",
                      TRANSFORMERS_OFFLINE="1", VLLM_NO_USAGE_STATS="1")

    import torch
    import vllm
    import vllm.entrypoints.cli.main
    import qwen_vl_utils
    from PIL import Image
    from transformers import AutoConfig, AutoProcessor

    versions = {name: importlib.metadata.version(name) for name in (
        "torch", "vllm", "transformers", "qwen-vl-utils", "torchvision", "av")}
    assert versions["torch"] == "2.11.0+cu130"
    assert versions["vllm"] == "0.20.2"
    assert versions["transformers"] == "5.15.1"
    assert versions["qwen-vl-utils"] == "0.0.14"
    config = AutoConfig.from_pretrained(args.model_metadata, local_files_only=True)
    architecture = "Qwen3_5MoeForConditionalGeneration"
    assert config.architectures == [architecture]
    registry = Path(vllm.__file__).parent / "model_executor/models/registry.py"
    assert architecture in registry.read_text()
    processor = AutoProcessor.from_pretrained(args.model_metadata, local_files_only=True)

    png = io.BytesIO()
    Image.new("RGB", (32, 32), "red").save(png, format="PNG")
    uri = "data:image/png;base64," + base64.b64encode(png.getvalue()).decode()
    messages = [{"role": "user", "content": [
        {"type": "image", "image": uri},
        {"type": "text", "text": "Synthetic image preprocessing check."},
    ]}]
    images, videos = qwen_vl_utils.process_vision_info(
        messages, image_patch_size=config.vision_config.patch_size)
    assert len(images) == 1 and videos is None
    text = processor.apply_chat_template(messages, tokenize=False,
                                         add_generation_prompt=True,
                                         enable_thinking=False, preserve_thinking=False)
    inputs = processor(text=[text], images=images, return_tensors="pt")
    assert "pixel_values" in inputs and "image_grid_thw" in inputs
    assert all(tensor.device.type == "cpu" for tensor in inputs.values())
    assert not torch.cuda.is_initialized()

    metadata_hashes = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in args.model_metadata.iterdir() if path.is_file()
    }
    receipt = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "versions": versions, "architecture": architecture,
        "model_revision": "995ad96eacd98c81ed38be0c5b274b04031597b0",
        "metadata_path": str(args.model_metadata), "metadata_sha256": metadata_hashes,
        "processor": type(processor).__name__,
        "input_shapes": {name: list(tensor.shape) for name, tensor in inputs.items()},
        "vllm_registry_entry_present": True, "vllm_cli_module_import": True,
        "cuda_initialized": False, "model_weights_loaded": False,
        "formal_questions_evaluated": 0,
        "status": "CPU preprocessing/import checks passed; GPU execution pending",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
