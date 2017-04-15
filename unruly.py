#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module: unruly.py
Author: zlamberty
Created: 2017-04-09

Description:
    Trying to automatically solve the game "unruly" from the simon tatham
    puzzle pack using pyautogui

    pyautogui docs: http://pyautogui.readthedocs.io/en/latest/cheatsheet.html

Usage:
    <usage>

"""

import argparse
import collections
import os

import pyautogui


# ----------------------------- #
#   Module Constants            #
# ----------------------------- #

HERE = os.path.dirname(os.path.realpath(__file__))
IMG = os.path.join(HERE, 'img')


# ----------------------------- #
#   game class                  #
# ----------------------------- #

class Cell(object):
    colors = ['clear', 'black', 'white']

    def __init__(self, l, t, w, h, c):
        self.left = l
        self.top = t
        self.width = w
        self.height = h
        self._color_index = Cell.colors.index(c)

    @property
    def color(self):
        return Cell.colors[self._color_index]

    @property
    def midx(self):
        return self.left + self.width * .5

    @property
    def midy(self):
        return self.top + self.height * .5

    def make(self, color):
        print('making cell {}'.format(color))
        newColorIndex = Cell.colors.index(color)
        numClicks = newColorIndex - self._color_index
        numClicks %= 3
        pyautogui.click(self.midx, self.midy, numClicks)
        self._color_index = newColorIndex


class Game(object):
    def __init__(self, files):
        self.files = files.copy()
        self.numRows = None
        self.numCols = None
        self._load_game_state()

    # init

    def _load_game_state(self):
        self.state = {}
        cells = []
        for (boxfill, filename) in self.files.items():
            for box in pyautogui.locateAllOnScreen(filename, grayscale=True):
                cells.append(box + (boxfill,))
        # measure field
        self._minx = min(l for (l, t, w, h, c) in cells)
        self._miny = min(t for (l, t, w, h, c) in cells)
        self._maxx = max(l + w for (l, t, w, h, c) in cells)
        self._maxy = max(t + h for (l, t, w, h, c) in cells)

        self._deltax = self._maxx - self._minx
        self._deltay = self._maxy - self._miny

        n = round(len(cells) ** .5)
        self.numCols = self.numCols or n
        self.numRows = self.numRows or n
        self._boxWidth = round(self._deltax / self.numRows)
        self._boxHeight = round(self._deltay / self.numCols)

        for (l, t, w, h, c) in cells:
            ix = round((l - self._minx) / self._boxWidth)
            iy = round((t - self._miny) / self._boxHeight)

            self.state[ix, iy] = Cell(l, t, w, h, c)

        self._minix = min(ix for (ix, iy) in self.state)
        self._miniy = min(iy for (ix, iy) in self.state)
        self._maxix = max(ix for (ix, iy) in self.state)
        self._maxiy = max(iy for (ix, iy) in self.state)

        self.cells = cells

    def newgame(self):
        c00 = self.state[0, 0]
        pyautogui.click(c00.midx, c00.midy)
        pyautogui.hotkey('ctrl', 'n')
        self._load_game_state()

    # solver rules
    def no_threepeats(self):
        print('no three-peats allowed')
        for (ix, iy) in self.state.keys():
            for dim in ['x', 'y']:
                try:
                    if dim == 'x':
                        cells = [self.state[ix + i, iy] for i in range(3)]
                    else:
                        cells = [self.state[ix, iy + i] for i in range(3)]

                    colors = [cell.color for cell in cells]
                    for i in range(3):
                        otherColors = {colors[(i + 1) % 3], colors[(i + 2) % 3]}
                        if colors[i] == 'clear':
                            if otherColors == {'white'}:
                                cells[i].make('black')
                            elif otherColors == {'black'}:
                                cells[i].make('white')
                except KeyError:
                    pass

    def _get_row_cols(self):
        for i in range(max(self._maxix, self._maxiy) + 1):
            for dim in ['row', 'col']:
                if dim == 'col':
                    cells = [self.state[i, iy] for iy in range(self._maxiy + 1)]
                else:
                    cells = [self.state[ix, i] for ix in range(self._maxix + 1)]

                yield cells

    def row_col_is_full(self):
        print('check for color limit in row/col')
        for rc in self._get_row_cols():
            N = len(rc) / 2
            colors = [cell.color for cell in rc]
            colorCt = collections.Counter(colors)

            topColor, topCt = colorCt.most_common(1)[0]
            if topCt == N and topColor != 'clear':
                otherColor = 'black' if topColor == 'white' else 'white'
                for cell in rc:
                    if cell.color == 'clear':
                        cell.make(otherColor)

    def no_room_left(self):
        print('only one left')
        for rc in self._get_row_cols():
            N = len(rc) / 2
            colors = [cell.color for cell in rc]
            colorCt = collections.Counter(colors)

            for color in ['black', 'white']:
                if colorCt[color] == N - 1:
                    otherColor = 'black' if color == 'white' else 'white'
                    clearInds = [i for (i, c) in enumerate(colors) if c == 'clear']

                    # basically, take turns placing the one remaining color
                    # square in all the clearInd locations. if only one such
                    # placement is possibly valid, make it
                    isInvalid = []
                    for putColorInd in clearInds:
                        newSeq = colors.copy()
                        for ci in clearInds:
                            if ci == putColorInd:
                                newSeq[ci] = color
                            else:
                                newSeq[ci] = otherColor
                        if not sequence_is_valid(newSeq):
                            isInvalid.append(putColorInd)

                    for i in isInvalid:
                        rc[i].make(otherColor)

    def apply_rules(self):
        self.no_threepeats()
        self.row_col_is_full()
        self.no_room_left()

    def solve(self, maxIters=1000):
        i = 0
        while not self.solved and i < maxIters:
            self.apply_rules()
            i += 1

    # convenience methods for accessing cells by type

    def _cells_by_color(self, colorstr):
        return [k for (k, v) in self.state.items() if v.color == colorstr]

    @property
    def whites(self):
        return self._cells_by_color('white')

    @property
    def blacks(self):
        return self._cells_by_color('black')

    @property
    def clears(self):
        return self._cells_by_color('clear')

    # check if game is solved
    @property
    def solved(self):
        return not any([cell.color == 'clear' for cell in self.state.values()])


# ----------------------------- #
#   utilities                   #
# ----------------------------- #

def sequence_is_valid(s):
    for i in range(len(s) - 2):
        if s[i] == s[i + 1] == s[i + 2]:
            return False
    return True


# ----------------------------- #
#   Main routine                #
# ----------------------------- #

def main():
    files = {
        boxfill: os.path.join(IMG, 'box_{}.png').format(boxfill)
        for boxfill in ['white', 'black', 'clear']
    }
    game = Game(files)
    game.solve()
    return game


# ----------------------------- #
#   Command line                #
# ----------------------------- #

def parse_args():
    """ Take a log file from the commmand line """
    parser = argparse.ArgumentParser()
    parser.add_argument("-x", "--xample", help="An Example", action='store_true')

    args = parser.parse_args()

    logger.debug("arguments set to {}".format(vars(args)))

    return args


if __name__ == '__main__':

    args = parse_args()

    main()
