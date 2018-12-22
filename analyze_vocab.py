import io
import json
import os
from collections import Counter
from postgres import Postgres

mecab_location = 'C:\\Program Files (x86)\\MeCab\\bin\\mecab.exe'

print('Connecting to DB...')

with open('db_url.txt', 'r') as db_url:
    db = Postgres(db_url.readline().strip())

print('Downloading scripts...')

scripts = db.all('SELECT * FROM scripts;', back_as='dict')

print(len(scripts), 'scripts found.')

for s in scripts:
    print(s['title'] + '...', end=' ')

    filename = s['title'].replace(' ', '_').replace('/', '_') + '.txt'
    filename_vocab = filename + '_vocab.txt'

    with io.open(filename, 'w', encoding='utf8') as script_file:
        script_file.write(s['script'])

    os.system('"' + mecab_location + '" ' + filename + ' -o ' + filename_vocab + ' -O wakati')  # noqa: E501

    with io.open(filename_vocab, 'r', encoding='utf8') as vocab_file:
        vocab_str = vocab_file.read().replace('\n', ' ')

    vocab = vocab_str.split()
    vocab_stats = Counter(vocab)
    stats_formatted = list(vocab_stats.items())
    stats_formatted.sort(key=lambda tup: tup[1], reverse=True)
    stats_json = json.dumps(stats_formatted)

    print(len(vocab_stats), 'unique vocab found. Uploading...', end=' ')

    query = 'UPDATE scripts SET vocab_stats = %(stats)s WHERE id = %(id)s;'
    db.run(query, {
        'stats': stats_json,
        'id': s['id']
    })

    print('Done.')

    os.remove(filename)
    os.remove(filename_vocab)
