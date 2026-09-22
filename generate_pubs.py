import os
import re
import unicodedata

def decode_latex_chars(text):
    """
    Converts common BibTeX/LaTeX diacritics into UTF-8 characters 
    and cleans protective curly braces.
    """
    if not text:
        return ""
        
    latex_map = {
        r'{\"a}': 'ä', r'{\"A}': 'Ä', r'{\"o}': 'ö', r'{\"O}': 'Ö', r'{\"u}': 'ü', r'{\"U}': 'Ü',
        r'{\'a}': 'á', r'{\'A}': 'Á', r'{\'e}': 'é', r'{\'E}': 'É', r'{\'i}': 'í', r'{\'I}': 'Í',
        r'{\'o}': 'ó', r'{\'O}': 'Ó', r'{\'u}': 'ú', r'{\'U}': 'Ú', r'{\'y}': 'ý', r'{\'Y}': 'Ý',
        r'{\'c}': 'ć', r'{\'C}': 'Ć', r'{\'n}': 'ń', r'{\'N}': 'Ń', r'{\'s}': 'ś', r'{\'S}': 'Ś',
        r'{\'z}': 'ź', r'{\'Z}': 'Ź',
        r'{\`a}': 'à', r'{\`A}': 'À', r'{\`e}': 'è', r'{\`E}': 'È', r'{\`u}': 'ù', r'{\`U}': 'Ù',
        r'{\^a}': 'â', r'{\^e}': 'ê', r'{\^i}': 'î', r'{\^o}': 'ô', r'{\^u}': 'û',
        r'{\~n}': 'ñ', r'{\~N}': 'Ñ', r'{\~a}': 'ã', r'{\~o}': 'õ',
        r'{\v s}': 'š', r'{\v S}': 'Š', r'{\v c}': 'č', r'{\v C}': 'Č', r'{\v r}': 'ř', r'{\v R}': 'Ř', 
        r'{\v z}': 'ž', r'{\v Z}': 'Ž', r'{\v e}': 'ě', r'{\v E}': 'Ě',
        r'{\.e}': 'ė', r'{\.E}': 'Ė', r'{\.z}': 'ż', r'{\.Z}': 'Ż',
        r'{\l}': 'ł', r'{\L}': 'Ł', r'{\o}': 'ø', r'{\O}': 'Ø', r'{\ss}': 'ß', r'\&': '&'
    }
    
    for latex, unicode_char in latex_map.items():
        text = text.replace(latex, unicode_char)
        
    text = re.sub(r'[{}]', '', text)
    return text.strip()

def parse_authors(author_string):
    """
    Splits the Zotero 'and' separated author string, cleans LaTeX, 
    and returns formatted names + the first author's last name.
    """
    authors = [a.strip() for a in author_string.split(" and ")]
    formatted_authors = []
    first_author_last = ""
    
    for i, author in enumerate(authors):
        clean_author = decode_latex_chars(author)
        
        if "," in clean_author:
            last, first = [part.strip() for part in clean_author.split(",", 1)]
            formatted_authors.append(f"{first} {last}")
            if i == 0:
                first_author_last = last
        else:
            formatted_authors.append(clean_author)
            if i == 0:
                first_author_last = clean_author.split()[-1] if clean_author else ""
                
    return formatted_authors, first_author_last

def generate_folder_slug(text):
    """Safely converts UTF-8 strings into ASCII folder slugs."""
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    return re.sub(r'[^a-zA-Z0-9]', '', text).lower()

def month_to_num(month_str):
    """Converts a three-letter month abbreviation to a two-digit string."""
    if not month_str: 
        return "01"
    m = month_str.lower().strip('{}')
    months = {'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04', 'may': '05', 'jun': '06',
              'jul': '07', 'aug': '08', 'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'}
    
    for key, val in months.items():
        if m.startswith(key): 
            return val
    return "01"

def extract_field(field_name, entry_text):
    """
    Extracts a field from BibTeX by properly counting nested braces.
    """
    match = re.search(fr'{field_name}\s*=\s*', entry_text, re.IGNORECASE)
    if not match:
        return ""
    
    start_idx = match.end()
    char = entry_text[start_idx]
    
    if char == '{':
        brace_count = 0
        for i in range(start_idx, len(entry_text)):
            if entry_text[i] == '{':
                brace_count += 1
            elif entry_text[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    return entry_text[start_idx+1:i].replace('\n', ' ')
    elif char == '"':
        m = re.match(r'"([^"]*)"', entry_text[start_idx:])
        if m:
            return m.group(1).replace('\n', ' ')
    else:
        m = re.match(r'([^,\n]+)', entry_text[start_idx:])
        if m:
            return m.group(1).strip().replace('\n', ' ')
            
    return ""

def process_bibtex(file_path, output_dir="content/publication"):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Safely split by @ at the start of a line to avoid duplicate @@ symbols
    raw_entries = re.split(r'(?m)^@', content)
    entries = [f"@{e.strip()}" for e in raw_entries if e.strip()]
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for entry in entries:
        type_match = re.search(r'@(\w+)\{', entry)
        if not type_match: 
            continue
        entry_type = type_match.group(1).lower()

        # Extract and clean metadata
        raw_title = extract_field("title", entry)
        title = decode_latex_chars(raw_title) if raw_title else "Untitled"
        
        year = extract_field("year", entry) or "0000"
        month = month_to_num(extract_field("month", entry))
        date_str = f"{year}-{month}-01"

        raw_authors = extract_field("author", entry)
        authors_list, first_last = parse_authors(raw_authors)

        # Apply APA 7th Edition formatting for 21+ authors
        if len(authors_list) >= 21:
            display_authors = authors_list[:19] + ["..."] + [authors_list[-1]]
        else:
            display_authors = authors_list

        # Generate safe folder name: author-firstword-year
        first_word_raw = title.split()[0] if title.split() else "paper"
        first_word_slug = generate_folder_slug(first_word_raw)
        author_slug = generate_folder_slug(first_last)
        
        folder_name = f"{author_slug}-{first_word_slug}-{year}"
        folder_path = os.path.join(output_dir, folder_name)
        os.makedirs(folder_path, exist_ok=True)

        pub_type = "2" if entry_type == "article" else "6" if entry_type == "incollection" else "1"
        
        # Extract publication container
        raw_pub = extract_field("journal", entry) or extract_field("booktitle", entry)
        publication = f"*{decode_latex_chars(raw_pub)}*" if raw_pub else ""

        url_pdf = extract_field("url", entry)
        
        # Format the display authors for the TOML array
        authors_toml = ", ".join([f'"{a}"' for a in display_authors])

        index_md = f"""+++
title = "{title}"
date = {date_str}
authors = [{authors_toml}]
publication_types = ["{pub_type}"]
abstract = ""
selected = false
publication = "{publication}"
url_pdf = "{url_pdf}"
+++
"""
        
        with open(os.path.join(folder_path, "index.md"), 'w', encoding='utf-8') as f:
            f.write(index_md)

        with open(os.path.join(folder_path, f"{folder_name}.bib"), 'w', encoding='utf-8') as f:
            f.write(entry.strip() + "\n")

        print(f"Generated successfully: {folder_path}")

if __name__ == "__main__":
    process_bibtex("new_pubs.bib", output_dir="content/publication")