import enum
import json
import logging
import numpy as np

from . import crossword_generator

from enum import Enum

import traceback


class HintOrientation(Enum):
    VERTICAL = 0
    HORIZONTAL = 1
    BOTH = 2


class FieldType(Enum):
    EMPTY = 0
    HINT = 1
    LETTER = 2


class Field(object):
    def __init__(self, field_type: FieldType = FieldType.EMPTY):
        self._field_type = field_type

    def get_type(self) -> FieldType:
        return self._field_type

    def get_content(self) -> str:
        return None

    def serialize(self):
        type_names = {
            FieldType.EMPTY: "empty",
            FieldType.HINT: "hint",
            FieldType.LETTER: "letter"
        }

        return {
            'cell_type': type_names[self._field_type]
        }


class HintField(Field):
    def __init__(self, horizontal_hint: str = None, vertical_hint: str = None):
        super().__init__(field_type=FieldType.HINT)

        self._horizontal_hint = horizontal_hint
        self._vertical_hint = vertical_hint

    def get_horizontal_hint(self) -> str:
        return self._horizontal_hint

    def get_vertical_hint(self) -> str:
        return self._vertical_hint

    def set_horizintal_hint(self, hint: str):
        self._horizontal_hint = hint

    def set_vertical_hint(self, hint: str):
        self._vertical_hint = hint

    def serialize(self):
        result = super().serialize()
        result['vertical_hint'] = self._vertical_hint
        result['horizontal_hint'] = self._horizontal_hint

        return result


class LetterField(Field):
    def __init__(self, letter: str):
        assert len(letter) <= 1

        super().__init__(field_type=FieldType.LETTER)

        self._letter = letter.lower()
        self._revealed = False
        self._user_letter = ""

    def get_content(self) -> str:
        return self._letter.upper()

    def get_user_content(self) -> str:
        return self._user_letter.upper()

    def reveal(self):
        self._revealed = True

    def user_input(self, input_letter):
        assert len(input_letter) <= 1
        self._user_letter = input_letter.lower()

    def is_revealed(self) -> bool:
        return self._revealed

    def serialize(self):
        result = super().serialize()
        result['letter'] = self._letter

        return result


