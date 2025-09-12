from clingo import Control, SolveResult
from clingo import Model as ClingoModel


class Model:
    """Represents a model with its properties."""

    def __init__(self, model: ClingoModel) -> None:
        self.symbols = list(model.symbols(atoms=True))
        self.cost = model.cost
        self.optimality_proven = model.optimality_proven

    def __repr__(self) -> str:
        return f"Model({self.symbols})"


def enumerate_all_models(
    constants: list[str], file_parts: list[tuple[str, list[int]]]
) -> tuple[SolveResult, list[Model]]:
    return enumerate_models(0, constants, file_parts)


def enumerate_one_model(constants: list[str], file_parts: list[tuple[str, list[int]]]) -> tuple[SolveResult, Model]:
    return enumerate_models(1, constants, file_parts)


def enumerate_at_most_n_models(
    num_models: int, constants: list[str], file_parts: list[tuple[str, list[int]]]
) -> tuple[SolveResult, Model]:
    return enumerate_models(num_models, constants, file_parts)


def enumerate_models(
    num_models: int, constants: list[str], file_parts: list[tuple[str, list[int]]]
) -> tuple[SolveResult, list[Model]]:
    """Enumerate all models for the given constants and filenames.
    At most 10000 models are returned.
    """
    time_limit = 20

    num_models = min(num_models, 10000)
    if num_models == 0:
        num_models = 10000
    ctl_args = [f"{num_models}"]
    for p in constants:
        ctl_args.extend(["--const", str(p)])
    control = Control(ctl_args)
    encoding = ""
    for filename, parts in file_parts:
        for part in parts:
            try:
                encoding += __vfs[filename][str(part)] + "\n"
            except KeyError:
                raise ValueError(f"File '{filename}' part '{part}' not found in virtual file system.")
    control.add("base", [], encoding)
    control.ground([("base", [])])
    models = []
    with control.solve(on_model=lambda m: models.append(Model(m)), async_=True) as handle:
        handle.wait(time_limit)
        handle.cancel()
        result = handle.get()
    return result, models
