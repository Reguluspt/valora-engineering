from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.schema import CheckConstraint


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy database models."""
    pass


@compiles(CheckConstraint, "sqlite")
def _compile_check_constraint_sqlite(element, compiler, **kw):
    sql = str(element.sqltext)
    if "~" in sql:
        return None
    name = compiler.preparer.format_constraint(element) if element.name else None
    if name:
        return f"CONSTRAINT {name} CHECK ({sql})"
    return f"CHECK ({sql})"
