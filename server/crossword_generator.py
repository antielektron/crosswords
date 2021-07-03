import json
import random
import numpy as np
from string import digits
import pathlib
import logging


def get_difficulty_threshold(lang: str, difficulty: int):
    return get_difficulty_threshold.thresholds[lang][difficulty]


get_difficulty_threshold.thresholds = {
    'de': {
        0: 12,
        1: 6,
        2: 0
    },
    'en': {
        0: 200,
        1: 100,
        2: 10
    }
}


def get_database(lang: str = "en") -> dict:
    if lang not in get_database._dbs:
        current_folder = pathlib.Path(__file__).parents[0]
        db_file = str(current_folder / f"{lang}.json")

        logging.info("loading database: %s", lang)

        with open(db_file, "r") as f:
            db = json.load(f)
            get_database._dbs[lang] = db

        logging.info("database loaded")

    return get_database._dbs[lang]


get_database._dbs = {}


class NoDataException(Exception):
    pass


class WordInfo(object):
    def __init__(self, word: str, y: int, x: int, is_vertical: bool, database: dict, opposite_prefix: str = "opposite of", synonym_prefix: str = "other word for"):
        self._dictionary_database = database
        self._y = y
        self._x = x
        self._word = word
        self._hint = None
        self._is_vertical = is_vertical

        self.opposite_prefix = opposite_prefix
        self.synonym_prefix = synonym_prefix

        self.choose_info()

    def get_attribute(self, attr: str):
        attr = self._dictionary_database[self._word][attr]
        if attr is None or len(attr) == 0:
            raise NoDataException
        return attr

    def get_best_antonym(self) -> str:
        antonyms = self.get_attribute("antonyms")
        return random.choice(antonyms)

    def get_best_synonym(self) -> str:
        synonyms = self.get_attribute("synonyms")
        return random.choice(synonyms)

    def get_best_sense(self) -> str:
        senses = self.get_attribute("senses")
        return random.choice(senses)

    def choose_info(self, n: int = 1):
        assert n <= 4
        # first choose antonyms, then synonyms, then senses

        hints = []

        try:
            antonyms = self.get_attribute("antonyms")
            antonyms = [f"{self.opposite_prefix} {w}" for w in antonyms]
            hints = hints + antonyms
        except NoDataException:
            pass

        try:
            synonyms = self.get_attribute("synonyms")
            synonyms = [f"{self.synonym_prefix} {w}" for w in synonyms]

            hints = hints + synonyms
        except NoDataException:
            pass

        try:
            senses = self.get_attribute("senses")
            hints = hints + senses
        except NoDataException:
            pass

        final_hints = []
        for i in range(n):
            choice = random.choice(hints)
            hints.remove(choice)
            final_hints.append(choice)

        if n == 1:
            self._hint = final_hints[0]
            return

        hint_symbols = ['a)', 'b)', 'c)', 'd)']

        self._hint = ""
        for i in range(n):
            self._hint += hint_symbols[i] + " " + final_hints[i] + ". "

    def get_hint(self) -> str:
        return self._hint

    def get_hint_location(self):
        x = self._x if self._is_vertical else self._x - 1
        y = self._y - 1 if self._is_vertical else self._y
        return (y, x)

    def is_vertical(self):
        return self._is_vertical


