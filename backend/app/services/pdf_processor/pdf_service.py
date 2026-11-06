import os
import fitz # PyMuPDF
from pathlib import Path
from typing import Dict, Any, List
from backend.app.core.config import settings

class PDFService:
    @staticmethod
    def get_pdf_info(file_path: str) -> Dict[str, Any]:
        """Reads PDF metadata and page count"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")
        
        doc = fitz.open(str(path))
        info = {
            "total_pages": len(doc),
            "file_name": path.name,
            "file_size": path.stat().st_size,
            "metadata": doc.metadata
        }
        doc.close()
        return info

    @staticmethod
    def extract_text_by_pages(file_path: str) -> List[Dict[str, Any]]:
        """Extracts text content per page"""
        doc = fitz.open(file_path)
        pages_text = []
        for i, page in enumerate(doc):
            pages_text.append({
                "page_number": i + 1,
                "text": page.get_text(),
                "width": page.rect.width,
                "height": page.rect.height
            })
        doc.close()
        return pages_text

    @staticmethod
    def render_page_image(file_path: str, page_number: int, zoom: float = 1.5) -> bytes:
        """Renders a PDF page as PNG bytes for thumbnail or high-res view"""
        doc = fitz.open(file_path)
        if page_number < 1 or page_number > len(doc):
            doc.close()
            raise ValueError(f"Page number {page_number} out of range (1-{len(doc)})")
        
        page = doc[page_number - 1]
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img_bytes = pix.tobytes("png")
        doc.close()
        return img_bytes

    @staticmethod
    def split_and_save_tagged_pdf(
        source_pdf_path: str, 
        start_page: int, 
        end_page: int, 
        tag_name: str, 
        document_id: str
    ) -> str:
        """
        Extracts selected pages from source_pdf_path and saves as a new PDF file
        in storage/tagged-documents/. Returns relative storage path.
        """
        src_doc = fitz.open(source_pdf_path)
        total = len(src_doc)
        
        # Clamp page range
        start_idx = max(0, start_page - 1)
        end_idx = min(total - 1, end_page - 1)
        
        if start_idx > end_idx:
            src_doc.close()
            raise ValueError(f"Invalid page range: {start_page} to {end_page}")
        
        new_doc = fitz.open()
        new_doc.insert_pdf(src_doc, from_page=start_idx, to_page=end_idx)
        
        # Clean tag name for filename
        clean_tag = tag_name.replace(" ", "_").replace("/", "_")
        filename = f"{document_id}_{clean_tag}_p{start_page}-{end_page}.pdf"
        settings.TAGGED_DOCS_DIR.mkdir(parents=True, exist_ok=True)
        dest_path = settings.TAGGED_DOCS_DIR / filename
        
        new_doc.save(str(dest_path))
        new_doc.close()
        src_doc.close()
        
        return f"tagged-documents/{filename}"

pdf_service = PDFService()
