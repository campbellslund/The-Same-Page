import json
import os

# Helpers
def load_json(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

def find_term_entry(terms_data, term):
    for entry in terms_data:
        if entry["term"].lower() == term.lower():
            return entry
    return None

import spacy
nlp = spacy.load("en_core_web_sm")

def text_similarity(a, b):
    # Convert each string to a spaCy doc
    doc_a = nlp(a)
    doc_b = nlp(b)
    return doc_a.similarity(doc_b)

def process_definition(discipline, term, new_definition):
    # Check if term exists
    term_entry = find_term_entry(terms_data, term)
    
    if not term_entry:
        # If no existing term, create a new entry in terms.json
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
        print(f"Added new term '{term}' to terms.json.")
    else:
        # Compare new definition with existing definitions
        # e.g., with the definition for discipline == "AI" or all definitions
        # For a simplified example, compare with the AI definition only:
        ai_def_obj = next((d for d in term_entry["definitions"] if d["discipline"] == "AI"), None)
        if ai_def_obj:
            similarity_score = text_similarity(ai_def_obj["definition"], new_definition)
            if similarity_score >= 0.8:
                # Very similar -> agreement
                agreement_data.append({
                    "term": term,
                    "discipline": discipline,
                    "definition": new_definition
                })
                print(f"New definition for '{term}' added to agreement.json (similarity={similarity_score:.2f})")
            elif similarity_score < 0.4:
                # Very different -> conflict
                conflicting_data.append({
                    "term": term,
                    "discipline": discipline,
                    "definition": new_definition
                })
                print(f"New definition for '{term}' added to conflicting.json (similarity={similarity_score:.2f})")
            else:
                # Partially similar -> your call
                # For now, let's default to conflict or prompt user
                print(f"Partial similarity for '{term}' (similarity={similarity_score:.2f}). Manual check recommended.")
                # Could store it somewhere or put it in conflict by default:
                conflicting_data.append({
                    "term": term,
                    "discipline": discipline,
                    "definition": new_definition
                })
        else:
            # If there's no AI definition to compare with, you might compare with other disciplines
            # or just add this definition to the same term entry
            term_entry["definitions"].append({
                "discipline": discipline,
                "definition": new_definition
            })
            print(f"Added definition for existing term '{term}' (no AI definition found).")

#########################################################################
           
# Read Existing JSON Files
TERMS_FILE = 'data/terms.json'
AGREEMENT_FILE = 'data/agreement.json'
CONFLICTING_FILE = 'data/conflicting.json'

terms_data = load_json(TERMS_FILE)         # List of term objects
agreement_data = load_json(AGREEMENT_FILE) # List of definitions
conflicting_data = load_json(CONFLICTING_FILE) # List of definitions

# Fetch New Submissions from the Google Sheet
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 1. Authorize with credentials.json
scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive.file","https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)

# 2. Open the Google Sheet by name or URL
SHEET_NAME = "Getting on The Same Page (Responses)"
sheet = client.open(SHEET_NAME).sheet1  # assume your form responses are in the first sheet

# 3. Fetch all rows
rows = sheet.get_all_values()  # returns list of lists, each representing a row

# Loop Over New Rows & Update JSON
for row in rows[1:]:  # skip header
    discipline = row[1]
    term = row[2]
    definition = row[3]
    process_definition(discipline, term, definition)

# Save updated JSONs
save_json(TERMS_FILE, terms_data)
save_json(AGREEMENT_FILE, agreement_data)
save_json(CONFLICTING_FILE, conflicting_data)
print("Done updating JSON files!")

# Push changes to GitHub
from git import Repo

repo = Repo('.')
repo.git.add('data/terms.json')
repo.git.add('data/agreement.json')
repo.git.add('data/conflicting.json')
repo.index.commit("Update JSON files from new form submissions")
origin = repo.remote(name='origin')
origin.push()



