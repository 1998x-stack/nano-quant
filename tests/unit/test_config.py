"""Schema checks prevent misinterpreted financial scenario inputs."""

import json
from decimal import Decimal
from pathlib import Path

import pytest

from nano_quant.core import ContractError
from nano_quant.core.config import SmokeConfig, load_smoke_config


def test_load_golden_config() -> None:
    cfg = load_smoke_config(Path("examples/phase_b_golden.json"))
    assert cfg.initial_cash == Decimal("1000.00")
    assert cfg.quantity == 10
    assert cfg.fee == Decimal("1.00")
    assert cfg.slippage_bps == Decimal("10")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("initial_cash", Decimal("0")),
        ("initial_cash", Decimal("NaN")),
        ("quantity", 0),
        ("quantity", True),
        ("fee", Decimal("-1")),
        ("slippage_bps", Decimal("10001")),
    ],
)
def test_config_rejects_bad_values(field: str, value: object) -> None:
    with pytest.raises(ContractError):
        SmokeConfig(**{field: value})


def test_config_rejects_unknown_or_missing_fields(tmp_path: Path) -> None:
    data = json.loads(Path("examples/phase_b_golden.json").read_text(encoding="utf-8"))
    data["unrecognized"] = True
    file = tmp_path / "config.json"
    file.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ContractError, match="unknown/missing"):
        load_smoke_config(file)
    data.pop("unrecognized")
    data.pop("quantity")
    file.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ContractError, match="unknown/missing"):
        load_smoke_config(file)


def test_config_rejects_float_money_and_malformed_decimal(tmp_path: Path) -> None:
    data = json.loads(Path("examples/phase_b_golden.json").read_text(encoding="utf-8"))
    file = tmp_path / "config.json"
    data["fee_usd"] = 1.0
    file.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ContractError, match="decimal string"):
        load_smoke_config(file)
    data["fee_usd"] = "garbage"
    file.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ContractError, match="invalid decimal"):
        load_smoke_config(file)
