import json
import os
import spacy
nlp = spacy.load("en_core_web_sm")
import gspread
from oauth2client.service_account import ServiceAccountCredentials

##############################
#       CONFIG / GLOBALS    #
##############################

TERMS_FILE = 'data/terms.json'
AGREEMENT_FILE = 'data/agreement.json'
CONFLICTING_FILE = 'data/conflicting.json'
NEW_TERMS_FILE = 'data/new_terms.json'  # <== NEW FILE

SIMILARITY_THRESHOLD = 0.8  # Adjust this as needed

##############################
#       HELPER FUNCTIONS    #
##############################

def load_json(filepath):
    """Load data from a JSON file, or return an empty list if it doesn't exist."""
    if not os.path.exists(filepath):
        return []
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(filepath, data):
    """Save data to a JSON file, pretty-printed."""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

def find_term_entry(term_list, term):
    """Locate the term object in 'term_list' (case-insensitive)."""
    for entry in term_list:
        if entry["term"].lower() == term.lower():
            return entry
    return None

def text_similarity(a, b):
    """
    Returns a similarity score (0.0 to 1.0+) between two text strings,
    using a spaCy model. Higher = more similar.
    """
    doc_a = nlp(a)
    doc_b = nlp(b)
    return doc_a.similarity(doc_b)

##############################
#       MAIN PROCESS        #
##############################

def process_definition(discipline, term, new_definition):
    """
    Updated logic:
      1) If the term does NOT exist in terms.json, add it to new_terms.json
         (no similarity check, no classification).
      2) If the term DOES exist in terms.json:
         - Compare new_definition to all existing definitions for that term.
         - If max similarity < SIMILARITY_THRESHOLD => conflicting.json
           else => agreement.json
         - Do NOT add the new definition to terms.json.
    """

    term_entry = find_term_entry(terms_data, term)

    # (1) New term: store in new_terms.json
    if not term_entry:
        add_new_term(discipline, term, new_definition)
        return

    # (2) Existing term: compare & classify
    existing_definitions = term_entry["definitions"]
    similarities = []
    for def_obj in existing_definitions:
        existing_text = def_obj["definition"]
        score = text_similarity(existing_text, new_definition)
        similarities.append(score)

    max_similarity = max(similarities)

    if max_similarity < SIMILARITY_THRESHOLD:
        # Conflict
        conflicting_data.append({
            "term": term,
            "discipline": discipline,
            "definition": new_definition
        })
        print(f"New definition for '{term}' => conflicting.json (max sim={max_similarity:.2f}).")
    else:
        # Agreement
        agreement_data.append({
            "term": term,
            "discipline": discipline,
            "definition": new_definition
        })
        print(f"New definition for '{term}' => agreement.json (max sim={max_similarity:.2f}).")

def add_new_term(discipline, term, new_definition):
    """
    Store a truly new term (not found in terms.json) into new_terms.json.
    If the term already exists in new_terms.json, just append its definitions.
    """
    existing_new_term = find_term_entry(new_terms_data, term)

    if not existing_new_term:
        # Create a new entry in new_terms.json
        new_term_obj = {
            "term": term,
            "definitions": [
                {
                    "discipline": discipline,
                    "definition": new_definition
                }
            ]
        }
        new_terms_data.append(new_term_obj)
        print(f"New term '{term}' => new_terms.json.")
    else:
        # Append the definition if it's not already there
        # (Optional: you could do a check to avoid duplicates)
        existing_new_term["definitions"].append({
            "discipline": discipline,
            "definition": new_definition
        })
        print(f"Appended another definition for new term '{term}' => new_terms.json.")

##############################
#     LOAD JSON FILES       #
##############################

terms_data = load_json(TERMS_FILE)         
agreement_data = load_json(AGREEMENT_FILE)
conflicting_data = load_json(CONFLICTING_FILE)
new_terms_data = load_json(NEW_TERMS_FILE) 

##############################
#  FETCH GOOGLE SHEET ROWS   #
##############################

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)

SHEET_NAME = "Getting on The Same Page (Responses)"
sheet = client.open(SHEET_NAME).sheet1  # Form responses in the first sheet

rows = sheet.get_all_values()  # list of lists representing each row

##############################
#    PROCESS EACH SUBMISSION #
##############################

# Row format assumptions (based on your form):
#  0 => Timestamp
#  1 => Discipline
#  2 => Term
#  3 => Definition/Connotation

for row in rows[1:]:  # skip the header
    discipline = row[1].strip().lower()
    term = row[2].strip().lower()
    definition = row[3].strip().lower()
    process_definition(discipline, term, definition)

##############################
#   SAVE UPDATED JSON FILES  #
##############################

save_json(TERMS_FILE, terms_data)
save_json(AGREEMENT_FILE, agreement_data)
save_json(CONFLICTING_FILE, conflicting_data)
save_json(NEW_TERMS_FILE, new_terms_data)  
print("Done updating JSON files!")

##############################
#       PUSH TO GITHUB       #
##############################

from git import Repo

repo = Repo('.')
repo.git.add('data/terms.json')
repo.git.add('data/agreement.json')
repo.git.add('data/conflicting.json')
repo.git.add('data/new_terms.json')  
repo.index.commit("Update JSON files from new form submissions")
origin = repo.remote(name='origin')
origin.push()
