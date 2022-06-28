import enum
from typing import Any, cast, Type


class TcProcedureType(enum.Enum):
    DEFAULT = 0
    CFDP = 1
    CUSTOM = 2


class TcProcedureBase:
    def __init__(self, ptype: TcProcedureType):
        self.ptype = ptype


class CustomProcedureInfo(TcProcedureBase):
    def __init__(self, info: any):
        super().__init__(TcProcedureType.CUSTOM)
        self.info = info

    def __repr__(self):
        return f"{self.__class__.__name__}(info={self.info!r}"


class DefaultProcedureInfo(TcProcedureBase):
    """Generic abstraction for procedures. A procedure can be a single command or a sequence
    of commands. Generally, one procedure is mapped to a specific TC queue which is packed
    during run-time"""

    def __init__(self, service: str, op_code: str):
        super().__init__(TcProcedureType.DEFAULT)
        self.service = service
        self.op_code = op_code

    def __repr__(self):
        return f"CmdInfo(service={self.service!r}, op_code={self.op_code!r})"


class ProcedureCastWrapper:
    """Cast wrapper to cast the procedure base type back to a concrete type easily"""

    def __init__(self, base: TcProcedureBase):
        self.base = base

    def __cast_internally(
        self,
        obj_type: Type[TcProcedureBase],
        obj: TcProcedureBase,
        expected_type: TcProcedureType,
    ) -> Any:
        if obj.ptype != expected_type:
            raise TypeError(f"Invalid object {obj} for type {self.base.ptype}")
        return cast(obj_type, obj)

    def to_def_procedure(self) -> DefaultProcedureInfo:
        return self.__cast_internally(
            DefaultProcedureInfo, self.base, TcProcedureType.DEFAULT
        )

    def to_custom_procedure(self) -> CustomProcedureInfo:
        return self.__cast_internally(
            CustomProcedureInfo, self.base, TcProcedureType.CUSTOM
        )