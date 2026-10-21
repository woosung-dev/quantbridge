"""미관측 시간은 측정 0초로 효율 점수를 받지 않는다."""

import pytest
from tools.research.sol_semantic_eval import paired_summary


@pytest.mark.parametrize(
    "evidence",
    [
        {"unknown_duration_calls": 1},
        {
            "attempts": [
                {
                    "generation": {
                        "status": "interrupted",
                        "duration_seconds": 180,
                        "usage": {"output_tokens": 0},
                    }
                }
            ]
        },
        {"attempts": [{"generation": {"status": "completed", "usage": {"output_tokens": 0}}}]},
    ],
)
def test_unobserved_latency_does_not_receive_five_efficiency_points(evidence):
    trial = {
        "arm": "A",
        "language": "python",
        "case_id": "01",
        "status": "public_pass",
        "semantic": {"contract_points": 40, "ledger_points": 25, "reproducibility_points": 15},
        "generation_output_tokens": 0,
        "generation_seconds": 0,
        **evidence,
    }
    assert paired_summary([trial])["cell_means"]["A/python"] == 95
