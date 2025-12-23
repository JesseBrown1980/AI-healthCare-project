import pypdf

def analyze_pdf(path):
    try:
        reader = pypdf.PdfReader(path)
        print(f"Number of pages: {len(reader.pages)}")
        text_count = 0
        image_count = 0
        for page in reader.pages:
            t = page.extract_text()
            if t: text_count += len(t)
            # pypdf images access might vary by version, but let's try standard way
            try:
                if hasattr(page, 'images') and page.images:
                    image_count += len(page.images)
            except:
                pass
        
        print(f"Total text characters: {text_count}")
        print(f"Total images: {image_count}")
        if text_count == 0 and image_count > 0:
            print("Conclusion: PDF likely consists of scanned images (requires OCR).")
        elif text_count == 0:
            print("Conclusion: PDF contains no text and no detected images (possibly encrypted or other format).")
        else:
            print("Conclusion: Some text found.")

    except Exception as e:
        print(f"Error analyzing PDF: {e}")

analyze_pdf("One.pdf")
