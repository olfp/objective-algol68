import re


# Algol 68 identifiers may contain blanks and underscores between name
# characters.  They are not part of the canonical identifier.  Keep the
# source spelling for diagnostics, but use the canonical spelling for all
# symbol-table operations.
_IDENTIFIER = r"[A-Za-z](?:[A-Za-z0-9]|(?:[_ ](?=[A-Za-z0-9])))*"


class O68Preprocessor:
    def __init__(self):
        self.classes = {}

    def normalize_identifier(self, name):
        """Return the canonical form of an Algol 68 identifier.

        Objective Algol 68 uses upper stropping: keywords and modes are
        written in upper case while user identifiers are written in lower
        case.  Blanks and underscores inside an identifier are ignored, as
        specified by the Algol 68 lexical rules.
        """
        if not isinstance(name, str):
            raise TypeError("identifier must be a string")

        spelling = name.strip()
        if not re.fullmatch(_IDENTIFIER, spelling):
            raise ValueError(f"invalid Algol 68 identifier: {name!r}")

        return re.sub(r"[ _]", "", spelling).lower()

    @staticmethod
    def _strip_comments(source_code):
        """Remove #...# comments without changing string literals."""
        result = []
        in_string = False
        in_comment = False
        escaped = False

        for char in source_code:
            if in_comment:
                if char == "#":
                    in_comment = False
                continue

            if char == '"' and not escaped:
                in_string = not in_string
            if char == "#" and not in_string:
                in_comment = True
                continue

            result.append(char)
            escaped = char == "\\" and not escaped
            if char != "\\":
                escaped = False

        if in_comment:
            raise ValueError("unterminated Algol 68 comment")
        if in_string:
            raise ValueError("unterminated string literal")
        return "".join(result)

    def parse_o68(self, source_code):
        """Analyse .o68 class declarations and collect their metadata.

        This remains the small source pre-parser used by the prototype.  A
        future token parser should reuse normalize_identifier() so lexical
        canonicalisation has one implementation.
        """
        clean_code = self._strip_comments(source_code)
        identifier = _IDENTIFIER

        class_blocks = re.findall(
            rf'(PUB\s+)?CLASS\s+({identifier})\s*'
            rf'(?:EXTENDS\s+({identifier}))?\s*=\s*BEGIN(.*?)END\s*;',
            clean_code, re.DOTALL | re.IGNORECASE)

        for pub, class_name, extends, block_content in class_blocks:
            c_name = self.normalize_identifier(class_name)
            parent = self.normalize_identifier(extends) if extends else None
            is_pub = bool(pub)

            self.classes[c_name] = {
                "name": c_name, "parent": parent, "is_pub": is_pub,
                "fields": [], "methods": []
            }

            fields = re.findall(
                rf'(PUB\s+)?(INT|REAL|BOOL|CHAR|STRING)\s+({identifier})\s*;',
                block_content, re.IGNORECASE)
            for f_pub, f_type, f_name in fields:
                self.classes[c_name]["fields"].append({
                    "is_pub": bool(f_pub), "type": f_type.upper(),
                    "name": self.normalize_identifier(f_name)
                })

            methods = re.findall(
                rf'(PUB\s+)?(VIRTUAL|EXTEND)?\s*METHOD\s+({identifier})\s*:\s*'
                rf'(?:\((.*?)\))?\s*({identifier})\s*:\s*\((.*?)\)\s*;',
                block_content, re.DOTALL | re.IGNORECASE)
            for m_pub, m_type, m_name, m_params, m_ret, m_body in methods:
                param_list = []
                if m_params.strip():
                    p_pairs = re.findall(
                        rf'({identifier})\s+({identifier})', m_params)
                    for p_type, p_name in p_pairs:
                        param_list.append({
                            "type": self.normalize_identifier(p_type).upper(),
                            "name": self.normalize_identifier(p_name)
                        })

                self.classes[c_name]["methods"].append({
                    "is_pub": bool(m_pub),
                    "type": m_type.upper() if m_type else "NORMAL",
                    "name": self.normalize_identifier(m_name),
                    "params": param_list,
                    "return": self.normalize_identifier(m_ret).upper(),
                    "body": m_body.strip()
                })

    def generate_a68(self, module_name="shapesmod"):
        """Generate the pure Algol-68-like target representation."""
        output = [f"MODULE {module_name.lower()} =", "DEF", ""]

        output.append("    # ========================================== #")
        output.append("    # 1. TYP-DEFINITIONEN (MODES ALS BOLD-WORDS) #")
        output.append("    # ========================================== #")

        for c_name, c_meta in self.classes.items():
            C_NAME = c_name.upper()
            output.append(f"    MODE {C_NAME}VMT = STRUCT(")
            vmt_fields = []
            all_virtuals = self._get_all_virtual_methods(c_meta)
            for v_meth in all_virtuals:
                p_types = [f"REF {C_NAME}OBJ"] + [p["type"] for p in v_meth["params"]]
                vmt_fields.append(
                    f"        REF PROC({', '.join(p_types)}) {v_meth['return']} {v_meth['name']}\n")
            output.append(",".join(vmt_fields) + "    );")

            pub_prefix = "PUB " if c_meta["is_pub"] else ""
            output.append(f"    {pub_prefix}MODE {C_NAME}OBJ = STRUCT(")
            fields_str = []
            if c_meta["parent"]:
                fields_str.append(f"        {c_meta['parent'].upper()}OBJ base")
            else:
                fields_str.append(f"        REF {C_NAME}VMT vmt")

            for f in c_meta["fields"]:
                fields_str.append(f"        {f['type']} {f['name']}")
            output.append(",\n".join(fields_str))
            output.append("    );")
            output.append(f"    {pub_prefix}MODE {C_NAME} = REF {C_NAME}OBJ;\n")

        output.append("    # ========================================== #")
        output.append("    # 2. METHODEN-IMPLEMENTIERUNGEN             #")
        output.append("    # ========================================== #")

        for c_name, c_meta in self.classes.items():
            C_NAME = c_name.upper()
            for m in c_meta["methods"]:
                pub_prefix = "PUB " if m["is_pub"] else ""
                if m["type"] in ["VIRTUAL", "EXTEND"] and c_meta["parent"]:
                    dispatch_type = f"REF {self._get_root_parent(c_name).upper()}OBJ"
                else:
                    dispatch_type = f"REF {C_NAME}OBJ"

                p_str = [f"{dispatch_type} self"] + [
                    f"{p['type']} {p['name']}" for p in m["params"]]
                output.append(
                    f"    {pub_prefix}PROC {c_name}{m['name']} = "
                    f"({', '.join(p_str)}) {m['return']}: (")

                if m["type"] in ["VIRTUAL", "EXTEND"] and c_meta["parent"]:
                    output.append(f"        {C_NAME} cself = {C_NAME}(self);")

                body = m["body"]
                body = re.sub(
                    rf'super\s+SEND\s+({identifier})\s*\((.*?)\)',
                    rf'{c_meta["parent"]}\\1(base OF self, \\2)',
                    body, flags=re.IGNORECASE)
                body = body.replace(
                    "OF self", "OF cself" if
                    (m["type"] in ["VIRTUAL", "EXTEND"] and c_meta["parent"])
                    else "OF self")
                body = re.sub(
                    rf'self\s*::\s*({identifier})', r'\1(self)', body,
                    flags=re.IGNORECASE)

                output.append(f"        {body}")
                output.append("    );\n")

        output.append("    # ========================================== #")
        output.append("    # 3. VMT-INITIALISIERUNG & KONSTRUKTOREN     #")
        output.append("    # ========================================== #")
        for c_name, c_meta in self.classes.items():
            C_NAME = c_name.upper()
            all_virtuals = self._get_all_virtual_methods(c_meta)
            vmt_impls = [
                f"{self._find_method_implementer(c_name, v['name'])}{v['name']}"
                for v in all_virtuals]
            output.append(
                f"    {C_NAME}VMT global{c_name}vmt := ({', '.join(vmt_impls)});")

            init_meth = next((m for m in c_meta["methods"] if m["name"] == "init"), None)
            if init_meth:
                p_str = [f"{p['type']} {p['name']}" for p in init_meth["params"]]
                p_call = [p["name"] for p in init_meth["params"]]
                output.append(
                    f"    PUB PROC new{c_name} = ({', '.join(p_str)}) {C_NAME}: (")
                output.append(f"        {C_NAME} instance := HEAP {C_NAME}OBJ;")
                root_var = "base OF " * self._get_inheritance_depth(c_name) + "instance"
                output.append(
                    f"        vmt OF {root_var.strip()} := global{c_name}vmt;")
                output.append(f"        {c_name}init(instance, {', '.join(p_call)});")
                output.append("        instance")
                output.append("    );\n")

        output.append("FED")
        return "\n".join(output)

    def _get_all_virtual_methods(self, c_meta):
        virtuals = [m for m in c_meta["methods"] if m["type"] in ["VIRTUAL", "EXTEND"]]
        if c_meta["parent"]:
            parent_meta = self.classes[c_meta["parent"]]
            parent_virtuals = self._get_all_virtual_methods(parent_meta)
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


if __name__ == "__main__":
    print("O68Preprocessor loaded; provide source text to parse_o68().")
