import pypdf
import sys

def extract_text(pdf_path, output_path):
    try:
        reader = pypdf.PdfReader(pdf_path)
        with open(output_path, "w", encoding="utf-8") as f:
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    f.write(text)
                    f.write("\n\n") # Separate pages
        print(f"Successfully extracted text to {output_path}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    extract_text("One.pdf", "One_text.txt")
