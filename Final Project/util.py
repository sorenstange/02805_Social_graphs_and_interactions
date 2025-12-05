import networkx as nx
import re, pickle, urllib.request, time, json, requests

#Define helper functions
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

def create_network(data, field_origin, field_species, use_only_largest_component = False):
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

def load_network(name = None):
    if name in ['HP', 'hp', 'Harry Potter']:
        with open("data/Harry_Potter_Wiki_pages.pkl", "rb") as f:   # 'rb' = read binary
            data = pickle.load(f)

        corrected_list = []
        for x in data:
            if 'Individual infobox' in x['content']:
                corrected_list.append(x)

        G = create_network(corrected_list, field_origin = 'house', field_species = 'blood', use_only_largest_component=True)
        nodes_w_in = [node for node, deg in G.in_degree() if deg > 0]
        nodes_w_out = [node for node, deg in G.out_degree() if deg > 0]

        nodes = list(set(nodes_w_in).intersection( set(nodes_w_out)))
        return G.subgraph(nodes).copy()
    
    elif name in ['LOTR', 'lotr', 'Lord of the Rings']:
        with open("data/Lord_of_the_rings_Wiki_pages.pkl", "rb") as f:   # 'rb' = read binary
            data = pickle.load(f)

        corrected_list = []
        for x in data:
            if 'Infobox Person' in x['content']:
                corrected_list.append(x)


        G = create_network(corrected_list, field_origin = 'culture', field_species = 'race', use_only_largest_component=True)

        nodes_w_in = [node for node, deg in G.in_degree() if deg > 0]
        nodes_w_out = [node for node, deg in G.out_degree() if deg > 0]

        nodes = list(set(nodes_w_in).intersection( set(nodes_w_out)))
        return G.subgraph(nodes).copy()
    
    else:
        HP = load_network('HP')
        LOTR = load_network('LOTR')
        return nx.union(HP, LOTR)
    

def load_LabTM():
    #download LabTM list for sentiment analysis

    # Direct URL to the raw LabMT file
    url = "https://journals.plos.org/plosone/article/file?id=10.1371/journal.pone.0026752.s001&type=supplementary"

    # Download the file
    r = requests.get(url)
    r.raise_for_status()  # check if download worked
    text = r.text

    # Split into lines
    lines = text.splitlines()

    # Skip any lines before the header 
    header_index = 0
    for i, line in enumerate(lines):
        if line.startswith("word"):
            header_index = i
            break

    # Parse the header line
    columns = lines[header_index].split('\t')

    # Parse the remaining lines into a list of dictionaries
    data = []
    for line in lines[header_index+1:]:
        values = line.split('\t')
        if len(values) == len(columns):
            data.append(dict(zip(columns, values)))

    #  mapping word to happiness_average
    word_scores = {row['word']: float(row['happiness_average']) for row in data}
    return word_scores
