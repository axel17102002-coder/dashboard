import csv
import os

print(os.getcwd())

const = ['_box_score','_comparison','_header','_play_by_play','_players','_points','_teams']

eurocup_files = []
euroleague_files = []
headers_dict = {}

for a in const:
    eurocup_files.append('data/eurocup' + a + '.csv')
    euroleague_files.append('data/euroleague' + a + '.csv')



for file in eurocup_files:
    try:
        # Abrir el archivo en modo lectura ('r')
        with open(file, mode='r', encoding='utf-8') as csv_file:
            # Crear un objeto reader
            csv_reader = csv.reader(csv_file, delimiter=',')
            header = next(csv_reader)
            headers_dict[file] = header
    except FileNotFoundError:
        print(f"{file} no existe")

with open('headers_output.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)

    # opcional: escribir encabezado del CSV

    writer.writerow(['file_name', 'headers'])

    for file, header in headers_dict.items():

        writer.writerow([file] + header)