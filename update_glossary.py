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

def find_term_entry(terms_data, term):
    """Locate the term object in 'terms_data' (case-insensitive)."""
    for entry in terms_data:
        if entry["term"].lower() == term.lower():
            return entry
    return None

def definition_exists(term_entry, discipline, new_definition):
    """
    Check if the exact (discipline + definition) pair already exists
    for the given term_entry.
    """
    for def_obj in term_entry["definitions"]:
        same_discipline = def_obj["discipline"].strip().lower() == discipline.strip().lower()
        same_definition = def_obj["definition"].strip().lower() == new_definition.strip().lower()
        if same_discipline and same_definition:
            return True
    return False

def text_similarity(a, b):
    """
    Returns a similarity score (0.0 to 1.0+) between two text strings,
    using a spaCy model. Higher = more similar.
    """
    doc_a = nlp(a)
    doc_b = nlp(b)
    return doc_a.similarity(doc_b)

##############################
#        MAIN PROCESS       #
##############################

def process_definition(discipline, term, new_definition):
    """
    Logic for handling a new submission:
      1) If the term does NOT exist in terms.json:
         - Create a new term entry. 
         - (No conflict/agreement since there's nothing to compare yet.)
      2) If the term DOES exist:
         - Compare 'new_definition' to all existing definitions for that term.
         - Find the maximum similarity across all definitions.
         - If max similarity >= SIMILARITY_THRESHOLD => add to agreement.json
           else => add to conflicting.json
         - Also add the new definition to terms.json if it's not already there.
    """

    term_entry = find_term_entry(terms_data, term)

    # 1) New term
    if not term_entry:
        new_entry = {
            "term": term,
            "definitions": [
                {
                    "discipline": discipline,
                    "definition": new_definition
                }
            ]
        }
        terms_data.append(new_entry)
        print(f"Added new term '{term}' to terms.json (no existing definitions to compare).")
        return

    # 2) Existing term: Compare to all existing definitions
    existing_definitions = term_entry["definitions"]

    if not existing_definitions:
        term_entry["definitions"] = [
            {
                "discipline": discipline,
                "definition": new_definition
            }
        ]
        print(f"Term '{term}' existed but had no definitions. Added new definition.")
        return

    # Compute similarity to each existing definition
    similarities = []
    for def_obj in existing_definitions:
        existing_text = def_obj["definition"]
        score = text_similarity(existing_text, new_definition)
        similarities.append(score)

    # Determine if it's similar or conflicting based on max similarity
    max_similarity = max(similarities)

    if max_similarity >= SIMILARITY_THRESHOLD:
        # Agreement
        agreement_data.append({
            "term": term,
            "discipline": discipline,
            "definition": new_definition
        })
        print(f"New definition for '{term}' added to agreement.json (max similarity={max_similarity:.2f}).")
    else:
        # Conflict
        conflicting_data.append({
            "term": term,
            "discipline": discipline,
            "definition": new_definition
        })
        print(f"New definition for '{term}' added to conflicting.json (max similarity={max_similarity:.2f}).")

    # Finally, add it to terms.json if it's not a duplicate
    if not definition_exists(term_entry, discipline, new_definition):
        term_entry["definitions"].append({
            "discipline": discipline,
            "definition": new_definition
        })
        print(f"Added new definition for term '{term}' under discipline '{discipline}' to terms.json.")
    else:
        print(f"Skipping duplicate definition for '{term}' under '{discipline}'.")

##############################
#     LOAD JSON FILES       #
##############################

terms_data = load_json(TERMS_FILE)         
agreement_data = load_json(AGREEMENT_FILE)
conflicting_data = load_json(CONFLICTING_FILE)

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
print("Done updating JSON files!")

##############################
#       PUSH TO GITHUB       #
##############################

from git import Repo

repo = Repo('.')
repo.git.add('data/terms.json')
repo.git.add('data/agreement.json')
repo.git.add('data/conflicting.json')
repo.index.commit("Update JSON files from new form submissions")
origin = repo.remote(name='origin')
origin.push()
