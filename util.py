import networkx as nx 
import re

def extract_infobox(content):
    # Step 1: find the starting point of the infobox
    start_match = re.search(r"\{\{[^{}]{0,50}?[Ii]nfobox", content, flags=re.IGNORECASE)
    if not start_match:
        return None

    start_index = start_match.start()

    # Step 2: walk forward and find the matching braces
    brace_count = 0
    i = start_index
    while i < len(content):
        if content[i:i+2] == "{{":
            brace_count += 1
            i += 2
            continue
        elif content[i:i+2] == "}}":
            brace_count -= 1
            i += 2
            if brace_count == 0:
                return content[start_index:i]  # extract full infobox
            continue
        else:
            i += 1

    return None  # fallback if somehow unbalanced

def extract_field(text, field):
    lines = text.splitlines()
    capture = False
    genre_lines = []
    for line in lines:
        if not capture:
            if re.match(rf'\|\s*{field}\s*=', line, flags=re.I):
                line = re.sub(rf'\|\s*{field}\s*=\s*', '', line, flags=re.I)
                genre_lines.append(line)
                capture = True
        else:
            if re.match(r'\|\s*\w+\s*=', line):
                break
            genre_lines.append(line)
    return '\n'.join(genre_lines).strip()

def extract_name(text):
    pattern = r"\[\[(.*?)\]\]"
    matches = re.findall(pattern, text)
    return matches

def extract_origin(text, field):
    return extract_name(extract_field(extract_infobox(text), field))

# Declare helper functions
def clean_links(links, node):
    arr = []
    for l in links:
        match = re.search(r'|', l)
        if match:
            splits = l.split(r'|')
            if splits[0].replace(' ', '_') == node: #Remove self-loops
                continue
            else:
                arr.append(splits[0].replace(' ', '_'))
        else:
            if l.replace(' ', '_') == node:
                continue
            else:
                arr.append(l.replace(' ', '_'))
    return arr

def analyze_node(data_point, field_origin, field_species):
    Node = data_point['page_name']
    text = data_point['content']
    words = len(text.split())
    try:
        origin = extract_origin(text, field_origin)
    except:
        origin = None

    try:
        species = extract_origin(text, field_species)
    except:
        species = None
    links_to = re.findall(r'\[\[([^\]]+)\]\]', text)
    links_to = clean_links(links_to, Node)
    return Node, links_to, words, origin, species

def create_network(data, field_origin, field_species, use_only_largest_component = True):
    for entry in data:
        entry['page_name'] = entry['page_name'].replace(' ','_')
    G = nx.DiGraph()
    non_links = []
    Nodes = list(set([data_point['page_name'] for data_point in data]))
    for data_point in data:
        Node, links_to, words, origin, species = analyze_node(data_point, field_origin, field_species)
        G.add_node(Node, words=words, origin = origin, species = species)
        for links_to_node in links_to:
            if links_to_node in Nodes:
                G.add_edge(Node, links_to_node)
            else:
                non_links.append(links_to_node)

    G = G.subgraph([node for node, deg in G.degree() if deg > 0])
    if use_only_largest_component:
        # Extract the largest component
        components = nx.weakly_connected_components(G)
        largest = max(components, key=len)
        G = G.subgraph(largest).copy()
    
    return G