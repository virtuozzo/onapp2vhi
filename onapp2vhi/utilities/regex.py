import regex


JSON_REGEX = regex.compile(
    r'''
    \s*
    (?P<value>
        (?P<object>   \{\s*
                      (?: (?P<member>(?&string) \s*:\s* (?&value))
                          ( \s*,\s* (?&member) )* )?
                      \s*\})
      | (?P<array>    \[\s* ((?&value) (\s*,\s* (?&value))*)? \s*\])
      | (?P<string>   " [^"\\]* (?: \\. | [^"\\]* )* ")
      | (?P<number>   (?P<integer> -? (?: 0 | [1-9][0-9]* ))
                      (?: \. [0-9]* )?
                      (?: [eE] [-+]? [0-9]+ )?)
      | true
      | false
      | null
    )
    \s*
    ''',
    flags=regex.VERBOSE | regex.UNICODE)    # pylint: disable=no-member