class Grid(object):
    def __init__(self, width: int, height: int, lang_code: str, density=0.55):
        self._width = width
        self._height = height
        self._lang_code = lang_code
        self._density = density
        self._grid = []
        self._solution_locations = None
        try:
            self._build_grid()
        except Exception as e:
            logging.error("error in generation", str(e))
            traceback.print_exc()

    def serialize(self):
        return [
            [cell.serialize() for cell in row] for row in self._grid
        ]

    def get_status(self):
        status = []
        for y, row in enumerate(self._grid):
            for x, cell in enumerate(row):
                if cell.get_type() == FieldType.LETTER:

                    user_content = cell.get_user_content()
                    if cell.is_revealed():
                        status.append({
                            'x': x,
                            'y': y,
                            'revealed': cell.get_content()
                        })
                    elif len(user_content) > 0:
                        status.append({
                            'x': x,
                            'y': y,
                            'user_input': user_content
                        })
        return status

    def check_and_reveal_horizontal(self, x: int, y: int) -> list:
        # TODO: this would be much more perfomant and elegant, if every cell would hold a reference
        # to it's own word^^

        status_update = []
        cells_to_reveal = []

        x_start = x
        while (self._grid[y][x_start-1].get_type() == FieldType.LETTER):
            x_start -= 1

        x_i = x_start - 1
        while(x_i + 1 < self._width and self._grid[y][x_i+1].get_type() == FieldType.LETTER):

            x_i += 1
            cell = self._grid[y][x_i]
            if cell.get_user_content() != cell.get_content():
                return []
            cells_to_reveal.append(cell)

        if x_start - x_i == 0:
            # we have a single letter, not a word
            return []

        for i, cell in enumerate(cells_to_reveal):
            status_update.append({
                'x': x_start + i,
                'y': y,
                'revealed': cell.get_content()
            })
            cell.reveal()

        return status_update

    def check_and_reveal_vertical(self, x: int, y: int) -> list:
        # TODO: this would be much more perfomant and elegant, if every cell would hold a reference
        # to it's own word^^

        status_update = []
        cells_to_reveal = []

        y_start = y
        while (self._grid[y_start - 1][x].get_type() == FieldType.LETTER):
            y_start -= 1

        y_i = y_start - 1
        while(y_i + 1 < self._width and self._grid[y_i+1][x].get_type() == FieldType.LETTER):

            y_i += 1
            cell = self._grid[y_i][x]
            if cell.get_user_content() != cell.get_content():
                return []
            cells_to_reveal.append(cell)

        if y_start - y_i == 0:
            # we have a single letter, not a word
            return []

        for i, cell in enumerate(cells_to_reveal):
            status_update.append({
                'x': x,
                'y': y_start + i,
                'revealed': cell.get_content()
            })
            cell.reveal()

        return status_update

    def check_and_reveal_word(self, x: int, y: int):
        return self.check_and_reveal_horizontal(x, y) + self.check_and_reveal_vertival(x, y)

    def user_input(self, x: int, y: int, letter: str) -> list:
        assert len(letter) <= 1

        cell = self._grid[y][x]

        if cell.get_type() != FieldType.LETTER:
            # should not happen if the client does everything right
            logging.warning("try to modify wrong cell")
            return []

        if cell.is_revealed():
            # user tries to modify already revealed change, telling him it's already revealed ;)
            return [{
                'x': x,
                'y': y,
                'revealed': cell.get_content()
            }]

        letter = letter.lower()

        cell.user_input(letter.lower())

        revealed_changes = self.check_and_reveal_vertical(
            x, y) + self.check_and_reveal_horizontal(x, y)

        if len(revealed_changes) == 0:
            return [{
                'x': x,
                'y': y,
                'user_input': cell.get_user_content()
            }]

        return revealed_changes

    def get_solution_locations(self):
        return self._solution_locations

    def _build_grid(self):
        raw_grid, word_infos, solution_locations = crossword_generator.create_word_grid(
            self._width - 1, self._height - 1, lang_code=self._lang_code, target_density=self._density)

        self._solution_locations = solution_locations
        # fix solution locations offsets
        for i in range(len(self._solution_locations)):
            self._solution_locations[i][0] += 1
            self._solution_locations[i][1] += 1

        # note: we will append an additional row and column, to have enough space to place hint fields

        self._grid = [[Field()] * self._width]  # initialize with empty row

        for y in range(self._height - 1):
            row = [Field()]  # initialize row with empty column
            for x in range(self._width - 1):
                raw_cell = raw_grid[y, x]
                if raw_cell == " ":
                    row.append(Field())
                else:
                    row.append(LetterField(raw_cell))

            self._grid.append(row)

        # place hint fields:
        for word, info in word_infos.items():
            y, x = info.get_hint_location()
            # correct offset
            y += 1
            x += 1

            cell = self._grid[y][x]

            # check if we already have a hint here:
            if cell.get_type() == FieldType.HINT:
                if info.is_vertical():
                    cell.set_vertical_hint(info.get_hint())
                else:
                    cell.set_horizintal_hint(info.get_hint())
            elif cell.get_type() == FieldType.LETTER:
                # edge case: a word has "eaten up" another one, skipping that case
                pass

            else:
                if info.is_vertical():
                    self._grid[y][x] = HintField(vertical_hint=info.get_hint())
                else:
                    self._grid[y][x] = HintField(
                        horizontal_hint=info.get_hint())


class Crossword(object):
    def __init__(self, width: int, height: int, lang_code: str = "en"):
        self._width = width
        self._height = height
        self._grid = Grid(width, height, lang_code)

    def serialize(self):
        return {
            'w': self._width,
            'h': self._height,
            'grid': self._grid.serialize(),
            'solution': self._grid.get_solution_locations()
        }

    def user_input(self, x: int, y: int, letter: str) -> list:
        return self._grid.user_input(x=x, y=y, letter=letter)

    def get_status(self) -> list:
        return self._grid.get_status()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cw = Crossword(30, 30, "de")
    print(cw.serialize())
