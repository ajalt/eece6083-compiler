import tokens

def tokenize_word(word):
    pos = 0
    length = len(word)
    
    while pos < length:
        pass
    
    
    
def tokenize_file(filename):
    with open(filename) as file:
        for line in file:
            for word in line.split():
                for token in tokenize(word):
                    yield token