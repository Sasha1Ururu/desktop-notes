import markdown

def render_markdown(md_text):
    """
    Converts Markdown text to HTML.
    Uses the python-markdown library.
    Basic extensions like tables, fenced_code can be enabled if desired.
    """
    try:
        # Basic usage:
        # html = markdown.markdown(md_text)

        # Usage with some common extensions:
        html = markdown.markdown(
            md_text,
            extensions=[
                'markdown.extensions.fenced_code', # For ```code``` blocks
                'markdown.extensions.tables',      # For tables
                'markdown.extensions.nl2br',       # For converting newlines to <br>
                'markdown.extensions.extra'        # Includes several useful extensions like abbr, attr_list, def_list, footnotes, etc.
                                                   # 'extra' itself includes 'tables' and 'fenced_code',
                                                   # but explicitly listing them doesn't hurt and shows intent.
            ]
        )
        return html
    except Exception as e:
        # Fallback or error handling
        print(f"Error rendering Markdown: {e}")
        # Return plain text with escaped HTML characters as a fallback
        import html as html_converter
        return f"<p>Error rendering Markdown. Content displayed as plain text:</p><pre>{html_converter.escape(md_text)}</pre>"

# Example usage (for testing this utility directly)
if __name__ == '__main__':
    test_md_simple = "Hello World\nThis is a new line."
    print("--- Simple Markdown (with nl2br from 'extra' or 'nl2br') ---")
    print(render_markdown(test_md_simple))
    print("\n")

    test_md_features = """
# Main Heading

This is some text with **bold** and *italic*.

## Subheading

- List item 1
- List item 2
  - Nested item A
  - Nested item B

1. Numbered item 1
2. Numbered item 2

```python
def greet(name):
    print(f"Hello, {name}!")
```

| Header 1 | Header 2 |
|----------|----------|
| Cell 1   | Cell 2   |
| Cell 3   | Cell 4   |

This is a footnote.[^1]

[^1]: This is the footnote definition.

An abbreviation: HTML (Hyper Text Markup Language).
*[HTML]: Hyper Text Markup Language

    """
    print("--- Markdown with Features (using 'extra' extension) ---")
    print(render_markdown(test_md_features))
    print("\n")

    test_md_broken = "This is [an unclosed link"
    print("--- Potentially Broken Markdown (should still render safely) ---")
    print(render_markdown(test_md_broken))
    print("\n")

    # Test the error case by making markdown module fail (simulated)
    original_markdown_func = markdown.markdown
    def mock_broken_markdown(text, extensions):
        raise ImportError("Simulated markdown processing error")
    markdown.markdown = mock_broken_markdown

    print("--- Markdown with Simulated Processing Error ---")
    print(render_markdown("This text will cause a simulated error."))

    # Restore original function if further tests were needed
    markdown.markdown = original_markdown_func
