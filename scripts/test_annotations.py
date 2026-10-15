import os, sys
os.chdir('E:\\xampp\\htdocs\\3DGame')
print('CWD:', os.getcwd())

print('1. Importing modules...')
try:
    import objaverse
    print('   objaverse OK')
except Exception as e:
    print(f'   objaverse FAIL: {e}')
    sys.exit(1)

print('2. Loading annotations...')
try:
    annotations = objaverse.load_annotations()
    print(f'   Loaded {len(annotations)} annotations')
except Exception as e:
    print(f'   load_annotations FAIL: {e}')
    sys.exit(1)

print('3. Filtering educational models...')
EDU_KEYWORDS = [
    'sphere', 'cube', 'cylinder', 'cone', 'pyramid', 'torus', 'polyhedron',
    'cell', 'dna', 'rna', 'protein', 'virus', 'bacteria', 'organ', 'heart',
    'brain', 'lung', 'kidney', 'skeleton', 'skull', 'eye', 'ear', 'tooth',
    'molecule', 'atom', 'water', 'methane', 'ethanol', 'benzene', 'crystal',
    'gear', 'pulley', 'lever', 'spring', 'magnet', 'circuit', 'engine',
    'microscope', 'beaker', 'flask', 'test_tube', 'bunsen', 'centrifuge',
    'book', 'pencil', 'ruler', 'calculator', 'compass', 'notebook',
    'globe', 'earth', 'moon', 'mars', 'planet', 'telescope', 'map',
    'leaf', 'flower', 'root', 'seed', 'photosynthesis',
    'fossil', 'dinosaur', 'artifact', 'ancient', 'pottery'
]
edu_uids = []
for uid, ann in annotations.items():
    text = f"{ann.get('name','')} {ann.get('description','')} {' '.join([t['name'] for t in ann.get('tags',[])])}".lower()
    if any(kw in text for kw in EDU_KEYWORDS):
        edu_uids.append(uid)
print(f'   Found {len(edu_uids)} educational models')

if len(edu_uids) > 0:
    sample = edu_uids[:10]
    print(f'   First 10 UIDs:')
    for uid in sample:
        ann = annotations[uid]
        name = ann.get('name', 'unnamed')
        tags = [t['name'] for t in ann.get('tags', [])[:3]]
        print(f'     {uid}: {name} - tags: {tags}')
else:
    print('   NO models found! Checking all annotations names...')
    names = [annotations[uid].get('name','') for uid in list(annotations.keys())[:20]]
    print(f'   Sample names: {names}')
