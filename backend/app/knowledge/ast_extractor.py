"""Python AST Code Extractor for AgentGuard Knowledge Pipeline.

Extracts classes, functions, methods, Pydantic models, FastAPI routes, docstrings,
line numbers, and deterministic relationship edges using Python's ast module.
"""

import ast
import hashlib
from pathlib import Path

from backend.app.knowledge.models import (
    AuthorityType,
    CodeRelationship,
    CodeSymbolRecord,
    DomainCategory,
    FreshnessStatus,
    KnowledgeUnit,
    QAIssue,
    SourceTier,
)
from backend.app.knowledge.secret_scanner import SecretScanner

MODULE_DOMAIN_MAPPING: dict[str, DomainCategory] = {
    "policy": DomainCategory.I_POLICY_ENGINE,
    "models": DomainCategory.H_DATABASE_ARCHITECTURE,
    "services/audit_log.py": DomainCategory.P_AUDIT_TRAIL,
    "services/payment_gateway.py": DomainCategory.M_RAZORPAY_INTEGRATION,
    "integrations/gemini_client.py": DomainCategory.N_AGENT_BEHAVIOR,
    "integrations/razorpay_client.py": DomainCategory.M_RAZORPAY_INTEGRATION,
    "api/propose.py": DomainCategory.L_TRANSACTIONS,
    "api/execute.py": DomainCategory.L_TRANSACTIONS,
    "api/approve.py": DomainCategory.L_TRANSACTIONS,
    "api/routes_agent.py": DomainCategory.N_AGENT_BEHAVIOR,
    "api/routes_mandate.py": DomainCategory.J_MANDATES,
    "api/routes_audit.py": DomainCategory.P_AUDIT_TRAIL,
    "api/schemas.py": DomainCategory.G_BACKEND_ARCHITECTURE,
    "config.py": DomainCategory.G_BACKEND_ARCHITECTURE,
}


