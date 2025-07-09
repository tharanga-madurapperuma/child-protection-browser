# nsfw_blur.py
import requests

HUGGINGFACE_API_URL = "https://api-inference.huggingface.co/models/michellejieli/NSFW_text_classifier"
HEADERS = {
    "Authorization": "Bearer token"  # 🔁 Replace this with your real token
}

def is_paragraph_nsfw(text):
    try:
        response = requests.post(HUGGINGFACE_API_URL, headers=HEADERS, json={"inputs": text})
        if response.status_code == 200:
            result = response.json()
            if result and isinstance(result, list):
                label = result[0]["label"]
                score = result[0]["score"]
                return label == "NSFW" and score > 0.8
    except Exception as e:
        print("API error:", e)
    return False

def scan_and_blur_nsfw_paragraphs(page):
    js_code = """
    (function() {
        const elements = Array.from(document.getElementsByTagName("p"))
            .map((el, i) => ({text: el.innerText.trim(), index: i}))
            .filter(e => e.text.length > 20);
        return elements;
    })();
    """

    def handle_result(result):
        if not result:
            return
        for para in result:
            if is_paragraph_nsfw(para["text"]):
                blur_js = f"""
                    (function() {{
                        const p = document.getElementsByTagName("p")[{para["index"]}];
                        if (p) {{
                            p.style.filter = "blur(5px)";
                            p.style.backgroundColor = "rgba(0,0,0,0.1)";
                        }}
                    }})();
                """
                page.page().runJavaScript(blur_js)

    page.page().runJavaScript(js_code, handle_result)
