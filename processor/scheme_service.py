import json
import os
from difflib import get_close_matches

class SchemeService:
    def __init__(self, schemes_dir="data/schemes"):
        self.schemes_dir = schemes_dir
        self.schemes = {}
        self._load_schemes()

    def _load_schemes(self):
        if not os.path.exists(self.schemes_dir):
            print(f"Directory {self.schemes_dir} not found.")
            return
        
        count = 0
        for filename in os.listdir(self.schemes_dir):
            if filename.endswith(".json"):
                try:
                    with open(os.path.join(self.schemes_dir, filename), 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if 'scheme_name' in data:
                            name = data['scheme_name']
                            self.schemes[name] = data
                            count += 1
                except Exception as e:
                    print(f"Error loading {filename}: {e}")
        print(f"Loaded {count} schemes from {self.schemes_dir}.")

    def get_scheme_by_name(self, query):
        if not query: return None
        names = list(self.schemes.keys())
        # Try exact match first (case-insensitive)
        for name in names:
            if query.lower().strip() in name.lower():
                return self.schemes[name]
                
        matches = get_close_matches(query, names, n=1, cutoff=0.3) # Lower cutoff
        if matches:
            return self.schemes[matches[0]]
        return None

    def get_field(self, scheme_name, field_name):
        scheme = self.get_scheme_by_name(scheme_name)
        if scheme:
            return scheme.get(field_name)
        return None

if __name__ == "__main__":
    service = SchemeService()
    test_name = "HDFC Mid Cap"
    result = service.get_scheme_by_name(test_name)
    if result:
        print(f"Found: {result['scheme_name']}")
    else:
        print(f"No match for '{test_name}'")
