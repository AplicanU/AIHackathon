from fuzzywuzzy import process

def get_best_match(user_input, options, score_cutoff=90):
    matches = process.extract(user_input, options, limit=None)
    best_match = None
    highest_score = score_cutoff
    
    for match, score in matches:
        if score > highest_score:
            best_match, highest_score = match, score
    
    return best_match