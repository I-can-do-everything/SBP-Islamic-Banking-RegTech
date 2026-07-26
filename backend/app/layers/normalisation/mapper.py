"""
RCOA Mapping Module

PURPOSE:
Maps Core Banking System account codes to SBP's Reporting Chart of Accounts (RCOA).

MAPPING TYPES:
- DIRECT: One CBS code maps to one RCOA code
- AGGREGATION: Multiple CBS codes roll up into one RCOA code
- APPORTIONMENT: One CBS code splits across multiple RCOA codes by percentage

HOW TO EXTEND:
1. Edit config/mappings/{institution_code}.json
2. Add new mapping rules with regex patterns
3. Specify mapping_type: DIRECT, AGGREGATION, or APPORTIONMENT
4. For apportionment, include allocation_percentages
"""

import json 
import re 
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from __future__ import annotations

from app.core.config import get_settings


# we need a single rule to map from CBS code to RCOA code.
# we will introduce three mapping types for now, as drafted in the docstring above.

class MappingRule:
    """
    Represents a single mapping rule from CBS code to RCOA code.

    ATTRIBUTES:
    - cbs_pattern: Regex pattern to match CBS account codes
    - rcoa_code: Target RCOA code
    - rcoa_description: Official SBP description
    - mapping_type: DIRECT, AGGREGATION, or APPORTIONMENT
    - allocation_percentages: For APPORTIONMENT, how to split
    """

    def __init__(
            self,
            cbs_pattern: str,
            rcoa_code: str,
            rcoa_description: str,
            mapping_type: str = "DIRECT",
            allocation_percentages: Optional[Dict[str, float]] = None
    ):
        self.cbs_pattern = cbs_pattern
        self.rcoa_code = rcoa_code
        self.rcoa_description = rcoa_description
        self.mapping_type = mapping_type
        self.allocation_percentages = allocation_percentages or {}
        self._compiled_pattern = re.compile(cbs_pattern)

    def matches(self, cbs_code: str) -> bool:
        """Check if CBS code matches this rule's pattern."""
        return bool(self._compiled_pattern.match(cbs_code))
    
    def apply(
            self, 
            cbs_code: str,
            balance: Decimal
    ) -> List[Tuple[str, str, str, Decimal]]:
        """
        Apply this mapping rule to a CBS account.

        Returns list of tuples:
        - (rcoa_code, rcoa_description, mapping_type, allocated_balance)

        For DIRECT: Single result with full balance
        For AGGREGATION: Single result, will be summed with others
        For APPORTIONMENT: Multiple results split by percentage
        """
        if self.mapping_type == "APPORTIONMENT":
            results = []
            for rcoa_code, percentage in self.allocation_percentages.items():
                allocated = balance * Decimal(str(percentage / 100))
                results.append((rcoa_code, self.rcoa_description, "APPORTIONMENT", allocated))
            return results
        else:
            return [(self.rcoa_code, self.rcoa_description, self.mapping_type, balance)]
        


