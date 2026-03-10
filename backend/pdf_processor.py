import pdfplumber
import os

def extract_text_from_pdf(filepath: str) -> str:
    """
    Reads a PDF file and extracts all text content.
    Returns the accumulated text as a string.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Provided path {filepath} does not exist.")
        
    full_text = []
    try:
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                # Extract text using default layout parameters
                text = page.extract_text()
                if text:
                    full_text.append(text)
        return "\n".join(full_text)
    except Exception as e:
        return f"Error extracting PDF: {str(e)}"
