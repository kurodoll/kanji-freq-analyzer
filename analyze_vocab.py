import io
import json
import os
from collections import Counter
from postgres import Postgres

mecab_location = 'C:\\Program Files (x86)\\MeCab\\bin\\mecab.exe'

print('Connecting to DB...')

with open('db_url.txt', 'r') as db_url:
    db = Postgres(db_url.readline().strip())

print('Loading scripts...')

scripts = db.all('SELECT id, title FROM scripts;', back_as='dict')

print(len(scripts), 'scripts found.')


def clean(str):
    bad_chars = [' ', '/', ':']

    for c in bad_chars:
        str = str.replace(c, '_')

    return str


for s in scripts:
    print(s['title'] + '...', end=' ')

    filename = 'scripts\\' + clean(s['title']) + '.txt'
    filename_vocab = filename + '_vocab.txt'

    if not os.path.isfile(filename):
        script = db.one(
            'SELECT script FROM scripts WHERE id = %(id)s;',
            {'id': s['id']},
            back_as='dict'
        )

        with io.open(filename, 'w', encoding='utf8') as script_file:
            script_file.write(script)

    os.system('"' + mecab_location + '" ' + filename + ' -o ' + filename_vocab + ' -O wakati')  # noqa: E501

    with io.open(filename_vocab, 'r', encoding='utf8') as vocab_file:
        vocab_str = vocab_file.read().replace('\n', ' ')

    vocab = vocab_str.split()
    vocab_stats = Counter(vocab)
    stats_formatted = list(vocab_stats.items())
    stats_formatted.sort(key=lambda tup: tup[1], reverse=True)
    stats_json = json.dumps(stats_formatted)

    print(len(vocab_stats), 'unique vocab found. Uploading...', end=' ')

    query = 'UPDATE scripts SET n_unique_vocab = %(vocab)s, vocab_stats = %(stats)s WHERE id = %(id)s;'  # noqa: E501
    db.run(query, {
        'vocab': len(vocab_stats),
        'stats': stats_json,
        'id': s['id']
    })

    print('Done.')

    # os.remove(filename)
    os.remove(filename_vocab)
