import io
import os
from postgres import Postgres

mecab_location = 'C:\\Program Files (x86)\\MeCab\\bin\\mecab.exe'

with open('db_url.txt', 'r') as db_url:
    db = Postgres(db_url.readline().strip())

scripts = db.all(
    'SELECT * FROM scripts WHERE vocab_stats IS NULL;',
    back_as='dict')

for s in scripts:
    filename = s['title'].replace(' ', '_') + '.txt'

    with io.open(filename, 'w', encoding='utf8') as script_file:
        script_file.write(s['script'])

    os.system('"' + mecab_location + '" ' + filename + ' -o ' + filename + '_vocab.txt')  # noqa: E501

    os.remove(filename)
    os.remove(filename + '_vocab.txt')