class CodeAstExtractor:
    """Extracts code symbols, metadata, and cross-reference edges from Python files."""

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root

    def discover_python_files(self) -> list[Path]:
        """Discovers all active backend Python files excluding tests and caches."""
        backend_dir = self.workspace_root / "backend" / "app"
        py_files: list[Path] = []

        if backend_dir.exists():
            for p in sorted(backend_dir.rglob("*.py")):
                rel = p.relative_to(self.workspace_root)
                if not SecretScanner.is_path_excluded(rel):
                    py_files.append(p)

        return py_files

    def extract_file(
        self, file_path: Path
    ) -> tuple[list[CodeSymbolRecord], list[KnowledgeUnit], list[QAIssue]]:
        """Parses a Python file using AST and extracts symbols and knowledge units."""
        rel_path = str(file_path.relative_to(self.workspace_root)).replace("\\", "/")
        issues: list[QAIssue] = []
        symbols: list[CodeSymbolRecord] = []
        units: list[KnowledgeUnit] = []

        if SecretScanner.is_path_excluded(rel_path):
            return symbols, units, issues

        try:
            raw_code = file_path.read_text(encoding="utf-8")
        except Exception as exc:
            issues.append(
                QAIssue(
                    severity=QAIssue.QASeverity.ERROR,  # type: ignore
                    code="PYTHON_FILE_READ_ERROR",
                    message=f"Failed to read {rel_path}: {exc}",
                    source_path=rel_path,
                )
            )
            return symbols, units, issues

        # Pre-scan for secrets
        clean_code, scan_issues, is_clean = SecretScanner.scan_and_redact(raw_code, rel_path)
        issues.extend(scan_issues)

        try:
            tree = ast.parse(clean_code, filename=rel_path)
        except SyntaxError as exc:
            issues.append(
                QAIssue(
                    severity=QAIssue.QASeverity.ERROR,  # type: ignore
                    code="PYTHON_AST_SYNTAX_ERROR",
                    message=f"AST SyntaxError in {rel_path}:{exc.lineno}: {exc.msg}",
                    source_path=rel_path,
                    line_number=exc.lineno,
                )
            )
            return symbols, units, issues

        # Determine domain
        primary_domain = DomainCategory.AE_CODE_IMPLEMENTATION
        for pattern, domain in MODULE_DOMAIN_MAPPING.items():
            if pattern in rel_path:
                primary_domain = domain
                break

        # Module-level documentation KnowledgeUnit
        mod_doc = ast.get_docstring(tree)
        mod_hash = hashlib.sha256(clean_code.encode("utf-8")).hexdigest()
        mod_id = f"mod_{Path(rel_path).stem}_{mod_hash[:8]}"

        units.append(
            KnowledgeUnit(
                id=mod_id,
                domain=primary_domain,
                title=f"Module: {rel_path}",
                summary=mod_doc or f"Python module at {rel_path}",
                content=f"Module `{rel_path}`\n\nDocstring: {mod_doc or 'No docstring.'}",
                source_type="PYTHON_AST",
                source_path=rel_path,
                source_tier=SourceTier.TIER_2_SOURCE_CODE,
                line_start=1,
                line_end=len(clean_code.splitlines()),
                symbol=Path(rel_path).stem,
                content_sha256=mod_hash,
                authority=AuthorityType.AUTHORITATIVE,
                freshness=FreshnessStatus.VERIFIED,
                relationships=[],
                tags=["python", "module", primary_domain.value.lower()],
            )
        )

        # Extract top-level classes and functions
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                cls_records, cls_units = self._process_class(node, rel_path, clean_code, primary_domain)
                symbols.extend(cls_records)
                units.extend(cls_units)
            elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                fn_record, fn_unit = self._process_function(node, rel_path, clean_code, primary_domain)
                symbols.append(fn_record)
                units.append(fn_unit)

        return symbols, units, issues

    def _process_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        rel_path: str,
        full_code: str,
        domain: DomainCategory,
        parent_class: str | None = None,
    ) -> tuple[CodeSymbolRecord, KnowledgeUnit]:
        """Extracts a function/method symbol and knowledge unit."""
        lines = full_code.splitlines()
        fn_lines = lines[node.lineno - 1 : node.end_lineno]
        fn_snippet = "\n".join(fn_lines)
        fn_hash = hashlib.sha256(fn_snippet.encode("utf-8")).hexdigest()

        docstring = ast.get_docstring(node)
        decorators = [ast.unparse(d) for d in node.decorator_list]

        # Extract function call dependencies inside body
        called_symbols: list[str] = []
        for child in ast.walk(node):
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                called_symbols.append(child.func.id)

        full_name = f"{parent_class}.{node.name}" if parent_class else node.name
        symbol_type = "method" if parent_class else ("route_handler" if decorators else "function")

        sym_record = CodeSymbolRecord(
            id=f"sym_{Path(rel_path).stem}_{full_name}_{fn_hash[:8]}",
            name=full_name,
            symbol_type=symbol_type,
            file_path=rel_path,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            docstring=docstring,
            signature=f"def {node.name}(...)",
            decorators=decorators,
            dependencies=list(set(called_symbols)),
            content_sha256=fn_hash,
        )

        relationships = [
            CodeRelationship(
                source_symbol=full_name,
                target_symbol=call,
                relationship_type="CALLS",
            )
            for call in set(called_symbols)
        ]

        unit = KnowledgeUnit(
            id=f"code_{Path(rel_path).stem}_{full_name.replace('.', '_')}_{fn_hash[:8]}",
            domain=domain,
            title=f"Code: {full_name}() in {rel_path}",
            summary=docstring.split("\n\n")[0] if docstring else f"Function {full_name} in {rel_path}",
            content=(
                f"File: `{rel_path}` (Lines {node.lineno}-{node.end_lineno})\n"
                f"Symbol: `{full_name}` ({symbol_type})\n\n"
                f"Docstring: {docstring or 'No docstring provided.'}\n\n"
                f"Decorators: {', '.join(decorators) if decorators else 'None'}\n"
                f"Calls: {', '.join(set(called_symbols)) if called_symbols else 'None'}\n\n"
                f"```python\n{fn_snippet[:1500]}\n```"
            ),
            source_type="PYTHON_AST",
            source_path=rel_path,
            source_tier=SourceTier.TIER_2_SOURCE_CODE,
            line_start=node.lineno,
            line_end=node.end_lineno,
            symbol=full_name,
            content_sha256=fn_hash,
            authority=AuthorityType.AUTHORITATIVE,
            freshness=FreshnessStatus.VERIFIED,
            relationships=relationships,
            tags=["python", symbol_type, Path(rel_path).stem, domain.value.lower()],
        )

        return sym_record, unit

    def _process_class(
        self,
        node: ast.ClassDef,
        rel_path: str,
        full_code: str,
        domain: DomainCategory,
    ) -> tuple[list[CodeSymbolRecord], list[KnowledgeUnit]]:
        """Extracts a class symbol, its methods, and knowledge units."""
        lines = full_code.splitlines()
        cls_lines = lines[node.lineno - 1 : node.end_lineno]
        cls_snippet = "\n".join(cls_lines[:40])  # limit class summary snippet
        cls_hash = hashlib.sha256(cls_snippet.encode("utf-8")).hexdigest()

        docstring = ast.get_docstring(node)
        base_classes = [ast.unparse(b) for b in node.bases]
        symbol_type = "pydantic_model" if "BaseModel" in base_classes else "class"

        symbols: list[CodeSymbolRecord] = []
        units: list[KnowledgeUnit] = []

        cls_record = CodeSymbolRecord(
            id=f"sym_{Path(rel_path).stem}_{node.name}_{cls_hash[:8]}",
            name=node.name,
            symbol_type=symbol_type,
            file_path=rel_path,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            docstring=docstring,
            signature=f"class {node.name}({', '.join(base_classes)})",
            decorators=[ast.unparse(d) for d in node.decorator_list],
            dependencies=base_classes,
            content_sha256=cls_hash,
        )
        symbols.append(cls_record)

        cls_unit = KnowledgeUnit(
            id=f"code_{Path(rel_path).stem}_{node.name}_{cls_hash[:8]}",
            domain=domain,
            title=f"Class: {node.name} in {rel_path}",
            summary=docstring.split("\n\n")[0] if docstring else f"Class {node.name} inheriting from {base_classes}",
            content=(
                f"File: `{rel_path}` (Lines {node.lineno}-{node.end_lineno})\n"
                f"Class: `{node.name}`\n"
                f"Bases: {', '.join(base_classes) if base_classes else 'object'}\n\n"
                f"Docstring: {docstring or 'No docstring provided.'}\n\n"
                f"```python\n{cls_snippet}\n```"
            ),
            source_type="PYTHON_AST",
            source_path=rel_path,
            source_tier=SourceTier.TIER_2_SOURCE_CODE if symbol_type != "pydantic_model" else SourceTier.TIER_3_API_SCHEMA,
            line_start=node.lineno,
            line_end=node.end_lineno,
            symbol=node.name,
            content_sha256=cls_hash,
            authority=AuthorityType.AUTHORITATIVE,
            freshness=FreshnessStatus.VERIFIED,
            relationships=[
                CodeRelationship(
                    source_symbol=node.name,
                    target_symbol=base,
                    relationship_type="INHERITS",
                )
                for base in base_classes
            ],
            tags=["python", symbol_type, Path(rel_path).stem, domain.value.lower()],
        )
        units.append(cls_unit)

        # Process class methods
        for item in node.body:
            if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                method_record, method_unit = self._process_function(
                    item, rel_path, full_code, domain, parent_class=node.name
                )
                symbols.append(method_record)
                units.append(method_unit)

        return symbols, units

    def extract_all(
        self,
    ) -> tuple[list[CodeSymbolRecord], list[KnowledgeUnit], list[QAIssue]]:
        """Discovers and extracts all backend Python symbols and knowledge units."""
        files = self.discover_python_files()
        all_symbols: list[CodeSymbolRecord] = []
        all_units: list[KnowledgeUnit] = []
        all_issues: list[QAIssue] = []

        for f in files:
            syms, units, issues = self.extract_file(f)
            all_symbols.extend(syms)
            all_units.extend(units)
            all_issues.extend(issues)

        return all_symbols, all_units, all_issues
