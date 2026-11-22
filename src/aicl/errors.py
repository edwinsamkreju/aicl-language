"""Structured diagnostics used by the AICL prototype."""
class AICLError(Exception):
    def __init__(self,code,message,*,line=None):
        super().__init__(message); self.code=code; self.message=message; self.line=line
    def as_dict(self):
        result={"code":self.code,"message":self.message}
        if self.line is not None: result["line"]=self.line
        return result
