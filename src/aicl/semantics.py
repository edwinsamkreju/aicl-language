"""Static type checking and bounded reference interpreter for AICL-C 0.1."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable
from .errors import AICLError
from .syntax import Expr, Program

NUMERIC={"i64","f64"}

def _list_item(t):
    if not (t.startswith("List[") and t.endswith("]")): raise AICLError("E-TYPE-010",f"Expected List[T], received {t}")
    return t[5:-1]

def _expect(actual,expected,context):
    if actual!=expected: raise AICLError("E-TYPE-011",f"{context}: expected {expected}, received {actual}")

def _callable_type(name,program):
    if name=="trim": return ("Str","Str")
    if name=="not_empty": return ("Str","bool")
    for f in program.functions:
        if f.name==name and len(f.parameters)==1: return (f.parameters[0].type_name,f.return_type)
    return None

class TypeChecker:
    def __init__(self,program):
        self.program=program; self.functions={f.name:f for f in program.functions}
        self.node_types={}
    def check(self):
        env={}
        for c in self.program.constants:
            actual=self.infer(c.value,env,f"const:{c.name}:value"); _expect(actual,c.type_name,f"constant {c.name}"); env[c.name]=c.type_name
        for f in self.program.functions:
            local={p.name:p.type_name for p in f.parameters}; local.update(env)
            actual=self.infer(f.body,local,f"fn:{f.name}:body"); _expect(actual,f.return_type,f"function {f.name} return type")
        return dict(self.node_types)
    def infer(self,e,env,path):
        k=e.kind
        if k=="literal":
            v=e.value
            if isinstance(v,int) and not isinstance(v,bool) and not -(2**63)<=v<2**63: raise AICLError("E-TYPE-028","Integer literal is outside the signed i64 range")
            t="bool" if isinstance(v,bool) else "Str" if isinstance(v,str) else "i64" if isinstance(v,int) else "f64"
        elif k=="name":
            if e.value not in env: raise AICLError("E-RESOLVE-010",f"Unknown value {e.value!r}")
            t=env[e.value]
        elif k=="unary":
            a=self.infer(e.children[0],env,path+"/operand")
            if e.value=="-" and a in NUMERIC: t=a
            elif e.value=="!" and a=="bool": t="bool"
            else: raise AICLError("E-TYPE-012",f"Operator {e.value} is not defined for {a}")
        elif k=="binary":
            a=self.infer(e.children[0],env,path+"/left"); b=self.infer(e.children[1],env,path+"/right"); op=e.value
            if op in {"+","-","*","/","%"}:
                if a==b and a in NUMERIC: t="f64" if op=="/" and a in {"i32","i64"} else a
                elif op=="+" and a==b=="Str": t="Str"
                else: raise AICLError("E-TYPE-013",f"Cannot apply {op} to {a} and {b}")
            elif op in {"<","<=",">",">="}:
                if a!=b or a not in NUMERIC|{"Str"}: raise AICLError("E-TYPE-014",f"Cannot compare {a} and {b} with {op}")
                t="bool"
            elif op in {"==","!="}:
                if a!=b: raise AICLError("E-TYPE-015",f"Equality requires matching types, received {a} and {b}")
                t="bool"
            elif op in {"&&","||"}: _expect(a,"bool",f"left operand of {op}"); _expect(b,"bool",f"right operand of {op}"); t="bool"
            else: raise AICLError("E-TYPE-016",f"Unsupported operator {op}")
        elif k=="call": t=self._call(str(e.value),e.children,env,path)
        elif k=="pipe":
            left,right=e.children; self.infer(left,env,path+"/left")
            if right.kind=="name": t=self._call(str(right.value),(left,),env,path+"/right")
            elif right.kind=="call": t=self._call(str(right.value),(left,*right.children),env,path+"/right")
            else: raise AICLError("E-TYPE-018","The right side of |> must be a function name or call")
            self.node_types[path+"/right"]=t
        else: raise AICLError("E-TYPE-017",f"Unknown expression node {k!r}")
        self.node_types[path]=t; return t
    def _call(self,name,args,env,path):
        if name in {"min","max"}:
            if len(args)!=2: raise AICLError("E-TYPE-020",f"{name} expects exactly two arguments")
            a=self.infer(args[0],env,path+"/arg0"); b=self.infer(args[1],env,path+"/arg1")
            if a!=b or a not in NUMERIC: raise AICLError("E-TYPE-021",f"{name} requires two values of the same numeric type")
            return a
        if name in {"trim","not_empty","abs","len"}:
            if len(args)!=1: raise AICLError("E-TYPE-022",f"{name} expects exactly one argument")
            a=self.infer(args[0],env,path+"/arg0")
            if name in {"trim","not_empty"}: _expect(a,"Str",name); return "Str" if name=="trim" else "bool"
            if name=="abs":
                if a not in NUMERIC: raise AICLError("E-TYPE-023","abs expects a numeric argument")
                return a
            if a=="Str" or a.startswith("List["): return "i64"
            raise AICLError("E-TYPE-024","len expects Str or List[T]")
        if name=="unique":
            if len(args)!=1: raise AICLError("E-TYPE-025","unique expects exactly one argument")
            a=self.infer(args[0],env,path+"/arg0"); _list_item(a); return a
        if name in {"map","filter"}:
            if len(args)!=2 or args[1].kind!="name": raise AICLError("E-TYPE-026",f"{name} expects a list and a named unary function")
            lt=self.infer(args[0],env,path+"/arg0"); item=_list_item(lt); cb=_callable_type(str(args[1].value),self.program)
            if cb is None: raise AICLError("E-RESOLVE-011",f"Unknown unary function {args[1].value!r}")
            _expect(item,cb[0],f"{name} callback input"); self.node_types[path+"/arg1"]=f"Fn[{cb[0]},{cb[1]}]"
            if name=="filter": _expect(cb[1],"bool","filter callback result"); return lt
            return f"List[{cb[1]}]"
        f=self.functions.get(name)
        if f is None: raise AICLError("E-RESOLVE-012",f"Unknown function {name!r}")
        if len(args)!=len(f.parameters): raise AICLError("E-TYPE-027",f"{name} expects {len(f.parameters)} arguments, received {len(args)}")
        for i,(arg,p) in enumerate(zip(args,f.parameters)): _expect(self.infer(arg,env,f"{path}/arg{i}"),p.type_name,f"argument {p.name} of {name}")
        return f.return_type

@dataclass
class ExecutionBudget:
    max_steps:int=100_000
    max_depth:int=128
    steps:int=0
    def tick(self):
        self.steps+=1
        if self.steps>self.max_steps: raise AICLError("E-RUN-001",f"Execution step budget exceeded ({self.max_steps})")

@dataclass(frozen=True)
class FunctionReference:
    name:str

class Interpreter:
    def __init__(self,program,*,budget=None):
        self.program=program; self.functions={f.name:f for f in program.functions}; self.budget=budget or ExecutionBudget(); self.constants={}
        TypeChecker(program).check()
        for c in program.constants: self.constants[c.name]=self.evaluate(c.value,{},0)
    def call(self,name,arguments):
        f=self.functions.get(name)
        if f is None: raise AICLError("E-RUN-002",f"Function {name!r} does not exist")
        if len(arguments)!=len(f.parameters): raise AICLError("E-RUN-003",f"{name} expects {len(f.parameters)} arguments, received {len(arguments)}")
        env=dict(self.constants); env.update({p.name:v for p,v in zip(f.parameters,arguments)})
        return self._call_function(f,env,0)
    def _call_function(self,f,env,depth):
        if depth>=self.budget.max_depth: raise AICLError("E-RUN-004",f"Maximum call depth exceeded ({self.budget.max_depth})")
        self.budget.tick(); return self.evaluate(f.body,env,depth+1)
    def evaluate(self,e,env,depth):
        self.budget.tick(); k=e.kind
        if k=="literal": return e.value
        if k=="name":
            if e.value in env: return env[e.value]
            if e.value in self.constants: return self.constants[e.value]
            if e.value in self.functions or e.value in {"min","max","trim","not_empty","abs","len","unique","map","filter"}: return FunctionReference(e.value)
            raise AICLError("E-RUN-010",f"Unknown value {e.value!r}")
        if k=="unary":
            v=self.evaluate(e.children[0],env,depth); return -v if e.value=="-" else not v
        if k=="binary":
            a=self.evaluate(e.children[0],env,depth)
            if e.value=="&&": return bool(a) and bool(self.evaluate(e.children[1],env,depth))
            if e.value=="||": return bool(a) or bool(self.evaluate(e.children[1],env,depth))
            b=self.evaluate(e.children[1],env,depth)
            ops={"+":lambda x,y:x+y,"-":lambda x,y:x-y,"*":lambda x,y:x*y,"/":lambda x,y:x/y,"%":lambda x,y:x%y,"==":lambda x,y:x==y,"!=":lambda x,y:x!=y,"<":lambda x,y:x<y,"<=":lambda x,y:x<=y,">":lambda x,y:x>y,">=":lambda x,y:x>=y}
            try: return ops[e.value](a,b)
            except (ArithmeticError,TypeError) as exc: raise AICLError("E-RUN-011",f"Operator {e.value} failed: {exc}") from exc
        if k=="call": return self._invoke(e.value,[self.evaluate(x,env,depth) for x in e.children],depth)
        if k=="pipe":
            left,right=e.children; first=self.evaluate(left,env,depth)
            if right.kind=="name": return self._invoke(right.value,[first],depth)
            if right.kind=="call": return self._invoke(right.value,[first,*[self.evaluate(x,env,depth) for x in right.children]],depth)
            raise AICLError("E-RUN-012","Invalid pipeline target")
        raise AICLError("E-RUN-013",f"Unknown expression node {k!r}")
    def _invoke(self,name,args,depth):
        self.budget.tick()
        if name in {"min","max"}: self._arity(name,args,2); return min(args) if name=="min" else max(args)
        if name=="trim": self._arity(name,args,1); return args[0].strip()
        if name=="not_empty": self._arity(name,args,1); return bool(args[0].strip())
        if name=="abs": self._arity(name,args,1); return abs(args[0])
        if name=="len": self._arity(name,args,1); return len(args[0])
        if name=="unique":
            self._arity(name,args,1)
            if len(args[0])>10000: raise AICLError("E-RUN-018","Collection exceeds the 10,000-item prototype limit")
            out=[]
            for item in args[0]:
                self.budget.tick()
                if item not in out: out.append(item)
            return out
        if name in {"map","filter"}:
            self._arity(name,args,2); values,callback=args
            if not isinstance(callback,FunctionReference): raise AICLError("E-RUN-014",f"{name} callback must be a function name")
            if len(values)>10000: raise AICLError("E-RUN-018","Collection exceeds the 10,000-item prototype limit")
            out=[]
            for item in values:
                self.budget.tick(); result=self._invoke(callback.name,[item],depth+1)
                if name=="map": out.append(result)
                elif result: out.append(item)
            return out
        f=self.functions.get(name)
        if f is None: raise AICLError("E-RUN-015",f"Unknown function {name!r}")
        if len(args)!=len(f.parameters): raise AICLError("E-RUN-016",f"{name} expects {len(f.parameters)} arguments, received {len(args)}")
        env=dict(self.constants); env.update({p.name:v for p,v in zip(f.parameters,args)})
        return self._call_function(f,env,depth)
    @staticmethod
    def _arity(name,args,n):
        if len(args)!=n: raise AICLError("E-RUN-017",f"{name} expects {n} arguments, received {len(args)}")

def check_program(program): return TypeChecker(program).check()

def _matches_type(value,t):
    if t=="bool": return isinstance(value,bool)
    if t=="Str": return isinstance(value,str)
    if t in {"i32","i64"}: return isinstance(value,int) and not isinstance(value,bool)
    if t in {"f32","f64"}: return isinstance(value,(int,float)) and not isinstance(value,bool)
    if t.startswith("List["): return isinstance(value,list) and all(_matches_type(x,t[5:-1]) for x in value)
    return False

def run_function(program,name,arguments,*,budget=None):
    f=next((x for x in program.functions if x.name==name),None)
    if f is None: raise AICLError("E-RUN-020",f"Function {name!r} does not exist")
    if len(arguments)!=len(f.parameters): raise AICLError("E-RUN-021",f"{name} expects {len(f.parameters)} arguments, received {len(arguments)}")
    for p,v in zip(f.parameters,arguments):
        if not _matches_type(v,p.type_name): raise AICLError("E-RUN-022",f"Argument {p.name} must match {p.type_name}")
    result=Interpreter(program,budget=budget).call(name,arguments)
    if not _matches_type(result,f.return_type): raise AICLError("E-RUN-023",f"Runtime result for {name} did not match declared type {f.return_type}")
    return result
