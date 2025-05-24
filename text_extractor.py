def extract_text_from_page(page):
    """
    Extract text from specific tags (p, h1–h6, li, etc.) with their tag names.
    """
    js_code = """
        (function() {
            const tags = document.querySelectorAll("p, h1, h2, h3, h4, h5, h6, li, span, strong, em");
            let result = "";
            tags.forEach(el => {
                if (el.offsetParent !== null) {
                    const tag = el.tagName.toLowerCase();
                    const text = el.innerText.trim();
                    if (text) {
                        result += `<${tag}>${text}</${tag}>\\n`;
                    }
                }
            });
            return result;
        })();
    """

    js_code_txt = """
        (function() {
            var body = document.body;
            if (!body) return "";
            return body.innerText || body.textContent;
        })();
    """
    page.page().runJavaScript(js_code, print_text_to_html)
    page.page().runJavaScript(js_code_txt, print_text_to_txt)
    

def print_text_to_html(text):

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    tagged_text = "\n".join(lines)


    with open("for_text_model/extracted_text_with_tags.html", "w", encoding="utf-8") as f:
        f.write(tagged_text)


def print_text_to_txt(text):
    # Remove empty lines and strip extra spaces
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    cleaned_text = "\n".join(lines)

    # Write to file (overwrite each time)
    with open("for_text_model/extracted_text.txt", "w", encoding="utf-8") as f:
        f.write(cleaned_text)