import os
import csv
import re
import requests
from thefuzz import fuzz

OFAC_SDN_URL = "https://www.treasury.gov/ofac/downloads/sdn.csv"
OFAC_ALT_URL = "https://www.treasury.gov/ofac/downloads/alt.csv"
SDN_CACHE_FILE = "ofac_sdn.csv"
ALT_CACHE_FILE = "ofac_alt.csv"

FATF_BLACKLIST = {"KP", "IR", "MM"}
FATF_GREYLIST = {"SY", "YE", "VE", "RU"}

LEGAL_SUFFIXES = r"\b(PJSC|JSC|LLC|LTD|PLC|CORP|CORPORATION|INC|INCORPORATED|SA|NV|AG|GMBH|CO|COMPANY)\b"

def clean_entity_name(name: str) -> str:
    cleaned = name.upper()
    cleaned = re.sub(LEGAL_SUFFIXES, "", cleaned)
    cleaned = re.sub(r"[^\w\s]", "", cleaned)
    return " ".join(cleaned.split())


class InstitutionalComplianceEngine:
    def __init__(self, match_threshold: int = 80):
        self.match_threshold = match_threshold
        self.sdn_index = self._load_or_fetch_records()

    def _load_or_fetch_records(self) -> dict[str, str]:
        """Indexes primary SDN names and known aliases/AKAs."""
        for url, filepath in [(OFAC_SDN_URL, SDN_CACHE_FILE), (OFAC_ALT_URL, ALT_CACHE_FILE)]:
            if not os.path.exists(filepath):
                print(f"[ComplianceEngine] Downloading {filepath} from US Treasury...")
                resp = requests.get(url, timeout=30)
                resp.raise_for_status()
                with open(filepath, "wb") as f:
                    f.write(resp.content)

        # Dictionary mapping cleaned_name -> original_sanction_record
        indexed_names = {}

        # 1. Primary SDN list
        with open(SDN_CACHE_FILE, mode="r", encoding="utf-8", errors="ignore") as f:
            for row in csv.reader(f):
                if len(row) > 1 and row[1].strip():
                    orig = row[1].strip().upper()
                    indexed_names[clean_entity_name(orig)] = orig

        # 2. Alt/Alias list (column 3 is alias name)
        with open(ALT_CACHE_FILE, mode="r", encoding="utf-8", errors="ignore") as f:
            for row in csv.reader(f):
                if len(row) > 3 and row[3].strip():
                    orig_alias = row[3].strip().upper()
                    indexed_names[clean_entity_name(orig_alias)] = orig_alias

        print(f"[ComplianceEngine] Indexed {len(indexed_names):,} official entities & aliases.")
        return indexed_names

    def screen_entity(self, counterparty_name: str, jurisdiction: str) -> dict:
        norm_jurisdiction = jurisdiction.strip().upper()
        if norm_jurisdiction in FATF_BLACKLIST:
            return {
                "passed": False,
                "reason": f"FATF High-Risk Jurisdiction match: {norm_jurisdiction}",
                "confidence_score": 1.0,
                "matched_record": None
            }

        cleaned_query = clean_entity_name(counterparty_name)
        best_match = None
        highest_score = 0

        # Exact match check first for fast execution
        if cleaned_query in self.sdn_index:
            return {
                "passed": False,
                "reason": "Direct OFAC SDN/Alias match",
                "confidence_score": 1.0,
                "matched_record": self.sdn_index[cleaned_query]
            }

        for cleaned_sdn, original_record in self.sdn_index.items():
            score = fuzz.token_sort_ratio(cleaned_query, cleaned_sdn)
            if score > highest_score:
                highest_score = score
                best_match = original_record
            if score == 100:
                break

        if highest_score >= self.match_threshold:
            return {
                "passed": False,
                "reason": f"OFAC SDN match threshold exceeded ({highest_score}% similarity)",
                "confidence_score": highest_score / 100.0,
                "matched_record": best_match
            }

        return {
            "passed": True,
            "reason": "Entity cleared screening against OFAC SDN and FATF lists.",
            "confidence_score": highest_score / 100.0,
            "matched_record": best_match if highest_score > 60 else None
        }


if __name__ == "__main__":
    engine = InstitutionalComplianceEngine()
    print("VTB Check:", engine.screen_entity("VTB Bank PJSC", "RU"))
    print("Barclays Check:", engine.screen_entity("Barclays Bank PLC", "GB"))