from elopy import Implementation
import csv
import random

movie_elo = []
MIN_RATING = 800
MAX_RATING = 2000
elo = Implementation()
init_words = ["New", "Update", "Continue"]


restart = input("New, Update or Continue: ")
while not (restart in init_words):
    restart = input("Try agian: \nNew, Update or Continue: ")
if restart == "Update":
    with open('save.csv', 'r', newline='') as file:
        read = csv.reader(file)
        for row in read:
            title = row[0]
            rating = float(row[1]) if row[1] else 0.0  # Convert rating to float directly
            movie_elo.append([title, rating])
    with open('ratings.csv', 'r', newline='') as file:
        read = csv.reader(file)
        next(read, None)  # Skip header row
        for row in read:
            title = row[1]
            rating = float(row[4]) if row[4] else 0.0  # Convert rating to float directly
            if (not ([title, rating] in movie_elo)):
                rating = MIN_RATING + ((rating - 0.5)/4.5)*(MAX_RATING-MIN_RATING)
                elo.addPlayer(title, rating = rating)
    for i in movie_elo:
        elo.addPlayer(i[0], rating = i[1])
    
                
elif restart == "New":
    with open('ratings.csv', 'r', newline='') as file:
        read = csv.reader(file)
        next(read, None)  # Skip header row
        for row in read:
            title = row[1]
            rating = float(row[4]) if row[4] else 0.0  # Convert rating to float directly
            movie_elo.append([title, rating])

    for i in movie_elo:
        i[1] = MIN_RATING + ((i[1] - 0.5)/4.5)*(MAX_RATING-MIN_RATING)
        elo.addPlayer(i[0], rating = i[1])

else:
    with open('save.csv', 'r', newline='') as file:
        read = csv.reader(file)
        for row in read:
            title = row[0]
            rating = row[1]  # Convert rating to float directly
            movie_elo.append([title, rating])
            elo.addPlayer(title, rating = rating)

inps = ["1", "2", "3", "q"]

random_items = random.sample(movie_elo, 2)
print("1. "+str(random_items[0][0])+": " +str(elo.getPlayerRating(random_items[0][0])))
print("2. " + str(random_items[1][0])+": " +str(elo.getPlayerRating(random_items[1][0])))
while inp := input("1, 2, tie (3), or Quit (q): "):
    while not(inp in inps):
        inp = input("try agian: \n1, 2, tie (3), or Quit (q): ")
    if inp == "q":
        break
    elif (inp == "3"):
        elo.recordMatch(random_items[0][0], random_items[1][0], draw = True)
    else:   
        print(random_items[int(inp)-1][0])
        elo.recordMatch(random_items[0][0], random_items[1][0], winner=random_items[int(inp)-1][0])

    print(str(random_items[0][0])+": "+str(elo.getPlayerRating(random_items[0][0])))
    print(str(random_items[1][0])+": "+str(elo.getPlayerRating(random_items[1][0])))
    random_items[0][1] = elo.getPlayerRating(random_items[0][0])
    random_items[1][1] = elo.getPlayerRating(random_items[1][0])
    print()
    print()
    random_items = random.sample(movie_elo, 2)
    print("1. "+str(random_items[0][0])+": " +str(elo.getPlayerRating(random_items[0][0])))
    print("2. " + str(random_items[1][0])+": " +str(elo.getPlayerRating(random_items[1][0])))


sorted_list = sorted(movie_elo, key=lambda x: x[1], reverse=True)

with open('save.csv', 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerows(movie_elo)

