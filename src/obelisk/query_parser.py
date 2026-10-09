"""Search expression parser and evaluator.

Grammar (see docs/search.md)::

    expression := operand (operator operand)*
    operand    := TERM | NOT operand | "(" expression ")"
    operator   := AND | OR            (adjacent operands imply AND)

Operators are upper-case; lower-case words are ordinary search terms.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .errors import QueryError

_TOKEN = re.compile(r"\s*(?:(\()|(\))|([A-Za-z0-9]+(?:-[A-Za-z0-9]+)*))")

_PRECEDENCE = {"OR": 1, "NOT": 2, "AND": 3}
_UNARY = {"NOT"}
_OPERATORS = set(_PRECEDENCE)

TERM, OP, LPAREN, RPAREN = "term", "op", "(", ")"


@dataclass(frozen=True)
class Token:
    kind: str
    value: str


# --- AST -------------------------------------------------------------------


@dataclass(frozen=True)
class Term:
    value: str


@dataclass(frozen=True)
class Not:
    child: object


@dataclass(frozen=True)
class And:
    left: object
    right: object


@dataclass(frozen=True)
class Or:
    left: object
    right: object


# --- lexing ----------------------------------------------------------------


def tokenize(query: str) -> list[Token]:
    tokens: list[Token] = []
    pos = 0
    text = query.rstrip()
    while pos < len(text):
        match = _TOKEN.match(text, pos)
        if not match:
            bad = text[pos:].strip()[:1]
            raise QueryError(f"unexpected character {bad!r} in query")
        pos = match.end()
        if match.group(1):
            tokens.append(Token(LPAREN, "("))
        elif match.group(2):
            tokens.append(Token(RPAREN, ")"))
        else:
            word = match.group(3)
            if word in _OPERATORS:
                tokens.append(Token(OP, word))
            else:
                tokens.append(Token(TERM, word.lower()))
    return tokens


def _insert_implicit_and(tokens: list[Token]) -> list[Token]:
    out: list[Token] = []
    for tok in tokens:
        if out:
            prev = out[-1]
            ends_operand = prev.kind in (TERM, RPAREN)
            starts_operand = tok.kind in (TERM, LPAREN) or (
                tok.kind == OP and tok.value in _UNARY
            )
            if ends_operand and starts_operand:
                out.append(Token(OP, "AND"))
        out.append(tok)
    return out


# --- parsing (operator stack -> postfix -> tree) ------------------------------


def _to_postfix(tokens: list[Token]) -> list[Token]:
    output: list[Token] = []
    stack: list[Token] = []
    for tok in tokens:
        if tok.kind == TERM:
            output.append(tok)
        elif tok.kind == OP and tok.value in _UNARY:
            stack.append(tok)  # prefix operator: nothing to its left to flush
        elif tok.kind == OP:
            while (
                stack
                and stack[-1].kind == OP
                and _PRECEDENCE[stack[-1].value] >= _PRECEDENCE[tok.value]
            ):
                output.append(stack.pop())
            stack.append(tok)
        elif tok.kind == LPAREN:
            stack.append(tok)
        else:  # RPAREN
            while stack and stack[-1].kind != LPAREN:
                output.append(stack.pop())
            if not stack:
                raise QueryError("unbalanced parentheses: unexpected ')'")
            stack.pop()  # discard the "("
    while stack:
        top = stack.pop()
        if top.kind == LPAREN:
            raise QueryError("unbalanced parentheses: missing ')'")
        output.append(top)
    return output


def _build_tree(postfix: list[Token]):
    stack: list = []
    try:
        for tok in postfix:
            if tok.kind == TERM:
                stack.append(Term(tok.value))
            elif tok.value == "NOT":
                stack.append(Not(stack.pop()))
            else:
                right = stack.pop()
                left = stack.pop()
                stack.append(And(left, right) if tok.value == "AND" else Or(left, right))
    except IndexError:
        raise QueryError("malformed expression: operator is missing an operand")
    if len(stack) != 1:
        raise QueryError("malformed expression")
    return stack[0]


def parse(query: str):
    tokens = tokenize(query)
    if not tokens:
        raise QueryError("empty query")
    return _build_tree(_to_postfix(_insert_implicit_and(tokens)))


# --- evaluation & helpers ---------------------------------------------------


def evaluate(node, postings: dict[str, dict[str, int]], universe: set[str]) -> set[str]:
    if isinstance(node, Term):
        return set(postings.get(node.value, ()))
    if isinstance(node, Not):
        return universe - evaluate(node.child, postings, universe)
    if isinstance(node, And):
        return evaluate(node.left, postings, universe) & evaluate(
            node.right, postings, universe
        )
    return evaluate(node.left, postings, universe) | evaluate(
        node.right, postings, universe
    )


def positive_terms(node) -> list[str]:
    """Terms that contribute to relevance (those not under a NOT)."""
    if isinstance(node, Term):
        return [node.value]
    if isinstance(node, Not):
        return []
    return positive_terms(node.left) + positive_terms(node.right)


def canonical(node) -> str:
    """Fully parenthesised form; equivalent spellings share one string."""
    if isinstance(node, Term):
        return node.value
    if isinstance(node, Not):
        return f"(NOT {canonical(node.child)})"
    op = "AND" if isinstance(node, And) else "OR"
    return f"({canonical(node.left)} {op} {canonical(node.right)})"
