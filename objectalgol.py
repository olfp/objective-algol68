import re
import sys

class ClassMeta:
    def __init__(self, name, parent=None):
        self.name = name
        self.parent = parent
        self.fields = []       # List of ("TYPE", "name")
        self.methods = {}      # dict of method_signature -> {type: "VIRTUAL"/"OVERRIDE"/"EXTEND"/"METHOD", ret: "TYPE"}

class ObjectAlgolPreprocessor:
    def __init__(self):
        self.classes = {}
        self.current_class_context = None

    def parse_classes(self, source):
        """First Pass: Discover all classes, fields, and methods to map layouts."""
        class_blocks = re.findall(r'CLASS\s+(\w+)(?:\s+EXTENDS\s+(\w+))?\s*=\s*BEGIN(.*?)END\s*;', source, re.DOTALL)
        
        for name, parent, body in class_blocks:
            meta = ClassMeta(name, parent if parent else None)
            
            for line in body.split(';'):
                line = line.strip()
                if not line or "METHOD" in line:
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    field_type = " ".join(parts[:-1])
                    field_name = parts[-1]
                    meta.fields.append((field_type, field_name))
            
            # Match methods with multi-part signature tokens (e.g., VIRTUAL METHOD initX: (INT x) y: (INT y) VOID:)
            method_matches = re.finditer(r'(VIRTUAL\s+|OVERRIDE\s+|EXTEND\s+)?METHOD\s+((?:\w+:\s*\([^)]+\)\s*)+|(?:\w+:\s*))(\w+)\s*:', body)
            for m in method_matches:
                m_type = (m.group(1) or "METHOD").strip()
                raw_sig = m.group(2).strip()
                ret_type = m.group(3).strip()
                
                # Extract just the label keys for the VMT mapping name (e.g., "initX: y:" from "initX: (INT x) y: (INT y)")
                labels = re.findall(r'(\w+:)', raw_sig)
                sig = " ".join(labels)
                
                meta.methods[sig] = {"type": m_type, "ret": ret_type}
                
            self.classes[name] = meta

    def get_all_vmt_methods(self, class_name):
        """Recursively gather all functional slots belonging to a class VMT."""
        meta = self.classes.get(class_name)
        if not meta:
            return []
            
        methods = []
        if meta.parent:
            methods.extend(self.get_all_vmt_methods(meta.parent))
            
        for sig, details in meta.methods.items():
            if details["type"] in ["VIRTUAL", "EXTEND"]:
                flat_sig = sig.replace(":", "").replace(" ", "_")
                methods.append((class_name, flat_sig, details["ret"]))
        return methods

    def generate_boilerplate(self):
        """Generate valid ALGOL 68 STRUCTs, VMT declarations, and the init procedure."""
        output = []
        vmt_initializations = []
        
        for name, meta in self.classes.items():
            output.append(f"# --- Generated structures for {name} --- #")
            
            vmt_fields = []
            if meta.parent:
                vmt_fields.append(f"{meta.parent.upper()}VMT base")
            
            for base_cls, flat_sig, ret in self.get_all_vmt_methods(name):
                if base_cls == name:
                    vmt_fields.append(f"PROC(REF {name.upper()}) {ret} {flat_sig}")
            
            if vmt_fields:
                output.append(f"MODE {name.upper()}VMT = STRUCT(\n    " + ",\n    ".join(vmt_fields) + "\n);")
                output.append(f"REF {name.upper()}VMT {name.lower()} vmt;") 
            
            obj_fields = []
            if meta.parent:
                obj_fields.append(f"{meta.parent.upper()} base")
            else:
                obj_fields.append(f"REF {name.upper()}VMT vmt")
                
            for f_type, f_name in meta.fields:
                obj_fields.append(f"{f_type} {f_name}")
                
            output.append(f"MODE {name.upper()} = STRUCT(\n    " + ",\n    ".join(obj_fields) + "\n);")
            output.append("")

            bindings = []
            all_slots = self.get_all_vmt_methods(name)
            for origin_cls, flat_sig, _ in all_slots:
                impl_cls = name
                trace = meta
                while trace:
                    if flat_sig in [s.replace(":", "").replace(" ", "_") for s in trace.methods]:
                        impl_cls = trace.name
                        break
                    trace = self.classes.get(trace.parent) if trace.parent else None
                
                bindings.append(f"{impl_cls.lower()} {flat_sig}")

            binding_str = ", ".join(bindings)
            if meta.parent:
                vmt_initializations.append(f"    {name.lower()} vmt := HEAP {name.upper()}VMT := (({binding_str}));")
            else:
                vmt_initializations.append(f"    {name.lower()} vmt := HEAP {name.upper()}VMT := ({binding_str});")

        output.append("# --- Auto-Generated Global VMT Setup --- #")
        output.append("PROC init vmts = VOID: (")
        output.extend(vmt_initializations)
        output.append(");")
        output.append("")
            
        return "\n".join(output)

    def rewrite_invocations(self, match):
        """Translate complex multi-argument [receiver method: arg1 key2: arg2] expressions."""
        content = match.group(1).strip()
        
        # Parse alternating structure tokens: receiver, followed by pairs of (keyword:, value)
        # Using a regex that captures 'key:' tokens vs parameter value chunks cleanly
        tokens = re.findall(r'(\w+:|\w+)', content)
        if not tokens:
            return match.group(0)
            
        receiver = tokens[0]
        method_tokens = tokens[1:]
        
        # Static allocator sugar check: [CIRCLE new]
        if method_tokens == ["new"]:
            cls_name = receiver.upper()
            return f"( REF {cls_name} obj := HEAP {cls_name}; vmt OF obj := {receiver.lower()} vmt; obj )"
            
        sig_parts = []
        args = []
        
        # Read method labels and push intervening values out as arguments
        # Handles signatures like "initX: 10 y: 20" -> flat_sig = "initX_y", args = ["10", "20"]
        i = 0
        while i < len(method_tokens):
            tok = method_tokens[i]
            if tok.endswith(':'):
                sig_parts.append(tok)
                if i + 1 < len(method_tokens) and not method_tokens[i+1].endswith(':'):
                    args.append(method_tokens[i+1])
                    i += 1
            else:
                args.append(tok)
            i += 1
                
        sig = " ".join(sig_parts)
        flat_sig = sig.replace(":", "").replace(" ", "_")
        
        # 1. Handle Multiple Arguments inside [SUPER key1: a key2: b] Call Chains
        if receiver == "SUPER":
            if not self.current_class_context or not self.current_class_context.parent:
                print("Error: Attempted to use 'SUPER' outside of a valid derived class context.", file=sys.stderr)
                sys.exit(1)
                
            parent_cls = self.current_class_context.parent
            arg_str = ", ".join([f"(base OF self)"] + args)
            return f"({flat_sig} OF {parent_cls.lower()} vmt)({arg_str})"
            
        # 2. Handle standard multi-argument dynamic routing
        arg_str = ", ".join([receiver] + args)
        return f"({flat_sig} OF vmt OF {receiver})({arg_str})"

    def process(self, source):
        self.parse_classes(source)
        
        def class_replacer(match):
            cls_name = match.group(1)
            body_content = match.group(3)
            self.current_class_context = self.classes[cls_name]
            processed_body = re.sub(r'\[([^\]]+)\]', self.rewrite_invocations, body_content)
            self.current_class_context = None
            return processed_body

        clean_source = re.sub(r'CLASS\s+(\w+)(?:\s+EXTENDS\s+(\w+))?\s*=\s*BEGIN(.*?)END\s*;', class_replacer, source, flags=re.DOTALL)
        boilerplate = self.generate_boilerplate()
        final_source = re.sub(r'\[([^\]]+)\]', self.rewrite_invocations, clean_source)
        final_source = re.sub(r'START\s*=\s*BEGIN', 'START = \nBEGIN\n    init vmts();', final_source)
        
        return boilerplate + "\n" + final_source

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python objectalgol.py <source_file.a68>")
        sys.exit(1)
        
    with open(sys.argv, 'r') as f:
        src = f.read()
        
    compiler = ObjectAlgolPreprocessor()
    result = compiler.process(src)
    print(result)

