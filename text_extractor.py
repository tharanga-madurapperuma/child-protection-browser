import os
import pathlib
from PyQt5.QtCore import QDateTime

def get_output_base_dir():
    """Get the absolute path to the project root directory"""
    project_root = pathlib.Path(__file__).parent.resolve()
    base_dir = project_root / "text_extractions"
    return base_dir

def ensure_directory_exists(directory):
    """Create directory if it doesn't exist"""
    try:
        directory.mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        print(f"Directory creation failed: {str(e)}")
        return False

def save_extracted_content(content_type, content):
    """Save content to fixed filename (overwrites existing)"""
    base_dir = get_output_base_dir()
    sub_dir = base_dir / content_type
    
    if not ensure_directory_exists(sub_dir):
        return False
    
    try:
        ext = 'html' if content_type == 'html' else 'txt'
        filename = sub_dir / f"extracted_content.{ext}"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Updated {content_type} file at: {filename}")
        return True
    except Exception as e:
        print(f"Failed to update {content_type} file: {str(e)}")
        return False

def extract_text_from_page(page):
    """Extract and update text content in fixed files"""
    # JavaScript code to extract both HTML-tagged and plain text
    js_code = """
    (function() {
        function getVisibleText() {
            const tags = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'span', 'div'];
            let htmlResult = "";
            let textResult = "";
            
            tags.forEach(tag => {
                const elements = document.getElementsByTagName(tag);
                for (let el of elements) {
                    if (el.offsetParent !== null) {
                        const text = el.innerText.trim();
                        if (text) {
                            htmlResult += `<${tag}>${text}</${tag}>\\n`;
                            textResult += `${text}\\n`;
                        }
                    }
                }
            });
            
            if (!textResult.trim()) {
                textResult = document.body?.innerText || "";
            }
            
            return {
                html: htmlResult,
                text: textResult
            };
        }
        return getVisibleText();
    })();
    """

    def handle_result(result):
        if not result:
            print("No text content received from JavaScript")
            return
            
        # Save/update HTML content
        if result.get('html'):
            html_content = "\n".join([line.strip() for line in result['html'].splitlines() if line.strip()])
            save_extracted_content('html', html_content)
        
        # Save/update plain text
        if result.get('text'):
            plain_text = "\n".join([line.strip() for line in result['text'].splitlines() if line.strip()])
            save_extracted_content('text', plain_text)

    page.page().runJavaScript(js_code, handle_result)