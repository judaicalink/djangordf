"""``Q`` objects for composing filter expressions with ``&``, ``|`` and ``~``.

A ``Q`` instance carries a connector (``AND`` or ``OR``), a negation
flag, and a list of children. Children are either other ``Q``
subtrees or ``(key, value)`` leaves built from kwargs at construction
time. The operator dunders return new ``Q`` instances; same-connector
chains are flattened so the resulting tree stays shallow.
"""
from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple, Union


_Leaf = Tuple[str, object]


class Q:
    """Composable filter expression for :py:meth:`RDFManager.filter`."""

    AND = "AND"
    OR = "OR"

    def __init__(
        self,
        *args: Union["Q", _Leaf],
        _connector: str = AND,
        _negated: bool = False,
        **kwargs: object,
    ) -> None:
        if _connector not in (Q.AND, Q.OR):
            raise ValueError(
                f"Q connector must be 'AND' or 'OR', got {_connector!r}"
            )
        children: List[Union["Q", _Leaf]] = list(args) + list(kwargs.items())
        if not children:
            raise ValueError(
                "Q requires at least one child (positional Q or kwarg)"
            )
        self.connector = _connector
        self.negated = _negated
        self.children: List[Union["Q", _Leaf]] = children

    # -- operator surface ---------------------------------------------------

    def __or__(self, other: "Q") -> "Q":
        if not isinstance(other, Q):
            return NotImplemented
        return Q._combine(self, other, Q.OR)

    def __and__(self, other: "Q") -> "Q":
        if not isinstance(other, Q):
            return NotImplemented
        return Q._combine(self, other, Q.AND)

    def __invert__(self) -> "Q":
        clone = Q.__new__(Q)
        clone.connector = self.connector
        clone.negated = not self.negated
        clone.children = list(self.children)
        return clone

    def __bool__(self) -> bool:
        raise TypeError(
            "Q is not directly usable in boolean context; "
            "compose with &/|/~ or pass to filter()"
        )

    def __repr__(self) -> str:
        prefix = "~" if self.negated else ""
        joiner = " | " if self.connector == Q.OR else " & "
        rendered = joiner.join(
            repr(child) if isinstance(child, Q) else f"({child[0]}={child[1]!r})"
            for child in self.children
        )
        return f"{prefix}({rendered})"

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def _combine(left: "Q", right: "Q", connector: str) -> "Q":
        """Combine two Q instances under ``connector``. Same-connector
        children are flattened so the tree stays shallow, but a
        negated node is treated as a single opaque subtree to preserve
        its semantics."""
        children: List[Union["Q", _Leaf]] = []
        for side in (left, right):
            if (
                isinstance(side, Q)
                and side.connector == connector
                and not side.negated
            ):
                children.extend(side.children)
            else:
                children.append(side)
        merged = Q.__new__(Q)
        merged.connector = connector
        merged.negated = False
        merged.children = children
        return merged

    @property
    def is_leaf_only(self) -> bool:
        """True when every child is a ``(key, value)`` leaf — useful for
        the byte-identical fast path in the flat filter case."""
        return all(not isinstance(child, Q) for child in self.children)

    def leaves(self) -> Iterable[_Leaf]:
        """Iterate only the direct ``(key, value)`` leaves (not Q
        children). Used by the flat path."""
        for child in self.children:
            if not isinstance(child, Q):
                yield child

    def subtrees(self) -> Sequence["Q"]:
        """Direct Q children (excluding leaves)."""
        return [child for child in self.children if isinstance(child, Q)]
