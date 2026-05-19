# Parsing Reference

Detailed reference for selecting, extracting, and navigating HTML with Scrapling.

## Table of Contents

1. [CSS Selectors](#css-selectors)
2. [XPath Selectors](#xpath-selectors)
3. [Filter-based Searching](#filter-based-searching)
4. [Text and Regex Search](#text-and-regex-search)
5. [Finding Similar Elements](#finding-similar-elements)
6. [Navigation and Properties](#navigation-and-properties)
7. [Generating Selectors](#generating-selectors)
8. [Regex Extraction](#regex-extraction)
9. [Adaptive Scraping](#adaptive-scraping)

---

## CSS Selectors

Scrapling implements CSS3 selectors via `cssselect`, plus Scrapy/Parsel-compatible pseudo-elements:

```python
page.css('.product')                    # All elements with class "product"
page.css('.product')[0]                 # First element
page.css('h1::text').get()              # Text content
page.css('a::attr(href)').get()         # Attribute value
page.css('a::attr(href)').getall()      # All attribute values
page.css('.product h2:contains("Sale")::text').get()  # Text with filter
```

**Notes:**
- `::text` selects text nodes
- `::attr(name)` selects attribute values
- `:contains("text")` filters by text content

## XPath Selectors

```python
page.xpath('//*[@class="product"]')
page.xpath('//h1//text()').get()
page.xpath('//a/@href').getall()
```

**Note:** Scrapling does NOT implement Scrapy's `has-class` XPath extension. Use the `has_class()` method on elements instead.

## Filter-based Searching

The `find` and `find_all` methods provide an intuitive way to find elements, similar to BeautifulSoup:

```python
# By tag name
page.find_all('div')
page.find_all(['div', 'span'])  # Multiple tags

# By attributes
page.find_all('div', class_='product')
page.find_all('div', {'class': 'product'})
page.find_all({'class': 'product'})  # Any tag

# By attribute operators
page.find_all({'href$': 'Einstein'})    # Ends with
page.find_all({'href*': '/author/'})    # Contains
page.find_all({'href^': 'https://'})    # Starts with

# By function filter
page.find_all(lambda e: len(e.children) > 0)
page.find_all(lambda e: "world" in e.text)

# By regex content filter
page.find_all('span', re.compile(r'world'))

# Combined filters (waterfall: tag → attrs → regex → function)
page.find_all('div', {'class': 'quote'}, lambda e: "world" in e.css('.text::text').get())
```

**Important:** The order of arguments doesn't matter. Scrapling always applies filters in this order: tag names → attributes → regex → functions.

## Text and Regex Search

### `find_by_text`

Find elements whose direct text content matches:

```python
page.find_by_text('Tipping the Velvet')           # Exact match, first result
page.find_by_text('the', partial=True)             # Contains text
page.find_by_text('the', partial=True, first_match=False)  # All matches
page.find_by_text('The', case_sensitive=True)      # Case-sensitive
```

Arguments:
- `first_match` — Return only first result (default: True)
- `case_sensitive` — Consider case (default: False)
- `clean_match` — Normalize whitespace before matching (default: False)
- `partial` — Match elements containing the text, not exact match (default: False)

### `find_by_regex`

Find elements whose text matches a regex pattern:

```python
page.find_by_regex(r'£[\d\.]+')
page.find_by_regex(r'£[\d\.]+', first_match=False)

import re
pattern = re.compile(r'£[\d\.]+')
page.find_by_regex(pattern)
```

## Finding Similar Elements

Given one element, find others with similar structure. Powerful for extracting lists:

```python
# Find one product by its title
first = page.find_by_text('Product Name')

# Find all similar products
products = first.find_similar()

# Control similarity threshold (default: 0.2 = 20% attribute similarity)
products = first.find_similar(similarity_threshold=0.3)

# Ignore specific attributes during matching
products = first.find_similar(ignore_attributes=['href', 'src', 'title'])

# Include text content in matching (usually not recommended)
products = first.find_similar(match_text=True)
```

**How it works:**
1. Finds all elements at the same DOM depth
2. Filters by same tag name, parent tag, grandparent tag
3. Uses fuzzy matching on attributes (controlled by `similarity_threshold`)

### Practical Example: Extracting Product Grids

```python
def extract_products(page):
    # Find the "Add to Cart" button, then walk up to the product card
    first = page.find_by_text('Add to Cart').find_ancestor(
        lambda e: e.has_class('product-card')
    )
    products = first.find_similar()

    return [
        {
            'name': p.css('h3::text').get(),
            'price': p.css('.price::text').re_first(r'\d+\.\d{2}'),
        }
        for p in products
    ]
```

## Navigation and Properties

### Element Navigation

```python
element.parent           # Parent element
element.children         # List of child elements
element.siblings         # List of sibling elements
element.find_ancestor(lambda e: e.has_class('container'))  # Walk up until match
```

### Element Properties

```python
element.text             # Direct text content
element.get_all_text()   # All text including children
element.attrib           # Dictionary of attributes
element.tag              # Tag name
element.html             # Outer HTML
element.inner_html       # Inner HTML
```

### Helper Methods

```python
element.has_class('product')     # Check if element has a class
element.urljoin('path')          # Resolve relative URL
element.generate_css_selector    # Short CSS selector
element.generate_full_css_selector  # Full CSS selector from root
element.generate_xpath_selector     # Short XPath
element.generate_full_xpath_selector  # Full XPath from root
```

## Generating Selectors

For any found element, generate reusable selectors:

```python
url_element = page.find({'href*': '/author/'})

url_element.generate_css_selector       # 'body > div > div:nth-of-type(2) > div > div > span:nth-of-type(2) > a'
url_element.generate_full_css_selector  # Same, but guaranteed full path
url_element.generate_xpath_selector     # '//body/div/div[2]/div/div/span[2]/a'
url_element.generate_full_xpath_selector
```

Short selectors try to find a unique stopping point (like an `id`). If none exists, the short and full selectors are the same.

## Regex Extraction

Methods available on `Selector`, `Selectors`, `TextHandler`, and `TextHandlers`:

```python
page.css('.price_color')[0].re_first(r'[\d\.]+')    # First match
page.css('.price_color').re(r'[\d\.]+')             # All matches

# On attribute values
page.css('a::attr(href)').re(r'catalogue/(.*)/index.html')

# On text
page.find_by_text('Tipping the Velvet').attrib['href'].re(r'catalogue/(.*)/index.html')
```

## Adaptive Scraping

Make scrapers resilient to website redesigns by saving and later relocating elements based on their structural properties.

### Enabling Adaptive Mode

```python
from scrapling import Selector, Fetcher

# On Selector
page = Selector(html_doc, adaptive=True, url='https://example.com')

# On Fetcher
Fetcher.adaptive = True
page = Fetcher.get('https://example.com')
```

### CSS/XPath Adaptive Pattern

```python
# First scrape: save the element's properties
products = page.css('.product', auto_save=True)

# Later, if site changes: relocate using saved properties
products = page.css('.product', adaptive=True)
```

The identifier is automatically set to the CSS/XPath selector string.

### Manual Save/Retrieve/Relocate

For elements found by any method (text search, filters, etc.):

```python
# Save
element = page.find_by_text('Tipping the Velvet')
page.save(element, 'book_title_link')

# Later: retrieve and relocate
data = page.retrieve('book_title_link')
relocated = page.relocate(data, selector_type=True)
```

### Advanced Options

- `adaptive_domain` — Use a custom domain key for storage (useful when a site changes its URL)
- `identifier` — Custom identifier instead of auto-generated selector string
- `storage` / `storage_args` — Custom database backend (default: SQLite)

### Troubleshooting

```python
# Check if data was saved
data = page.retrieve('identifier')
if not data:
    print("No saved data for this identifier")

# Try a different identifier
products = page.css('.product', adaptive=True, identifier='old_selector')

# Save again with a new, more specific selector
products = page.css('.product-list .product', auto_save=True, identifier='new_identifier')
```

**Known issue:** In the save process, only the first element's properties are saved. So if your selector matches multiple different elements, adaptive relocation returns only the first one. Combined CSS selectors (with commas) are an exception — they're split and executed separately.
