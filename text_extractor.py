# def extract_text_from_page(page):
#     """
#     Extract text from specific tags (p, h1–h6, li, etc.) with their tag names.
#     """
#     js_code = """
#         (function() {
#             const tags = document.querySelectorAll("p, h1, h2, h3, h4, h5, h6, li, span, strong, em");
#             let result = "";
#             tags.forEach(el => {
#                 if (el.offsetParent !== null) {
#                     const tag = el.tagName.toLowerCase();
#                     const text = el.innerText.trim();
#                     if (text) {
#                         result += `<${tag}>${text}</${tag}>\\n`;
#                     }
#                 }
#             });
#             return result;
#         })();
#     """

#     js_code_txt = """
#         (function() {
#             var body = document.body;
#             if (!body) return "";
#             return body.innerText || body.textContent;
#         })();
#     """
#     page.page().runJavaScript(js_code, print_text_to_html)
#     page.page().runJavaScript(js_code_txt, print_text_to_txt)
    

# def print_text_to_html(text):

#     lines = [line.strip() for line in text.splitlines() if line.strip()]
#     tagged_text = "\n".join(lines)


#     with open("for_text_model/extracted_text_with_tags.html", "w", encoding="utf-8") as f:
#         f.write(tagged_text)


# def print_text_to_txt(text):
#     # Remove empty lines and strip extra spaces
#     lines = [line.strip() for line in text.splitlines() if line.strip()]
#     cleaned_text = "\n".join(lines)

#     # Write to file (overwrite each time)
#     with open("for_text_model/extracted_text.txt", "w", encoding="utf-8") as f:
#         f.write(cleaned_text)




from PyQt5.QtCore import QDateTime
import os

def extract_text_from_page(page):
    """
    Extract text from page with efficient single JavaScript call
    """
    js_code = """
    (function() {
        function getTextWithTags() {
            const tags = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li'];
            let result = "";
            tags.forEach(tag => {
                const elements = document.getElementsByTagName(tag);
                for (let el of elements) {
                    if (el.offsetParent !== null) {
                        const text = el.innerText.trim();
                        if (text) {
                            result += `<${tag}>${text}</${tag}>\\n`;
                        }
                    }
                }
            });
            return result;
        }
        
        return {
            html: getTextWithTags(),
            text: document.body?.innerText || ""
        };
    })();
    """

    def handle_result(result):
        if not result:
            return
            
        timestamp = QDateTime.currentDateTime().toString("yyyyMMdd_hhmmss")
        os.makedirs("for_text_model", exist_ok=True)
        
        # Save HTML version
        if result.get('html'):
            lines = [line.strip() for line in result['html'].splitlines() if line.strip()]
            with open(f"for_text_model/extracted_text_{timestamp}.html", "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
        
        # Save plain text version
        if result.get('text'):
            lines = [line.strip() for line in result['text'].splitlines() if line.strip()]
            with open(f"for_text_model/extracted_text_{timestamp}.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

    page.page().runJavaScript(js_code, handle_result)