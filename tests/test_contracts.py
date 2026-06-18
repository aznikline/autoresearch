from __future__ import annotations

from autoresearch.pipeline.contracts import CONTRACTS, contract_for
from autoresearch.pipeline.stages import STAGE_SEQUENCE


def test_every_stage_has_a_contract() -> None:
    assert set(CONTRACTS) == set(STAGE_SEQUENCE)


def test_contracts_define_outputs_and_dod() -> None:
    for stage in STAGE_SEQUENCE:
        contract = contract_for(stage)
        assert contract.output_files
        assert contract.definition_of_done
