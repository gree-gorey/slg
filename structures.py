# -*- coding:utf-8 -*-

import random
import codecs
import zipfile
import numpy
from scipy import stats

__author__ = 'Gree-gorey'


class Store:
    def __init__(self):
        self.min = []
        self.max = []
        self.first_list = []
        self.second_list = []
        self.nouns = []
        self.verbs = []
        self.first_list_output = []
        self.second_list_output = []
        self.minimum = None
        self.length = 0
        self.number_of_same = 0
        self.allow = True
        self.same = []
        self.statistics = None

    def read_verbs(self, f):
        for line in f:
            line = line.rstrip(u'\n').split(u'\t')
            self.verbs.append(Word())
            self.verbs[-1].name = line[0]
            self.verbs[-1].features = [float(x) for x in line[1:10:]]
            self.verbs[-1].arg = 1 if u'1' in line[10] else 0.5
            self.verbs[-1].reflexive = 1 if u'+' in line[11] else 0.5
            self.verbs[-1].instr = 1 if u'+' in line[12] else 0.5
            self.verbs[-1].name_rel = 1 if u'+' in line[13] else 0.5
            self.verbs[-1].vector = [self.verbs[-1].arg,
                                     self.verbs[-1].reflexive,
                                     self.verbs[-1].instr,
                                     self.verbs[-1].name_rel]

    def read_nouns(self, f):
        for line in f:
            line = line.rstrip(u'\n').split(u'\t')
            self.nouns.append(Word())
            self.nouns[-1].part = 1 if u'1' in line[0] else 0.5
            self.nouns[-1].name = line[1]
            self.nouns[-1].features = [float(x) for x in line[2::]]
            self.nouns[-1].vector = [self.nouns[-1].part]

    def find_min_max(self, arr):
        j = 0
        for word in arr:
            if j == 0:
                self.min += word.features
                self.max += word.features
            for i in xrange(len(word.features)):
                if word.features[i] < self.min[i]:
                    self.min[i] = word.features[i]
                if word.features[i] > self.max[i]:
                    self.max[i] = word.features[i]
            j = 1

    def normalize(self):
        self.find_min_max(self.first_list)
        self.find_min_max(self.second_list)
        for word in self.first_list:
            word.normalized_features += word.features
            for i in xrange(len(word.features)):
                word.normalized_features[i] = (word.features[i] - self.min[i]) / (self.max[i] - self.min[i])
        for word in self.second_list:
            word.normalized_features += word.features
            for i in xrange(len(word.features)):
                word.normalized_features[i] = (word.features[i] - self.min[i]) / (self.max[i] - self.min[i])

    def create_zip(self):
        with codecs.open(u'./data/list_1.csv', u'w', u'utf-8') as w:
            w.write(self.first_list_output)

        with codecs.open(u'./data/list_2.csv', u'w', u'utf-8') as w:
            w.write(self.second_list_output)

        z = zipfile.ZipFile(u'output.zip', u'w')
        z.write(u'./data/list_1.csv')
        z.write(u'./data/list_2.csv')

    def test_and_fix(self):
        for i in self.same:
            p_value_same = self.test([word.normalized_features[i] for word in self.first_list_output],
                                [word.normalized_features[i] for word in self.second_list_output])

            if p_value_same < 0.1:
                if self.equal():
                    self.first_list.append(self.first_list_output.pop(random.randint(0, len(self.first_list_output)-1)))
                    self.second_list.append(self.second_list_output.pop(random.randint(0, len(self.second_list_output)-1)))

                first_list_mean = mean([word.normalized_features[i] for word in self.first_list_output])
                second_list_mean = mean([word.normalized_features[i] for word in self.second_list_output])

                if first_list_mean > second_list_mean:
                    hhh, lll = compensate(self.first_list, self.second_list, i)
                    self.first_list_output.append(self.first_list[hhh])
                    del self.first_list[hhh]
                    self.second_list_output.append(self.second_list[lll])
                    del self.second_list[lll]
                else:
                    hhh, lll = compensate(self.second_list, self.first_list, i)
                    self.first_list_output.append(self.first_list[lll])
                    del self.first_list[lll]
                    self.second_list_output.append(self.second_list[hhh])
                    del self.second_list[hhh]

                for k in self.same:
                    p_value_same = self.test([word.normalized_features[k] for word in self.first_list_output],
                                        [word.normalized_features[k] for word in self.second_list_output])

                    if p_value_same < 0.05:
                        self.allow = False

    def create_list_from_to_choose(self, a_list):
        new_list = []
        if a_list.pos == 1:
            for verb in self.verbs:
                if is_match(a_list.vector, verb.vector):
                    new_list.append(verb)
        elif a_list.pos == 2:
            for noun in self.nouns:
                if is_match(a_list.vector, noun.vector):
                    new_list.append(noun)
        return new_list

    def setup_parameters(self, parameters):
        self.same = parameters.same
        self.number_of_same = len(self.same)
        self.length = parameters.length
        self.statistics = parameters.statistics
        # self.first_list = self.create_list_from_to_choose(parameters.first_list)
        # self.second_list = self.create_list_from_to_choose(parameters.second_list)
        # print len(self.first_list), len(self.second_list)
        self.normalize()
        for word in self.first_list:
            word.same = [word.normalized_features[i] for i in self.same]
            # word.diff = word.normalized_features[different]
        for word in self.second_list:
            word.same = [word.normalized_features[i] for i in self.same]

    def add_first(self):
        self.first_list += self.first_list_output
        self.second_list += self.second_list_output

        self.first_list_output = []
        self.second_list_output = []

        index = random.randint(0, len(self.first_list)-1)
        self.first_list_output.append(self.first_list[index])
        del self.first_list[index]

        index = random.randint(0, len(self.second_list)-1)
        self.second_list_output.append(self.second_list[index])
        del self.second_list[index]

    def add_closest(self):
        distance_for_first_list = []
        for i in xrange(self.number_of_same):
            distance_for_first_list.append(mean([word.same[i] for word in self.second_list_output]))
        minimum = self.number_of_same
        index = 0
        for i in xrange(len(self.first_list)):
            from_distance = sum([abs(self.first_list[i].same[j] - distance_for_first_list[j]) for j in xrange(self.number_of_same)])
            if from_distance < minimum:
                minimum = from_distance
                index = i
        self.first_list_output.append(self.first_list[index])
        del self.first_list[index]

        distance_for_second_list = []
        for i in xrange(self.number_of_same):
            distance_for_second_list.append(mean([word.same[i] for word in self.first_list_output]))
        minimum = self.number_of_same
        index = 0
        for i in xrange(len(self.second_list)):
            from_distance = sum([abs(self.second_list[i].same[j] - distance_for_second_list[j]) for j in xrange(self.number_of_same)])
            if from_distance < minimum:
                minimum = from_distance
                index = i
        self.second_list_output.append(self.second_list[index])
        del self.second_list[index]

    def sharp(self):
        return len(self.first_list_output) != self.length

    def less(self):
        return len(self.first_list_output) < self.length

    def equal(self):
        return len(self.first_list_output) == self.length

    def test(self, arr1, arr2):
        if self.statistics == 1:
            p_value = stats.ttest_ind(arr1, arr2)[1]
        elif self.statistics == 2:
            p_value = stats.ttest_ind(arr1, arr2, False)[1]
        elif self.statistics == 3:
            p_value = stats.mannwhitneyu(arr1, arr2)[1]
        return p_value


class Word:
    def __init__(self):
        self.name = u''
        self.features = []
        self.part = 0
        self.instr = None
        self.agr = 0
        self.reflexive = None
        self.name_rel = None
        self.normalized_features = []
        self.same = 0
        self.diff = 0
        self.distance = 1
        self.vector = []

    def __gt__(self, other):
        return self.diff > other.diff

    def __lt__(self, other):
        return self.diff < other.diff

    def __eq__(self, other):
        return self.diff == other.diff


def mean(arr):
    return sum(arr)/len(arr) if len(arr) > 0 else None


def compensate(higher, lower, i):
    lowest_from_rest = 1
    first_list_index = 0
    for j in xrange(len(higher)):
        if higher[j].normalized_features[i] < lowest_from_rest:
            lowest_from_rest = higher[j].normalized_features[i]
            first_list_index = j

    highest_from_rest = 0
    second_list_index = 0
    for j in xrange(len(lower)):
        if lower[j].normalized_features[i] > highest_from_rest:
            highest_from_rest = lower[j].normalized_features[i]
            second_list_index = j

    return first_list_index, second_list_index


def is_match(one, other):
    for item in [a*b for a, b in zip(one, other)]:
        if item != 1 and item != 0:
            return False
    return True