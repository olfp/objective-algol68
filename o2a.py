import re

class O68Preprocessor:
    def __init__(self):
        self.classes = {}

    def normalize_identifier(self, name):
        """Entfernt Unterstriche und wandelt Bezeichner in Kleinbuchstaben um (A68-Regel)."""
        return name.replace("_", "").lower().strip()

    def parse_o68(self, source_code):
        """Analysiert die .o68 Struktur und extrahiert Klassen, Methoden und Felder."""
        # Whitespace-Normalisierung für einfaches Regex-Parsing
        # (Ein echter Parser würde hier über Token-Stropping laufen)
        clean_code = re.sub(r'#.*?#', '', source_code, flags=re.DOTALL) # Kommentare entfernen
        
        class_blocks = re.findall(r'(PUB\s+)?CLASS\s+(\w+)\s*(?:EXTENDS\s+(\w+))?\s*=\s*BEGIN(.*?)END\s*;', clean_code, re.DOTALL | re.IGNORECASE)
        
        for pub, class_name, extends, block_content in class_blocks:
            c_name = self.normalize_identifier(class_name)
            parent = self.normalize_identifier(extends) if extends else None
            is_pub = bool(pub)
            
            self.classes[c_name] = {
                "name": c_name, "parent": parent, "is_pub": is_pub,
                "fields": [], "methods": []
            }
            
            # Felder extrahieren (z.B. INT x;)
            fields = re.findall(r'(PUB\s+)?(INT|REAL|BOOL|CHAR|STRING)\s+(\w+)\s*;', block_content, re.IGNORECASE)
            for f_pub, f_type, f_name in fields:
                self.classes[c_name]["fields"].append({
                    "is_pub": bool(f_pub), "type": f_type.upper(), "name": self.normalize_identifier(f_name)
                })
                
            # Methoden extrahieren
            methods = re.findall(r'(PUB\s+)?(VIRTUAL|EXTEND)?\s*METHOD\s+(\w+)\s*:\s*(?:\((.*?)\))?\s*(\w+)\s*:\s*\((.*?)\)\s*;', block_content, re.DOTALL | re.IGNORECASE)
            for m_pub, m_type, m_name, m_params, m_ret, m_body in methods:
                param_list = []
                if m_params.strip():
                    # Parameter parsen (z.B. INT initx, INT inity)
                    p_pairs = re.findall(r'(\w+)\s+(\w+)', m_params)
                    for p_type, p_name in p_pairs:
                        param_list.append({"type": p_type.upper(), "name": self.normalize_identifier(p_name)})
                
                self.classes[c_name]["methods"].append({
                    "is_pub": bool(m_pub), "type": m_type.upper() if m_type else "NORMAL",
                    "name": self.normalize_identifier(m_name), "params": param_list,
                    "return": m_ret.upper(), "body": m_body.strip()
                })

    def generate_a68(self, module_name="shapesmod"):
        """Generiert den puren, regelkonformen Algol-68-Code."""
        output = [f"MODULE {module_name.lower()} =", "DEF", ""]
        
        # 1. Vorwärtsdeklaration der VMTs und Objekt-Strukturen
        output.append("    # ========================================== #")
        output.append("    # 1. TYP-DEFINITIONEN (MODES ALS BOLD-WORDS) #")
        output.append("    # ========================================== #")
        
        for c_name, c_meta in self.classes.items():
            C_NAME = c_name.upper()
            
            # VMT Struktur generieren (Sammelt alle VIRTUAL/EXTEND Methoden)
            output.append(f"    MODE {C_NAME}VMT = STRUCT(")
            vmt_fields = []
            # Hier sammeln wir virtuelle Methoden (auch geerbte)
            all_virtuals = self._get_all_virtual_methods(c_meta)
            for v_meth in all_virtuals:
                p_types = [f"REF {C_NAME}OBJ"] + [p["type"] for p in v_meth["params"]]
                vmt_fields.append(f"        REF PROC({', '.join(p_types)}) {v_meth['return']} {v_meth['name']}\n")
            output.append(",".join(vmt_fields) + "    );")
            
            # Objekt-Struktur generieren
            pub_prefix = "PUB " if c_meta["is_pub"] else ""
            output.append(f"    {pub_prefix}MODE {C_NAME}OBJ = STRUCT(")
            fields_str = []
            
            # Wenn geerbt, bette die Basisklasse als allererstes Feld ein
            if c_meta["parent"]:
                fields_str.append(f"        {c_meta['parent'].upper()}OBJ base")
            else:
                fields_str.append(f"        REF {C_NAME}VMT vmt")
                
            for f in c_meta["fields"]:
                fields_str.append(f"        {f['type']} {f['name']}")
                
            output.append(",\n".join(fields_str))
            output.append("    );")
            output.append(f"    {pub_prefix}MODE {C_NAME} = REF {C_NAME}OBJ;\n")

        # 2. Methoden-Implementierungen
        output.append("    # ========================================== #")
        output.append("    # 2. METHODEN-IMPLEMENTIERUNGEN             #")
        output.append("    # ========================================== #")
        
        for c_name, c_meta in self.classes.items():
            C_NAME = c_name.upper()
            for m in c_meta["methods"]:
                pub_prefix = "PUB " if m["is_pub"] else ""
                
                # Bei EXTEND/VIRTUAL akzeptiert die Prozedur die Basis-Struktur, um VMT-kompatibel zu sein
                if m["type"] in ["VIRTUAL", "EXTEND"] and c_meta["parent"]:
                    dispatch_type = f"REF {self._get_root_parent(c_name).upper()}OBJ"
                else:
                    dispatch_type = f"REF {C_NAME}OBJ"
                    
                p_str = [f"{dispatch_type} self"] + [f"{p['type']} {p['name']}" for p in m["params"]]
                
                output.append(f"    {pub_prefix}PROC {c_name}{m['name']} = ({', '.join(p_str)}) {m['return']}: (")
                
                # Interner Downcast, falls es sich um eine überschriebene Methode handelt
                if m["type"] in ["VIRTUAL", "EXTEND"] and c_meta["parent"]:
                    output.append(f"        {C_NAME} cself = {C_NAME}(self);")
                
                # Body-Übersetzungen (Beispielhaftes Umschreiben von super SEND / OF self)
                body = m["body"]
                body = re.sub(r'super\s+SEND\s+(\w+)\s*\((.*?)\)', rf'{c_meta["parent"]}\1(base OF self, \2)', body, flags=re.IGNORECASE)
                body = body.replace("OF self", "OF cself" if (m["type"] in ["VIRTUAL", "EXTEND"] and c_meta["parent"]) else "OF self")
                body = re.sub(r'self\s*::\s*(\w+)', r'\1(self)', body) # Parameterlose Aufrufe auflösen
                
                output.append(f"        {body}")
                output.append("    );\n")

        # 3. VMT Instanziierung & Konstruktoren
        output.append("    # ========================================== #")
        output.append("    # 3. VMT-INITIALISIERUNG & KONSTRUKTOREN     #")
        output.append("    # ========================================== #")
        for c_name, c_meta in self.classes.items():
            C_NAME = c_name.upper()
            all_virtuals = self._get_all_virtual_methods(c_meta)
            vmt_impls = [f"{self._find_method_implementer(c_name, v['name'])}{v['name']}" for v in all_virtuals]
            
            output.append(f"    {C_NAME}VMT global{c_name}vmt := ({', '.join(vmt_impls)});")
            
            # NEW-Prozedur (Konstruktor)
            init_meth = next((m for m in c_meta["methods"] if m["name"] == "init"), None)
            if init_meth:
                p_str = [f"{p['type']} {p['name']}" for p in init_meth["params"]]
                p_call = [p['name'] for p in init_meth["params"]]
                output.append(f"    PUB PROC new{c_name} = ({', '.join(p_str)}) {C_NAME}: (")
                output.append(f"        {C_NAME} instance := HEAP {C_NAME}OBJ;")
                # VMT-Zuweisung auflösen (immer an die Wurzel oder Basisstruktur)
                root_var = "base OF " * self._get_inheritance_depth(c_name) + "instance"
                output.append(f"        vmt OF {root_var.strip()} := global{c_name}vmt;")
                output.append(f"        {c_name}init(instance, {', '.join(p_call)});")
                output.append("        instance")
                output.append("    );\n")

        output.append("FED")
        return "\n".join(output)

    # --- Hilfsfunktionen für Vererbungsketten ---
    def _get_all_virtual_methods(self, c_meta):
        virtuals = [m for m in c_meta["methods"] if m["type"] in ["VIRTUAL", "EXTEND"]]
        if c_meta["parent"]:
            parent_meta = self.classes[c_meta["parent"]]
            parent_virtuals = self._get_all_virtual_methods(parent_meta)
            # Überschriebene filtern, geerbte anfügen
            local_names = [m["name"] for m in virtuals]
            for pv in parent_virtuals:
                if pv["name"] not in local_names:
                    virtuals.append(pv)
        return virtuals

    def _find_method_implementer(self, class_name, method_name):
        c_meta = self.classes[class_name]
        if any(m["name"] == method_name for m in c_meta["methods"]):
            return class_name
        if c_meta["parent"]:
            return self._find_method_implementer(c_meta["parent"], method_name)
        return class_name

    def _get_root_parent(self, class_name):
        parent = self.classes[class_name]["parent"]
        if parent:
            return self._get_root_parent(parent)
        return class_name

    def _get_inheritance_depth(self, class_name):
        parent = self.classes[class_name]["parent"]
        return 1 + self._get_inheritance_depth(parent) if parent else 0

# --- Ausführungstest ---
prep = O68Preprocessor()
prep.parse_o68(o68_source)
a68_output = prep.generate_a68()
print(a68_output)
