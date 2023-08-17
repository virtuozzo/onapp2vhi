import regex


JSON_REGEX = regex.compile(r'\{(?:[^{}]|(?R))*\}')
