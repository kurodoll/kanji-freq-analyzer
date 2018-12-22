import io
import json
import os
from postgres import Postgres
from tqdm import tqdm

with open('db_url.txt', 'r') as db_url:
    db = Postgres(db_url.readline().strip())


# * Functions
def analyze(script, analyzed_once=False):
    kanji_counts = {}

    for c in script['script']:
        if c not in kanji_counts.keys():
            kanji_counts[c] = 1
        else:
            kanji_counts[c] += 1

    print(len(kanji_counts.keys()), 'unique characters in', script['filename'])

    if not analyzed_once:
        with db.get_cursor() as cursor:
            for kanji in tqdm(kanji_counts.keys()):
                query = 'INSERT INTO kanji (character, count) VALUES (%(kanji)s, %(count)s) ON CONFLICT (character) DO UPDATE SET count = kanji.count + %(count)s;'  # noqa: E501
                cursor.execute(query, {
                    'kanji': kanji,
                    'count': kanji_counts[kanji]
                })

            cursor.fetchall()

        db.run(
            "UPDATE scripts SET status = 'complete' WHERE id = %(id)s",
            {'id': script['id']})

    kanji_counts_formatted = []
    n_unique_kanji = 0

    for kanji in kanji_counts.keys():
        kanji_counts_formatted.append([kanji, kanji_counts[kanji]])

        if (kanji >= '\u4e00' and kanji <= '\u9faf') or (kanji >= '\u3400' and kanji <= '\u4dbf'):  # noqa: E501
            n_unique_kanji += 1

    kanji_counts_formatted.sort(key=lambda tup: tup[1], reverse=True)
    stats_json = json.dumps(kanji_counts_formatted)

    query = 'UPDATE scripts SET n_unique_kanji = %(kanji)s, kanji_stats = %(stats)s WHERE id = %(id)s;'  # noqa: E501
    db.run(query, {
        'kanji': n_unique_kanji,
        'stats': stats_json,
        'id': script['id']
    })


# * Program
n_scripts = db.one('SELECT count(*) FROM scripts;')
n_modq = db.one("SELECT count(*) FROM scripts WHERE status = 'modq';")
n_approved = db.one("SELECT count(*) FROM scripts WHERE status = 'approved';")
print(n_scripts, 'scripts |', n_modq, 'in moderation queue |', n_approved, 'to be analyzed')  # noqa: E501

if n_modq > 0:
    modq = db.all(
        "SELECT * FROM scripts WHERE status = 'modq';",
        back_as='dict'
    )

    for script in modq:
        print('\n' + script['title'] + ' (' + script['filename'] + ')')

        view_script = input('View script? (y/n) ')
        if view_script[0] == 'y' or view_script[0] == 'Y':
            script_file = io.open(script['filename'], 'w', encoding='utf8')
            script_file.write(script['script'])
            script_file.close()

            os.system('notepad ' + script['filename'])

            input('Press enter when done')
            os.remove(script['filename'])

        action = input('Action? (approve/deny) ')
        if action == 'approve':
            db.run(
                "UPDATE scripts SET status = 'approved' WHERE id = %(id)s",
                {'id': script['id']})
        elif action == 'deny':
            db.run(
                "UPDATE scripts SET status = 'denied' WHERE id = %(id)s",
                {'id': script['id']})
        else:
            print('Invalid option; no action will be taken for now')

print('\nNewly approved scripts will now be analyzed')

to_analyze = db.all(
    "SELECT * FROM scripts WHERE status = 'approved';",
    back_as='dict')

for script in to_analyze:
    analyze(script)

print('\nScripts without stats saved will now be analyzed')
reanalyze = input('Reanalyze all scripts? (y/n) ')

if reanalyze == 'y' or reanalyze == 'Y':
    query = "SELECT * FROM scripts;"
else:
    query = "SELECT * FROM scripts WHERE n_unique_kanji IS NULL OR kanji_stats IS NULL;"  # noqa: E501

analyze_stats_queue = db.all(query, back_as='dict')

print(len(analyze_stats_queue), 'scripts to analyze')

for script in analyze_stats_queue:
    analyze(script, True)
