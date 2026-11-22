"""Lexer, expression parser, and compact AICL-C 0.1 module parser.

This is an intentionally small, line-oriented prototype grammar. It is not the
complete language described in the project report.
"""
from __future__ import annotations
from dataclasses import dataclass
import json
import re
from typing import Any
from .errors import AICLError

@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    offset: int

@dataclass(frozen=True)
class Expr:
    kind: str
    value: Any = None
    children: tuple["Expr", ...] = ()

@dataclass(frozen=True)
class Parameter:
    name: str
    type_name: str

@dataclass(frozen=True)
class Function:
    name: str
    parameters: tuple[Parameter, ...]
    return_type: str
    body: Expr
    effect: str
    line_index: int
    source_line: str

@dataclass(frozen=True)
class Constant:
    name: str
    type_name: str
    value: Expr
    line_index: int
    source_line: str

@dataclass(frozen=True)
class Program:
    version: str
    functions: tuple[Function, ...]
    constants: tuple[Constant, ...]
    source_lines: tuple[str, ...]

_TOKEN_RE = re.compile(
    r"(?P<SPACE>\s+)|(?P<NUMBER>(?:\d+\.\d+|\d+))"
    r'|(?P<STRING>"(?:\\.|[^"\\])*")'
    r"|(?P<OP>\|>|->|==|!=|<=|>=|&&|\|\||[!()+\-*/%<>,])"
    r"|(?P<IDENT>[A-Za-z_][A-Za-z0-9_]*)"
)

class ExpressionParser:
    PRECEDENCE = {"|>":1,"||":2,"&&":3,"==":4,"!=":4,"<":4,"<=":4,">":4,">=":4,"+":5,"-":5,"*":6,"/":6,"%":6}
    def __init__(self, source: str) -> None:
        self.source=source; self.tokens=self._lex(source); self.index=0
    @staticmethod
    def _lex(source: str) -> list[Token]:
        tokens=[]; position=0
        while position < len(source):
            match=_TOKEN_RE.match(source,position)
            if not match: raise AICLError("E-PARSE-001",f"Unexpected character near {source[position:position+16]!r}")
            kind=match.lastgroup; value=match.group()
            if kind!="SPACE": tokens.append(Token(kind or "",value,position))
            position=match.end()
        tokens.append(Token("EOF","",len(source))); return tokens
    def peek(self): return self.tokens[self.index]
    def take(self, expected=None):
        token=self.peek()
        if expected is not None and token.value!=expected:
            raise AICLError("E-PARSE-002",f"Expected {expected!r}, found {token.value!r} at offset {token.offset}")
        self.index+=1; return token
    def parse(self):
        expression=self.parse_expression(0)
        if self.peek().kind!="EOF":
            t=self.peek(); raise AICLError("E-PARSE-003",f"Unexpected token {t.value!r} at offset {t.offset}")
        return expression
    def parse_expression(self, minimum_precedence):
        left=self.parse_prefix()
        while True:
            token=self.peek()
            if token.value=="(":
                if 8<minimum_precedence: break
                if left.kind!="name": raise AICLError("E-PARSE-004","Only named functions can be called in AICL-C 0.1")
                self.take("("); args=[]
                if self.peek().value!=")":
                    while True:
                        args.append(self.parse_expression(0))
                        if self.peek().value!=",": break
                        self.take(",")
                self.take(")"); left=Expr("call",left.value,tuple(args)); continue
            precedence=self.PRECEDENCE.get(token.value)
            if precedence is None or precedence<minimum_precedence: break
            operator=self.take().value; right=self.parse_expression(precedence+1)
            left=Expr("pipe",None,(left,right)) if operator=="|>" else Expr("binary",operator,(left,right))
        return left
    def parse_prefix(self):
        token=self.take()
        if token.kind=="NUMBER": return Expr("literal",float(token.value) if "." in token.value else int(token.value))
        if token.kind=="STRING":
            try: return Expr("literal",json.loads(token.value))
            except json.JSONDecodeError as exc: raise AICLError("E-PARSE-005",f"Invalid string literal: {exc.msg}") from exc
        if token.kind=="IDENT":
            if token.value in {"true","false"}: return Expr("literal",token.value=="true")
            return Expr("name",token.value)
        if token.value in {"-","!"}: return Expr("unary",token.value,(self.parse_expression(7),))
        if token.value=="(":
            expression=self.parse_expression(0); self.take(")"); return expression
        raise AICLError("E-PARSE-006",f"Expected an expression, found {token.value!r} at offset {token.offset}")

