class Implementation:
    def __init__(self, k_factor=32, base_rating=1000):
        self.k_factor = k_factor
        self.base_rating = base_rating
        self.players = {}

    def addPlayer(self, name, rating=None):
        """Adds a player with an optional initial rating."""
        if rating is None:
            rating = self.base_rating
        self.players[name] = float(rating)

    def getPlayerRating(self, name):
        """Returns the current rating of a player."""
        return self.players.get(name, self.base_rating)

    def getRatingList(self):
        """Returns a list of tuples with (player, rating) sorted by rating descending."""
        return sorted(self.players.items(), key=lambda item: item[1], reverse=True)

    def recordMatch(self, player1, player2, winner=None, draw=False):
        """
        Updates ratings for player1 and player2 based on match outcome.
        
        :param player1: Name of the first player
        :param player2: Name of the second player
        :param winner: Name of the winning player (if draw is False)
        :param draw: True if the match was a tie/draw
        """
        if player1 not in self.players:
            self.addPlayer(player1)
        if player2 not in self.players:
            self.addPlayer(player2)

        r1 = self.players[player1]
        r2 = self.players[player2]

        # Calculate expected scores
        e1 = 1 / (1 + 10 ** ((r2 - r1) / 400))
        e2 = 1 / (1 + 10 ** ((r1 - r2) / 400))

        # Determine actual scores
        if draw:
            s1, s2 = 0.5, 0.5
        elif winner == player1:
            s1, s2 = 1.0, 0.0
        elif winner == player2:
            s1, s2 = 0.0, 1.0
        else:
            raise ValueError(f"Winner must be '{player1}' or '{player2}' when draw is False")

        # Update and store new ratings
        self.players[player1] = r1 + self.k_factor * (s1 - e1)
        self.players[player2] = r2 + self.k_factor * (s2 - e2)