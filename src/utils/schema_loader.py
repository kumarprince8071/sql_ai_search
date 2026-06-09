import json
import os
from collections import defaultdict
from src.utils.logger import logger

class SchemaManager:
    """Loads a flat Semantic Schema JSON and dynamically reconstructs it into an Agent-ready hierarchy."""
    
    def __init__(self, filepath: str = "src/metadata/harmonia_schema.json"):
        self.filepath = filepath
        self.raw_data = self.load_schema()
        self.schema = self.build_nested_schema()
        
    def load_schema(self) -> list:
        """ Loads the JSON Schema """

        if not os.path.exists(self.filepath):
            logger.error(f"Schema file not found at {self.filepath}")
            return []            
        try:
            with open(self.filepath, 'r') as f:
                schema_data = json.load(f)
                return schema_data
        except Exception as e:
            logger.error(f"Failed to parse Semantic Schema JSON: {e}")
            return []

    def build_nested_schema(self) -> dict:
        """
        Takes the flat list of fields and builds the nested dictionary the LLMs expect.
        Translates 'field_name' -> 'column_name' and 'alias' -> 'aliases'.
        """
        if not self.raw_data:
            return {}
        join_registry = {
            "employee_inouttime": [
                {"column": "GlobalUserID", "references_table": "employee_master", "references_column": "GlobalUserId"}
            ],
            "employee_leavebalance": [
                {"column": "GlobalUserID", "references_table": "employee_master", "references_column": "GlobalUserId"}
            ],
            "employee_leavetaken": [
                {"column": "GlobalUserID", "references_table": "employee_master", "references_column": "GlobalUserId"}
            ],
            "manager_master": [
                {"column": "ManagerId", "references_table": "employee_master", "references_column": "GlobalUserId"},
                {"column": "ReporteeID", "references_table": "employee_master", "references_column": "GlobalUserId"}
            ]
        }
        tables_map = defaultdict(list)
        for field in self.raw_data:
            table_name = field.get("table_name", "unknown_table")
            normalized_col = {
                "column_name": field.get("field_name"),
                "description": field.get("description"),
                "aliases": field.get("alias", []),
                "data_type": "TEXT" 
            }
            tables_map[table_name].append(normalized_col)
        nested_schema = {
            "domain": "HR and Payroll",
            "tables": []
        }
        for table_name, columns in tables_map.items():
            table_def = {
                "table_name": table_name,
                "columns": columns,
                "primary_keys": [],
                "foreign_key_candidates": join_registry.get(table_name, [])
            }
            nested_schema["tables"].append(table_def)
        logger.info(f"Rebuilt schema hierarchy in memory. Loaded {len(nested_schema['tables'])} tables.")
        return nested_schema
            
    def find_column_by_alias(self, label: str) -> tuple[str, str, dict] | tuple[None, None, None]:
        """match columns using the alias provided in the JSON """

        if not self.schema:
            return None, None, None
        target_label = label.lower().strip()
        fallback_match = None
        for table in self.schema.get("tables", []):
            table_name = table.get("table_name")
            pks = [pk.lower() for pk in table.get("primary_keys", [])]
            for col in table.get("columns", []):
                exact_name = col.get("column_name", "")
                aliases = [a.lower() for a in col.get("aliases", [])]
                if target_label == exact_name.lower() or target_label in aliases:
                    if exact_name.lower() in pks:
                        return table_name, exact_name, col
                    if not fallback_match:
                        fallback_match = (table_name, exact_name, col) 
        if fallback_match:
            return fallback_match
            
        return None, None, None

    def get_intent_context(self) -> str:
        """returns a vocabulary-rich schema for intent extraction used by  intent agent ."""

        if not self.schema:
            return "No semantic schema available."
        context = [f"DOMAIN: {self.schema.get('domain', '')}\n"]
        for table in self.schema.get("tables", []):
            context.append(f"TABLE: {table.get('table_name')}")
            for col in table.get("columns", []):
                c_name = col.get("column_name")
                c_desc = col.get("description", "")
                c_aliases = ", ".join(col.get("aliases", []))
                alias_str = f" | Aliases: [{c_aliases}]" if c_aliases else ""
                context.append(f"  - {c_name}: {c_desc}{alias_str}")
            context.append("")
        return "\n".join(context)

    def get_sql_context(self) -> str:
        """returns a strictly structured schema for SQL generation used by SQL Agent ."""

        if not self.schema:
            return "No semantic schema available."
        context = []
        for table in self.schema.get("tables", []):
            table_name = table.get("table_name")
            context.append(f"TABLE: {table_name}")
            for fk in table.get("foreign_key_candidates", []):
                context.append(f"  -> JOIN HINT: {fk['column']} joins with {fk['references_table']}.{fk['references_column']}")
            col_strings = []
            for col in table.get("columns", []):
                col_strings.append(f"{col.get('column_name')} ({col.get('data_type')})")
            context.append(f"  -> COLUMNS: {', '.join(col_strings)}")
            context.append("")
        return "\n".join(context)