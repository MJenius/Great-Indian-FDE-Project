"""
PDF Document Loader and Provenance Text Ingestion.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional
import pydantic
import pypdf

from .models import PolicyDocumentCode


class DocumentSection(pydantic.BaseModel):
    document_code: PolicyDocumentCode
    page: int
    raw_text: str


class DocumentLoader:
    DOCUMENT_FILES = {
        PolicyDocumentCode.PP_2019: "PP-2019_Pricing_Distributor_Policy.pdf",
        PolicyDocumentCode.PP_2023: "PP-2023_Pricing_Distributor_Policy_Revised.pdf",
        PolicyDocumentCode.WRP_2020: "WRP-2020_Warranty_Returns_Policy.pdf",
        PolicyDocumentCode.VOS_7: "VOS-7_Vendor_Onboarding_SOP.pdf",
    }

    @classmethod
    def load_all_documents(cls, data_dir: Path) -> Dict[PolicyDocumentCode, List[DocumentSection]]:
        documents: Dict[PolicyDocumentCode, List[DocumentSection]] = {}
        for doc_code, filename in cls.DOCUMENT_FILES.items():
            path = data_dir / filename
            if not path.exists():
                raise FileNotFoundError(f"Policy PDF not found: {path}")

            reader = pypdf.PdfReader(str(path))
            sections: List[DocumentSection] = []
            for idx, page in enumerate(reader.pages):
                sections.append(
                    DocumentSection(
                        document_code=doc_code,
                        page=idx + 1,
                        raw_text=page.extract_text(),
                    )
                )
            documents[doc_code] = sections
        return documents
