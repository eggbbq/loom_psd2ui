from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Diagnostic:
    code: str
    severity: str
    psdPath: str
    message: str

    def to_dict(self):
        return asdict(self)


class ExportError(Exception):
    """A structural error that must fail even outside strict mode."""


class Diagnostics:
    def __init__(self):
        self.items: list[Diagnostic] = []

    def warn(self, code, path, message):
        self.items.append(Diagnostic(code, "warning", path, message))

    def fail(self, code, path, message):
        self.items.append(Diagnostic(code, "error", path, message))
        raise ExportError(message)

    def failed(self, strict=False):
        return any(d.severity == "error" or
                   (strict and d.code != "DUPLICATE_ASSET_PATH") for d in self.items)

