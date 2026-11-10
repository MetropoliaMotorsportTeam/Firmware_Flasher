from flasher.config import FlashConfig, load_config_file, merge_configs


def test_load_config_file_reads_toml(tmp_path):
    p = tmp_path / "flash.toml"
    p.write_text('backend = "socketcan"\nport = "can0"\nbaud = 1000000\n')
    cfg = load_config_file(str(p))
    assert cfg.backend == "socketcan"
    assert cfg.port == "can0"
    assert cfg.baud == 1000000
    assert cfg.retries is None


def test_merge_configs_cli_overrides_file():
    file_cfg = FlashConfig(
        backend="socketcan", port="can0", baud=1000000, retries=None, timeout_ms=None, firmware_path=None
    )
    cli_cfg = FlashConfig(
        backend=None, port="can1", baud=None, retries=None, timeout_ms=None, firmware_path="fw.bin"
    )
    merged = merge_configs(file_cfg, cli_cfg)
    assert merged.backend == "socketcan"  # from file, CLI didn't set it
    assert merged.port == "can1"  # CLI overrides file
    assert merged.firmware_path == "fw.bin"
