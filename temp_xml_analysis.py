import xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter

xml_dir = Path(r'C:\Users\neele\Downloads\dataset_xml_format\dataset_xml_format')
xml_files = list(xml_dir.glob('*.xml'))

classes = Counter()
images_with_drones = 0
total_detections = 0
empty_annots = 0

for xml_file in xml_files:
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        objects = root.findall('object')
        if len(objects) == 0:
            empty_annots += 1
        else:
            images_with_drones += 1
            
        for obj in objects:
            name = obj.find('name')
            if name is not None:
                classes[name.text] += 1
                total_detections += 1
    except Exception as e:
        print(f'Error: {e}')

print(f'Total XML files: {len(xml_files)}')
print(f'Images with drones: {images_with_drones}')
print(f'Empty annotations: {empty_annots}')
print(f'Total detections: {total_detections}')
print(f'\nClass distribution:')
for cls, count in classes.most_common():
    pct = 100*count/total_detections if total_detections > 0 else 0
    print(f'  {cls}: {count} ({pct:.1f}%)')
