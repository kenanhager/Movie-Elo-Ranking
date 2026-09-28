import csv

movie_elo = []

with open('save.csv', 'r', newline='') as file:
    read = csv.reader(file)
    for row in read:
        title = row[0]
        rating = float(row[1])  # Convert rating to float directly
        movie_elo.append([title, rating])


sorted_list = sorted(movie_elo, key=lambda x: x[1], reverse=True)

with open('save.csv', 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerows(sorted_list)

