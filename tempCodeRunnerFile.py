    """Handle page load completion"""
        if ok:  # Only proceed if load was successful
            print(f"Page loaded successfully: {browser.url().toString()}")
            extract_text_from_page(browser)
        else:
            print(f"Page failed to load: {browser.url().toString()}")