def parse_expression(source: str) -> Expr: return ExpressionParser(source).parse()

def split_top_level(source: str, separator: str=",") -> list[str]:
    parts=[]; depth=0; quote=None; escaped=False; start=0
    for index,character in enumerate(source):
        if quote:
            if escaped: escaped=False
            elif character=="\\": escaped=True
            elif character==quote: quote=None
            continue
        if character in {'"',"'"}: quote=character
        elif character in "([": depth+=1
        elif character in ")]": depth-=1
        elif character==separator and depth==0:
            parts.append(source[start:index].strip()); start=index+1
    tail=source[start:].strip()
    if tail: parts.append(tail)
    return parts

def parse_type(source: str) -> str:
    value=source.strip()
    if value in {"i64","f64","bool","Str"}: return value
    match=re.fullmatch(r"List\[(.+)\]",value)
    if match: return f"List[{parse_type(match.group(1))}]"
    raise AICLError("E-TYPE-001",f"Unsupported type in AICL-C 0.1: {value!r}")

_FUNCTION_RE=re.compile(r"^f\s+([A-Za-z_][A-Za-z0-9_]*)\s*\((.*?)\)\s*->\s*(.+?)(?:\s+(!pure|!\{[^}]*\}))?\s*=\s*(.+)$")
_CONSTANT_RE=re.compile(r"^c\s+([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.+?)\s*=\s*(.+)$")

def parse_module(source: str) -> Program:
    lines=source.splitlines(); version=None; functions=[]; constants=[]; function_names=set(); constant_names=set()
    for line_index,original_line in enumerate(lines):
        line=original_line.strip()
        if not line or line.startswith("#"): continue
        if version is None:
            match=re.fullmatch(r"aicl\s+(\d+\.\d+)",line)
            if not match: raise AICLError("E-PARSE-010","The first non-comment line must declare `aicl 0.1`",line=line_index+1)
            version=match.group(1)
            if version!="0.1": raise AICLError("E-VERSION-001",f"This prototype supports AICL 0.1, not {version}",line=line_index+1)
            continue
        fm=_FUNCTION_RE.fullmatch(line)
        if fm:
            name,raw_parameters,raw_return,effect,raw_body=fm.groups()
            if name in function_names or name in constant_names: raise AICLError("E-RESOLVE-001",f"Duplicate declaration {name!r}",line=line_index+1)
            if effect not in {None,"!pure"}: raise AICLError("E-EFFECT-001","AICL-C 0.1 prototype accepts only !pure; host capabilities are not implemented",line=line_index+1)
            parameters=[]
            for raw in split_top_level(raw_parameters):
                if ":" not in raw: raise AICLError("E-PARSE-011",f"Parameter must have name:type form: {raw!r}",line=line_index+1)
                pname,ptype=raw.split(":",1); pname=pname.strip()
                if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*",pname): raise AICLError("E-PARSE-012",f"Invalid parameter name {pname!r}",line=line_index+1)
                if any(p.name==pname for p in parameters): raise AICLError("E-RESOLVE-002",f"Duplicate parameter {pname!r}",line=line_index+1)
                parameters.append(Parameter(pname,parse_type(ptype)))
            functions.append(Function(name,tuple(parameters),parse_type(raw_return),parse_expression(raw_body),"pure",line_index,original_line))
            function_names.add(name); continue
        cm=_CONSTANT_RE.fullmatch(line)
        if cm:
            name,raw_type,raw_value=cm.groups()
            if name in constant_names or name in function_names: raise AICLError("E-RESOLVE-001",f"Duplicate declaration {name!r}",line=line_index+1)
            constants.append(Constant(name,parse_type(raw_type),parse_expression(raw_value),line_index,original_line)); constant_names.add(name); continue
        if line.startswith("u "): raise AICLError("E-FEATURE-001","Imports are reserved for a later MVP phase; use built-ins in AICL-C 0.1",line=line_index+1)
        raise AICLError("E-PARSE-013",f"Unrecognised declaration: {line!r}",line=line_index+1)
    if version is None: raise AICLError("E-PARSE-014","Missing AICL version declaration")
    if not functions and not constants: raise AICLError("E-PARSE-015","Module must declare at least one constant or function")
    return Program(version,tuple(functions),tuple(constants),tuple(lines))