class RCOAMapper:
    """
    Manages CBS to RCOA mappings for an institution.

    USAGE:
    from app.layers.normalization.mapper import RCOAMapper

    mapper = RCOAMapper.load("MEEZ")
    results = mapper.map_account("3590-MUR-001", Decimal("1000000"))
    for rcoa_code, desc, mapping_type, amount in results:
        print(f"{rcoa_code}: {amount}")
    """
    
    def __init__(
            self, 
            institution_code: str,
            mapping_rules: List[MappingRule], 
            version: str
            ):
        self.institution_code = institution_code
        self.mapping_rules = mapping_rules
        self.version = version
        self._cache: Dict[str, MappingRule] = {}

    @classmethod
    def load(cls, institution_code: str, config_dir: str = None) -> RCOAMapper:
        """
        Load mapping configuration for an institution.

        CONFIGURATION FILE:
        config/mappings/{institution_code}.json

        Structure:
        {
            "version": "v1.0",
            "institution_code": "MEEZ",
            "mappings": [
            {
                "cbs_code_pattern": "3590-MUR-.*",
                "rcoa_code": "3590-MUR",
                "rcoa_description": "Murabaha Financing",
                "mapping_type": "DIRECT"
            },
            ...
            ]
        }
        """
        settings = get_settings()
        config_dir = config_dir or getattr(settings, 'MAPPING_CONFIG_DIR', 'config')


        # Candidate base directories, so this resolves correctly whether the
        # app is started from the repo root, from backend/ (as documented in
        # the README), or from inside Docker (WORKDIR=/app)
        this_file = Path(__file__).resolve()
        try:
            backend_dir = this_file.parents[3]
            repo_root = this_file.parents[4]
        except IndexError:
            backend_dir = Path.cwd()
            repo_root = Path.cwd()
        
        base_dirs = [
            Path(config_dir),           # as given / relative to CWD
            backend_dir / config_dir,   # backend/config
            repo_root / config_dir      # <repo root>/config
        ]

        filenames = [
            f"{institution_code.lower()}.json",
            f"{institution_code.upper()}.json",
            "sample_mapping.json"
        ]

        config_path = None
        for base in base_dirs:
            for filename in filenames:
                candidate = base / filename
                if candidate.exists():
                    config_path = candidate
                    break
            if config_path:
                break

        if config_path is None:
            raise FileNotFoundError(
                f"No mapping configuration found for {institution_code}. "
                f"Looked in: {[str(b) for b in base_dirs]}. "
                f"Please create a {institution_code.lower()}.json there, "
                f"or a sample_mapping.json fallback."
            )
        
        with open(config_path, 'r') as f:
            config: dict = json.load(f)
        
        # parse mapping rules
        rules = []
        mappings: list[dict] = config.get("mappings", [])
        for mapping in mappings:
            rule = MappingRule(
                cbs_pattern=mapping["cbs_code_pattern"],
                rcoa_code=mapping["rcoa_code"],
                rcoa_description=mapping["rcoa_description"],
                mapping_type=mapping.get("mapping_type", "DIRECT"),
                allocation_percentages=mapping.get("allocation_percentages")
            )
            rules.append(rule)

        return cls(
            institution_code=institution_code,
            mapping_rules=rules,
            version=config.get("version", "v1.0")
        )

    def find_rule(self, cbs_code: str) -> Optional[MappingRule]:
        """
        Find the first matching rule for a CBS code.

        RULE ORDER MATTERS:
        Rules are checked in order. More specific patterns should come first.
        A catch-all pattern (e.g., ".*") should be last for unmapped accounts.
        """
        # Check cache first
        if cbs_code in self._cache:
            return self._cache[cbs_code]

        # Find first matching rule
        for rule in self.mapping_rules:
            if rule.matches(cbs_code):
                self._cache[cbs_code] = rule
                return rule

        return None
    
    def map_account(
            self,
            cbs_code: str,
            balance: Decimal,
            description: str = ""
    ) -> List[Dict]:
        """
        Map a CBS account to RCOA code(s).

        Args:
            cbs_code: CBS account code
            balance: Account balance (Decimal)
            description: CBS account description

        Returns:
            List of mapping results, each containing:
            - cbs_account_code: Original CBS code
            - cbs_account_description: Original description
            - rcoa_account_code: Target RCOA code
            - rcoa_account_description: RCOA description
            - balance: Allocated balance
            - mapping_rule: Type of mapping applied
        """
        rule = self.find_rule(cbs_code)

        if not rule:
            # No mapping found. Return as unmapped
            return[{
                "cbs_account_code": cbs_code,
                "cbs_account_description": description,
                "rcoa_account_code": "UNMAPPED",
                "rcoa_account_description": "Unmapped CBS Code",
                "balance": balance,
                "mapping_rule": "UNMAPPED",
            }]
        
        mappings = rule.apply(cbs_code, balance)
        results = []

        for rcoa_code, rcoa_desc, mapping_type, allocated_balance in mappings:
            results.append({
                "cbs_account_code": cbs_code,
                "cbs_account_description": description,
                "rcoa_account_code": rcoa_code,
                "rcoa_account_description": rcoa_desc,
                "balance": allocated_balance,
                "mapping_rule": mapping_type,
            })

        return results
    
def aggregate_by_rcoa(mapped_records: List[Dict]) -> Dict[str, Dict]:
    """
    Aggregate balances by RCOA code.

    AGGREGATION:
    When multiple CBS codes map to the same RCOA code (AGGREGATION type),
    we sum their balances to get the RCOA total.

    Args:
        mapped_records: List from RCOAMapper.map_account()

    Returns:
        Dictionary keyed by RCOA code with:
        - rcoa_account_code
        - rcoa_account_description
        - balance (summed)
        - source_codes (list of CBS codes that contributed)
    """
    aggregated: Dict[str, Dict] = {}

    

    for record in mapped_records:
        rcoa_code = record["rcoa_account_code"]
        if rcoa_code not in aggregated:
            aggregated[rcoa_code] = {
                "rcoa_account_code": rcoa_code,
                "rcoa_account_description": record["rcoa_account_description"],
                "balance": Decimal("0"),
                "source_codes": []
            }

        aggregated[rcoa_code]["balance"] += record["balance"]
        source_list: List[str] = aggregated[rcoa_code]["source_codes"]
        source_list.append(record["cbs_account_code"])

    return aggregated




        





