"""Deterministic Pydantic Evals helpers for CI-safe regression datasets."""

from collections.abc import Sequence

from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import EqualsExpected


def exact_match_dataset[InputT, OutputT](
    *, name: str, cases: Sequence[tuple[InputT, OutputT]]
) -> Dataset[InputT, OutputT, None]:
    """Build a deterministic exact-match dataset without model-graded evaluators."""

    return Dataset(
        name=name,
        cases=[
            Case(name=f"case-{index}", inputs=inputs, expected_output=expected)
            for index, (inputs, expected) in enumerate(cases)
        ],
        evaluators=[EqualsExpected()],
    )
