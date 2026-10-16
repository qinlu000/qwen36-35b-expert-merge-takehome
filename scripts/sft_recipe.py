"""The shared, user-approved LoRA SFT recipe."""
TARGET = r'model\.language_model\.layers\.\d+\.(?:self_attn\.(?:q_proj|k_proj|v_proj|o_proj)|linear_attn\.(?:in_proj_qkv|in_proj_z|in_proj_b|in_proj_a|out_proj)|mlp\.shared_expert\.(?:gate_proj|up_proj|down_proj))'
MODEL_REV = '995ad96eacd98c81ed38be0c5b274b04031597b0'
LOSS_SCALE = 'default+ignore_empty_think'


def common_args(model_path, world_size=4):
    assert world_size in (1, 2, 4)
    return ['--model', str(model_path), '--model_type', 'qwen3_5_moe', '--template', 'qwen3_5',
        '--tuner_type', 'lora', '--lora_rank', '16', '--lora_alpha', '32', '--lora_dropout', '0.05',
        '--target_regex', TARGET, '--lora_bias', 'none', '--freeze_vit', 'true', '--freeze_aligner', 'true',
        '--torch_dtype', 'bfloat16', '--attn_impl', 'sdpa', '--experts_impl', 'grouped_mm', '--deepspeed', 'zero3',
        '--split_dataset_ratio', '0', '--load_from_cache_file', 'false', '--per_device_train_batch_size', '1',
        '--gradient_accumulation_steps', str(8 // world_size), '--learning_rate', '1e-4', '--lr_scheduler_type', 'cosine',
        '--warmup_ratio', '0.03', '--optim', 'adamw_torch', '--gradient_checkpointing', 'true',
        '--gradient_checkpointing_kwargs', '{"use_reentrant":false}', '--packing', 'false', '--padding_free', 'false',
        '--enable_thinking', 'false', '--preserve_thinking', 'false', '--add_non_thinking_prefix', 'true',
        '--loss_scale', LOSS_SCALE, '--seed', '20261016', '--data_seed', '20261016', '--logging_steps', '1',
        '--save_total_limit', '2', '--save_only_model', 'true', '--report_to', 'none',
        '--dataset_num_proc', '1', '--dataloader_num_workers', '0', '--add_version', 'false']