def create_word_grid(w: int, h: int, lang_code: str = "en", target_density: float = 0.5, difficulty: int = 0):
    logging.info("generate new crossword with params: w:%s h:%s lang:%s density:%s difficulty:%s",
                 str(w),
                 str(h),
                 lang_code,
                 str(target_density),
                 str(difficulty))

    t_num_translations = get_difficulty_threshold(lang = lang_code, difficulty = difficulty)

    database = get_database(lang=lang_code)
    list_words = list(database.keys())

    grid = np.full(shape=(h, w), dtype=np.unicode, fill_value=' ')

    locations = {}

    word_hints = {}

    def store_location(char: str, y: int, x: int):
        assert len(char) == 1

        if char not in locations:
            locations[char] = []

        locations[char].append([y, x])

    remove_digits = str.maketrans('', '', digits)
    n_words = len(list_words)

    def get_word(max_length: int, min_length=0):
        assert max_length > 1

        index = random.randint(0, n_words-1)
        word = list_words[index][:]

        num_translations = database[word]['num_translations']
        t = t_num_translations

        while len(word) >= max_length or not word.isalnum() or len(word) <= min_length or num_translations < t:
            index = random.randint(0, n_words-1)
            word = list_words[index][:]
            num_translations = database[word]['num_translations']

        return word

    def normalize_word(word: str):
        word = word.translate(remove_digits)
        return word.lower()

    opposite_prefix = "opposite of" if lang_code == "en" else "Gegenteil von"
    synonym_prefix = "other word for" if lang_code == "en" else "anderes Wort für"

    def place_word(word: str, y: int, x: int, vertical: bool = False):
        normalized_word = normalize_word(word)
        n = len(normalized_word)
        if vertical:
            assert grid.shape[0] - n >= y
            for i, char in enumerate(normalized_word):
                grid[y + i, x] = char
                store_location(char, y+i, x)
        else:
            assert grid.shape[1] - n >= x
            for i, char in enumerate(normalized_word):
                grid[y, x + i] = char
                store_location(char, y, x+i)

        word_hints[normalized_word] = WordInfo(
            word, y, x, vertical, database, opposite_prefix, synonym_prefix)

    def density():
        return 1 - (grid == " ").sum() / (w * h)

    def check_if_fits(word: str, y: int, x: int, vertical: bool):
        n = len(word)
        if vertical:

            # check if there is space before and after
            if y - 1 >= 0 and grid[y - 1, x] != " ":
                return False
            if y + n < grid.shape[0] and grid[y+n, x] != " ":
                return False

            if grid.shape[0] - n < y or y < 0:
                # print("over board")
                return False

            for i, char in enumerate(word):
                char_x = x
                char_y = y + i

                if not (grid[char_y, char_x] == " " or grid[char_y, char_x] == char):
                    # print("not matching")
                    return False

                if grid[char_y, char_x] == " ":
                    # check for horizonatal neighbors:
                    if char_x - 1 >= 0 and grid[char_y, char_x - 1] != " ":
                        # print("3")
                        return False
                    if char_x + 1 < grid.shape[1] and grid[char_y, char_x + 1] != " ":
                        # print("4")
                        return False

        else:

            # check if there is space before and after
            if x - 1 >= 0 and grid[y, x - 1] != " ":
                return False
            if x + n < grid.shape[1] and grid[y, x + n] != " ":
                return False

            if grid.shape[1] - n < x or x < 0:
                # print("over board")
                return False

            for i, char in enumerate(word):
                char_x = x + i
                char_y = y

                if not (grid[char_y, char_x] == " " or grid[char_y, char_x] == char):
                    # print("not matching")
                    return False

                if grid[char_y, char_x] == " ":
                    # check for vertical neighbors:
                    if char_y - 1 >= 0 and grid[char_y - 1, char_x] != " ":
                        # print("1")
                        return False
                    if char_y + 1 < grid.shape[0] and grid[char_y + 1, char_x] != " ":
                        # print("2")
                        return False

        return True

    def get_crossover(word: str):
        # returns Tuple of: (y,x, is_vertical?) or None

        shuffled_order = list(range(len(word)))
        random.shuffle(shuffled_order)

        for index in shuffled_order:
            # check for existing locations
            char = word[index]
            if char in locations:
                char_locations = locations[char]

                for char_loc in char_locations:
                    # test vertical
                    y = char_loc[0] - index
                    x = char_loc[1]

                    if check_if_fits(word, y, x, vertical=True):
                        return (y, x, True)

                    # test horizontal
                    y = char_loc[0]
                    x = char_loc[1] - index

                    if check_if_fits(word, y, x, vertical=False):
                        return (y, x, False)

        return None

    def get_solution_word(min_length=8, max_length=100):
        word = get_word(min_length=min_length, max_length=max_length)

        # search for matching characters in locations
        locations_cpy = dict(locations)
        solution_locations = []

        for char in word:
            if char not in locations_cpy or len(locations_cpy[char]) == 0:
                # next try:
                return get_solution_word(min_length=min_length, max_length=max_length)

            location_candidates = locations_cpy[char]

            n = len(location_candidates)

            i = random.randint(0, n-1)

            solution_locations.append(location_candidates[i])
            del(location_candidates[i])

        return solution_locations

    min_shape = min(w, h, 30)

    # place first word:
    first_word = get_word(max_length=min_shape,
                          min_length=min(10, grid.shape[1] - 2))

    # find random place:
    x = random.randint(0, grid.shape[1] - len(first_word) - 1)
    y = random.randint(0, grid.shape[0] - 1)

    place_word(first_word, y, x, vertical=False)

    i = 0

    current_density = density()

    while current_density < target_density:
        word = get_word(max_length=(1 - current_density ** 0.4) * min_shape,
                        min_length=max(min(10, 0.5 * (1 - current_density ** 0.3) * min_shape), 2))

        normalized_word = normalize_word(word)

        if normalized_word in word_hints:
            continue

        # check if matching characters exist:
        crossover = get_crossover(normalized_word)

        i += 1
        if i % 1000 == 0:
            print(i)
        if i > 1200:
            break

        if crossover == None:
            current_density = density()
            continue

        y, x, is_vertical = crossover

        place_word(word, y, x, is_vertical)

        current_density = density()

    solution_word_locations = get_solution_word()

    logging.info("crossword generation done after %s iterations", str(i))
    return grid, word_hints, solution_word_locations
