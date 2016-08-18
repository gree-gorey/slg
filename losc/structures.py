# -*- coding:utf-8 -*-

import os
import math
import time
import random
import codecs
import zipfile
from scipy import stats
import numpy as np
from parameters import Parameters
from word import Word

__author__ = 'gree-gorey'


class Store:
    def __init__(self):
        self.min = dict()
        self.max = dict()
        self.first_list = []
        self.second_list = []
        self.nouns = []
        self.verbs = []
        self.first_list_output = []
        self.second_list_output = []
        self.minimum = None
        self.length = 0
        self.frequency = 'off'
        self.number_of_same = 0
        self.allow = True
        self.same = []
        self.statistics = None
        self.key_for_differ_feature = ''
        self.which_higher = None
        self.p_values = []
        self.time_begin = None
        self.success = True
        self.first_list_equality_counter = dict()
        self.second_list_equality_counter = dict()
        self.should_append = dict()
        self.numeric_features = [
            "name_agreement_percent",
            "name_agreement_abs",
            "subjective_complexity",
            # "objective_complexity",
            "familiarity",
            "age",
            "imageability",
            "image_agreement",
            "frequency",
            "syllables",
            "phonemes"
        ]
        self.categorical_features = {
            "arguments": ("one", "two"),
            "reflexivity": ("on", "off"),
            "instrumentality": ("on", "off"),
            "relation": ("on", "off"),
            "part": ("first", "second")
        }
        self.len_of_numeric = len(self.numeric_features)
        self.len_of_categorical = len(self.categorical_features)
        self.parameters = Parameters()

    def generate(self):
        while self.sharp():
            # считаем сколько времени прошло и убиваем
            time_current = time.time()
            if time_current - self.time_begin > 20:
                self.success = False
                break

            # сбрасывем листы и аутпут, добавляем в аутпут по одному случайному слову
            self.add_first()

            self.allow = True

            # пока длина аутпута не превышает требуемой
            while self.allow and self.less():
                time_current = time.time()
                if time_current - self.time_begin > 20:
                    self.success = False
                    break

                # начинаем добавлять слова с ближайшими векторами
                self.add_closest()
                # как только размер листа больше 5, начинаем проверять
                if len(self.first_list_output) > 5:
                    self.test_and_fix()

    def read_verbs(self, f):
        for line in f:
            line = line.rstrip(u'\n').replace(',', '.').split(u'\t')
            self.verbs.append(Word())

            self.verbs[-1].name = line[0] + '. ' + line[1] + ' (' + line[2] + ')'

            self.verbs[-1].features['name_agreement_percent'] = float(line[3])
            self.verbs[-1].features['name_agreement_abs'] = float(line[4])
            self.verbs[-1].features['subjective_complexity'] = float(line[5])
            # self.verbs[-1].features['objective_complexity'] = None if '-' in line[6] else float(line[6])
            self.verbs[-1].features['familiarity'] = float(line[7])
            self.verbs[-1].features['age'] = float(line[8])
            self.verbs[-1].features['imageability'] = float(line[9])
            self.verbs[-1].features['image_agreement'] = float(line[10])
            self.verbs[-1].features['frequency'] = float(line[11])
            self.verbs[-1].features['syllables'] = float(line[12])
            self.verbs[-1].features['phonemes'] = float(line[13])
            self.verbs[-1].features['arguments'] = 'one' if '1' in line[14] else 'two'
            self.verbs[-1].features['reflexivity'] = 'on' if '+' in line[15] else 'off'
            self.verbs[-1].features['instrumentality'] = 'on' if '+' in line[16] else 'off'
            self.verbs[-1].features['relation'] = 'on' if '+' in line[16] else 'off'

            # логарифмируем частоту
            self.verbs[-1].log_freq = math.log(self.verbs[-1].features['frequency'] + 1, 10)

    def read_nouns(self, f):
        for line in f:
            line = line.rstrip(u'\n').replace(',', '.').split(u'\t')
            self.nouns.append(Word())

            self.nouns[-1].name = line[1]

            self.nouns[-1].features['part'] = 'first' if '1' in line[0] else 'second'
            self.nouns[-1].features['name_agreement_percent'] = float(line[2])
            self.nouns[-1].features['name_agreement_abs'] = float(line[3])
            self.nouns[-1].features['subjective_complexity'] = float(line[4])
            # self.nouns[-1].features['objective_complexity'] = None if '-' in line[5] else float(line[5])
            self.nouns[-1].features['familiarity'] = float(line[6])
            self.nouns[-1].features['age'] = float(line[7])
            self.nouns[-1].features['imageability'] = float(line[8])
            self.nouns[-1].features['image_agreement'] = float(line[9])
            self.nouns[-1].features['frequency'] = float(line[10])
            self.nouns[-1].features['syllables'] = float(line[11])
            self.nouns[-1].features['phonemes'] = float(line[12])

            # логарифмируем частоту
            self.nouns[-1].log_freq = math.log(self.nouns[-1].features['frequency'] + 1, 10)

    def create_equality_counter(self, list_parameters_from_client):
        # создаем пустой счетчик
        equality_counter = dict()

        # обходим список категориальных
        for feature in self.categorical_features:
            # если у кого-то значение 50/50
            if list_parameters_from_client['features'][feature]['value'] == 'half':
                # создаем для данного параметра ячейку с двумя значениями, равными нулю
                equality_counter[feature] = {
                    self.categorical_features[feature][0]: 0,
                    self.categorical_features[feature][1]: 0
                }

        return equality_counter

    def find_min_max(self, word_list):
        for word in word_list:
            for key in word.features:
                if type(word.features[key]) == float:
                    if word.features[key] < self.min[key]:
                        self.min[key] = word.features[key]
                    if word.features[key] > self.max[key]:
                        self.max[key] = word.features[key]

    def normalize(self):
        # копируем фичи первого слова, чтобы было с чего начать сравнивать
        self.min = self.first_list[0].features.copy()
        self.max = self.first_list[0].features.copy()

        # находим минимум и максимум для всех фич в листах
        self.find_min_max(self.first_list)
        self.find_min_max(self.second_list)

        # нормализуем
        for word in self.first_list:
            word.normalized_features = word.features.copy()
            for key in word.features:
                if type(word.features[key]) == float:
                    word.normalized_features[key] = (word.features[key] - self.min[key]) / (self.max[key] - self.min[key])
        for word in self.second_list:
            word.normalized_features = word.features.copy()
            for key in word.features:
                if type(word.features[key]) == float:
                    word.normalized_features[key] = (word.features[key] - self.min[key]) / (self.max[key] - self.min[key])

    def create_zip(self):
        # first_list_head = 'name\t' + '\t'.join(self.first_list_output[0].features.keys()) + '\r\n'
        # with codecs.open(u'list_1.tsv', u'w', u'utf-8') as w:
        #     w.write(first_list_head)
        #     for word in self.first_list_output:
        #         w.write(word.name + u'\t' + u'\t'.join([str(word.features[key]) for key in word.features]) + u'\r\n')
        #
        # second_list_head = 'name\t' + '\t'.join(self.first_list_output[0].features.keys()) + '\r\n'
        # with codecs.open(u'list_2.tsv', u'w', u'utf-8') as w:
        #     w.write(second_list_head)
        #     for word in self.second_list_output:
        #         w.write(word.name + u'\t' + u'\t'.join([str(word.features[key]) for key in word.features]) + u'\r\n')

        stat_table = self.create_final_table()

        # with codecs.open(u'statistics.tsv', u'w', u'utf-8') as w:
        #     w.write(stat_table)
        #
        # z = zipfile.ZipFile(u'results.zip', u'w')
        # z.write(u'list_1.tsv')
        # z.write(u'list_2.tsv')
        # z.write(u'statistics.tsv')
        #
        # os.remove(u'list_1.tsv')
        # os.remove(u'list_2.tsv')
        # os.remove(u'statistics.tsv')

    def create_table_per_list(self, list_output, list_name):
        table_per_list = ''

        list_features = dict()

        for feature in self.numeric_features:
            list_features[feature] = [word.features[feature] for word in list_output]

        means = [str(np.mean(list_features[feature])) for feature in self.numeric_features]

        list1_mean = list_name + '\tmean\t' + '\t'.join(means) + '\t' + '\t'.join(['None'] * self.len_of_categorical) + '\r\n'
        table_per_list += list1_mean

        mins = [str(np.min(list_features[feature])) for feature in self.numeric_features]

        list1_min = '\tmin\t' + '\t'.join(mins) + '\t' + '\t'.join(['None'] * self.len_of_categorical) + '\r\n'
        table_per_list += list1_min

        maxes = [str(np.max(list_features[feature])) for feature in self.numeric_features]

        list1_max = '\tmax\t' + '\t'.join(maxes) + '\t' + '\t'.join(['None'] * self.len_of_categorical) + '\r\n'
        table_per_list += list1_max

        sd = [str(np.std(list_features[feature])) for feature in self.numeric_features]

        list1_sd = '\tSD\t' + '\t'.join(sd) + '\t' + '\t'.join(['None'] * self.len_of_categorical) + '\r\n'
        table_per_list += list1_sd

        ratios = list()

        for feature in self.categorical_features:
            ratio = {
                self.categorical_features[feature][0]: 0,
                self.categorical_features[feature][1]: 0
            }

            for word in list_output:
                if word.features[feature] in self.categorical_features[feature]:
                    ratio[word.features[feature]] += 1
                else:
                    ratio = None
                    break

            ratios.append(ratio)

        ratio_string = ''
        for ratio in ratios:
            ratio_string += '\t'
            if ratio is None:
                ratio_string += 'None'
            else:
                for key in ratio:
                    string = key + ': ' + str(ratio[key]) + '; '
                    ratio_string += string

        print ratio_string

        list1_ratio = '\tratio\t' + '\t'.join(['None'] * self.len_of_numeric) + ratio_string + '\r\n'
        table_per_list += list1_ratio

        return table_per_list

    def create_stat_table(self):
        stat_table = ''

        test_name = 'statistics\ttest name\tMann\tStudent\r\n'
        stat_table += test_name

        # for numeric_feature in self.numeric_features:
        #     p_value = self.test([word.features[numeric_feature] for word in self.first_list_output],
        #                         [word.features[numeric_feature] for word in self.second_list_output])
        #
        #     self.p_values.append(p_value)

        return stat_table

    def create_final_table(self):
        table = ''
        header = '\t\t' + '\t'.join(self.numeric_features) + '\t' + '\t'.join(self.categorical_features) + '\r\n'
        table += header

        table += self.create_table_per_list(self.first_list_output, 'list 1')
        table += '\r\n'
        table += self.create_table_per_list(self.second_list_output, 'list 2')
        table += '\r\n'

        table += self.create_stat_table()

        return table

    def compensate(self, first_list_mean, second_list_mean, i):
        # print 777

        # если это среднее больше в первом листе
        if first_list_mean > second_list_mean:
            # оставляем только неравные параметры, остальные неважны в этой итерации
            self.set_should_append(self.first_list_equality_counter)

            if self.should_append:
                for word in self.first_list:
                    for feature in self.should_append:
                        if word.features[feature] != self.should_append[feature]:
                            word.allowed = False
            else:
                for word in self.first_list:
                    word.allowed = True

            lowest_from_rest = 1
            first_list_index = 0
            for j, word in enumerate(self.first_list):
                if word.allowed:
                    if word.normalized_features[i] < lowest_from_rest:
                        lowest_from_rest = word.normalized_features[i]
                        first_list_index = j

            # оставляем только неравные параметры, остальные неважны в этой итерации
            self.set_should_append(self.second_list_equality_counter)

            if self.should_append:
                for word in self.second_list:
                    for feature in self.should_append:
                        if word.features[feature] != self.should_append[feature]:
                            word.allowed = False
            else:
                for word in self.first_list:
                    word.allowed = True

            highest_from_rest = 0
            second_list_index = 0
            for j, word in enumerate(self.second_list):
                if word.allowed:
                    if word.normalized_features[i] > highest_from_rest:
                        highest_from_rest = word.normalized_features[i]
                        second_list_index = j

        else:
            # оставляем только неравные параметры, остальные неважны в этой итерации
            self.set_should_append(self.second_list_equality_counter)

            if self.should_append:
                for word in self.second_list:
                    for feature in self.should_append:
                        if word.features[feature] != self.should_append[feature]:
                            word.allowed = False
            else:
                for word in self.first_list:
                    word.allowed = True

            lowest_from_rest = 1
            second_list_index = 0
            for j, word in enumerate(self.second_list):
                if word.allowed:
                    if word.normalized_features[i] < lowest_from_rest:
                        lowest_from_rest = word.normalized_features[i]
                        second_list_index = j

            # оставляем только неравные параметры, остальные неважны в этой итерации
            self.set_should_append(self.first_list_equality_counter)

            if self.should_append:
                for word in self.first_list:
                    for feature in self.should_append:
                        if word.features[feature] != self.should_append[feature]:
                            word.allowed = False
            else:
                for word in self.first_list:
                    word.allowed = True

            highest_from_rest = 0
            first_list_index = 0
            for j, word in enumerate(self.first_list):
                if word.allowed:
                    if word.normalized_features[i] > highest_from_rest:
                        highest_from_rest = word.normalized_features[i]
                        first_list_index = j

        self.first_list_output.append(self.first_list[first_list_index])
        del self.first_list[first_list_index]
        self.second_list_output.append(self.second_list[second_list_index])
        del self.second_list[second_list_index]

    def test_and_fix(self):
        for i in self.same:
            p_value_same = self.test([word.normalized_features[i] for word in self.first_list_output],
                                     [word.normalized_features[i] for word in self.second_list_output])

            # if p_value_same < 0.2:
            if p_value_same < self.parameters.alpha * 4:
                # while p_value_same < 0.06:

                # если листы достигли нужной пользователю длины
                if self.equal():
                    # print 888

                    # возвращаем по одному слову из аутпута в общий лист
                    first_list_to_pop = self.first_list_output.pop(random.randint(0, len(self.first_list_output)-1))
                    second_list_to_pop = self.second_list_output.pop(random.randint(0, len(self.second_list_output)-1))

                    self.first_list.append(first_list_to_pop)
                    self.second_list.append(second_list_to_pop)

                # по всем словам в аутпуте считаем среднее параметра i
                first_list_mean = mean([word.normalized_features[i] for word in self.first_list_output])
                second_list_mean = mean([word.normalized_features[i] for word in self.second_list_output])

                self.compensate(first_list_mean, second_list_mean, i)

            p_value_same = self.test([word.normalized_features[i] for word in self.first_list_output],
                                     [word.normalized_features[i] for word in self.second_list_output])

            # if p_value_same < 0.15:
            if p_value_same < self.parameters.alpha * 3:
                self.allow = False

    def high_low(self, high, low):
        high_sorted = sorted(high, reverse=True)
        low_sorted = sorted(low, reverse=False)
        stop = min(len(high_sorted), len(low_sorted))
        high_stop = high_sorted[0]
        low_stop = low_sorted[0]
        i = 0
        high = []
        low = []
        while high_stop > low_stop and stop > i:
            high.append(high_sorted[i])
            low.append(low_sorted[i])
            high_stop = high_sorted[i]
            low_stop = low_sorted[i]
            i += 1
        return high, low

    def differentiate(self):
        for word in self.first_list:
            word.value_of_differ_feature = word.normalized_features[self.key_for_differ_feature]
        for word in self.second_list:
            word.value_of_differ_feature = word.normalized_features[self.key_for_differ_feature]
        if self.which_higher == 'first':
            self.first_list, self.second_list = self.high_low(self.first_list, self.second_list)
        elif self.which_higher == 'second':
            self.second_list, self.first_list = self.high_low(self.second_list, self.first_list)

    def create_list_from_to_choose(self, parameters_for_one_list):
        filtered_list = []
        if parameters_for_one_list['pos'] == 'verb':
            parameters_for_one_list['features']['part']['matters'] = False

            for verb in self.verbs:
                if is_match(verb, parameters_for_one_list):
                    filtered_list.append(verb)

        elif parameters_for_one_list['pos'] == 'noun':
            parameters_for_one_list['features']['arguments']['matters'] = False
            parameters_for_one_list['features']['reflexivity']['matters'] = False
            parameters_for_one_list['features']['instrumentality']['matters'] = False
            parameters_for_one_list['features']['relation']['matters'] = False

            for noun in self.nouns:
                if is_match(noun, parameters_for_one_list):
                    filtered_list.append(noun)

        return filtered_list

    def split(self):
        if self.first_list == self.second_list:
            new = []
            new += self.first_list
            random.shuffle(new)
            self.first_list = []
            self.first_list += new[:len(new)/2]
            self.second_list = []
            self.second_list += new[len(new)/2:]

    def setup_parameters(self):
        if self.parameters.bonferroni != 'off':
            self.parameters.calculate_alpha()

        self.same = self.parameters.same
        self.number_of_same = len(self.same)
        self.length = self.parameters.length
        self.statistics = self.parameters.statistics
        self.frequency = self.parameters.frequency
        for word in self.first_list:
            # это массив из значений фич, которые не должны отличаться
            word.same = [word.normalized_features[key] for key in self.same]
        for word in self.second_list:
            word.same = [word.normalized_features[key] for key in self.same]

        if self.frequency == 'on':
            self.change_frequency()

    def change_frequency(self):
        for word in self.first_list:
            word.features['frequency'] = word.log_freq
        for word in self.second_list:
            word.features['frequency'] = word.log_freq

    def add_first(self):
        self.first_list += self.first_list_output
        self.second_list += self.second_list_output

        self.first_list_output = []
        self.second_list_output = []

        # вытаскиваем случайное слово из листа
        index = random.randint(0, len(self.first_list)-1)

        word = self.first_list[index]

        # прибавляем параметры добавленного слова в счетчик
        for feature in self.first_list_equality_counter:
            # если значение этого параметра есть среди значений в счетчике, то плюс 1
            if word.features[feature] in self.first_list_equality_counter[feature]:
                self.first_list_equality_counter[feature][word.features[feature]] += 1

        self.first_list_output.append(word)
        del self.first_list[index]

        # вытаскиваем случайное слово из листа
        index = random.randint(0, len(self.second_list)-1)

        word = self.second_list[index]

        # прибавляем параметры добавленного слова в счетчик
        for feature in self.second_list_equality_counter:
            # если значение этого параметра есть среди значений в счетчике, то плюс 1
            if word.features[feature] in self.second_list_equality_counter[feature]:
                self.second_list_equality_counter[feature][word.features[feature]] += 1

        self.second_list_output.append(word)
        del self.second_list[index]

    def set_should_append(self, list_equality_counter):
        self.should_append = dict()
        for feature in list_equality_counter:
            keys = list_equality_counter[feature].keys()
            if list_equality_counter[feature][keys[0]] < list_equality_counter[feature][keys[1]]:
                self.should_append[feature] = keys[0]
            elif list_equality_counter[feature][keys[0]] > list_equality_counter[feature][keys[1]]:
                self.should_append[feature] = keys[1]

    def add_closest(self):
        # оставляем только неравные параметры, остальные неважны в этой итерации
        self.set_should_append(self.first_list_equality_counter)

        # print self.first_list_equality_counter
        # print self.should_append

        if self.should_append:
            for word in self.first_list:
                for feature in self.should_append:
                    if word.features[feature] != self.should_append[feature]:
                        word.allowed = False
        else:
            for word in self.first_list:
                word.allowed = True

        # вектор расстояния до другого листа
        distance_for_first_list = []
        for i in xrange(self.number_of_same):
            # длина этого массива равна длине массива одинаковых фич
            # значения -- это среднее значение фичи по всем словам второго листа
            distance_for_first_list.append(mean([word.same[i] for word in self.second_list_output]))

        # index_changed = False

        # allowed = 0
        #
        # for word in self.first_list:
        #     if word.allowed:
        #         allowed += 1
        #
        # print allowed

        index = 0
        for i, word in enumerate(self.first_list):
            if word.allowed:
                index = i
                # index_changed = True
                break

        # задираем максимальо минимум (максимальное значение это длина массива одинаковых фич,
        # т.к. все они максимум по 1
        minimum = self.number_of_same
        # обходим первый лист и ищем слово с ближайшим вектором
        for i in xrange(len(self.first_list)):
            if self.first_list[i].allowed:
                # считаем расстояние (Эвклидово??) от текущего слова до "среднего" вектора второго листа
                from_distance = sum([abs(self.first_list[i].same[j] - distance_for_first_list[j]) for j in xrange(self.number_of_same)])
                # находим среди всех минимум и запоминаем индекс
                if from_distance < minimum:
                    minimum = from_distance
                    index = i

        word = self.first_list[index]

        # if self.should_append:
        #     for feature in self.should_append:
        #         if word.features[feature] != self.should_append[feature]:
        #             print index_changed

        # добавляем найденное слово в аутпут и удаляем из листа
        self.first_list_output.append(word)

        # прибавляем параметры добавленного слова в счетчик
        for feature in self.first_list_equality_counter:
            # если значение этого параметра есть среди значений в счетчике, то плюс 1
            if word.features[feature] in self.first_list_equality_counter[feature]:
                # print word.features[feature]
                self.first_list_equality_counter[feature][word.features[feature]] += 1

        del self.first_list[index]

        # оставляем только неравные параметры, остальные неважны в этой итерации
        self.set_should_append(self.second_list_equality_counter)

        if self.should_append:
            for word in self.second_list:
                for feature in self.should_append:
                    if word.features[feature] != self.should_append[feature]:
                        word.allowed = False
        else:
            for word in self.second_list:
                word.allowed = True

        index = 0
        for i, word in enumerate(self.second_list):
            if word.allowed:
                index = i
                break

        # повторяем те же действия для второго листа
        distance_for_second_list = []
        for i in xrange(self.number_of_same):
            distance_for_second_list.append(mean([word.same[i] for word in self.first_list_output]))
        minimum = self.number_of_same + 1
        for i in xrange(len(self.second_list)):
            if self.second_list[i].allowed:
                from_distance = sum([abs(self.second_list[i].same[j] - distance_for_second_list[j]) for j in xrange(self.number_of_same)])
                if from_distance < minimum:
                    minimum = from_distance
                    index = i

        word = self.second_list[index]

        # добавляем найденное слово в аутпут и удаляем из листа
        self.second_list_output.append(word)

        # прибавляем параметры добавленного слова в счетчик
        for feature in self.second_list_equality_counter:
            # если значение этого параметра есть среди значений в счетчике, то плюс 1
            if word.features[feature] in self.second_list_equality_counter[feature]:
                self.second_list_equality_counter[feature][word.features[feature]] += 1

        del self.second_list[index]

    def sharp(self):
        return len(self.first_list_output) != self.length

    def less(self):
        return len(self.first_list_output) < self.length

    def equal(self):
        return len(self.first_list_output) == self.length

    def test(self, arr1, arr2):
        p_value = 0
        if self.statistics == 'auto':
            # проверяем Левеном на равенство дисперсий. Если равны
            if stats.levene(arr1, arr2)[1] > 0.05:
                # Шапир на нормальность выборок. Если нормальные
                if stats.shapiro(arr1)[1] > 0.05 and stats.shapiro(arr2)[1] > 0.05:
                    # p = Student
                    p_value = stats.ttest_ind(arr1, arr2)[1]
                else:
                    # p = Mann
                    if equal(arr1, arr2):
                        p_value = 1
                    else:
                        p_value = stats.mannwhitneyu(arr1, arr2)[1]
            else:
                p_value = stats.ttest_ind(arr1, arr2, False)[1]

        elif self.statistics == 'student':
            p_value = stats.ttest_ind(arr1, arr2)[1]
        elif self.statistics == 'welch':
            p_value = stats.ttest_ind(arr1, arr2, False)[1]
        elif self.statistics == 'mann':
            if equal(arr1, arr2):
                p_value = 1
            else:
                p_value = stats.mannwhitneyu(arr1, arr2)[1]
        return p_value


def equal(arr1, arr2):
    ref = arr1[0]
    for el in arr1[2:] + arr2:
        if el != ref:
            return False
    return True


def mean(arr):
    # vector_without_none = []
    # for value in arr:
    #     if value is not None:
    #         vector_without_none.append(value)
    return sum(arr)/len(arr) if len(arr) > 0 else None


def is_match(database_word, client_word_parameters):
    for feature in client_word_parameters['features']:

        # Берем только те, которые нам важны
        if client_word_parameters['features'][feature]['matters']:

            # если это категориальная фича, просто сравниваем значение
            if client_word_parameters['features'][feature]['categorical']:
                if client_word_parameters['features'][feature]['value'] != database_word.features[feature]:
                    return False

            # если это континуальная фича, то должна попадать в диапазон
            else:
                # print client_word_parameters['features'][feature]['value']
                # print database_word.features[feature]
                # print float(client_word_parameters['features'][feature]['value'][0]) <= database_word.features[feature] <= float(client_word_parameters['features'][feature]['value'][1])

                if not client_word_parameters['features'][feature]['value'][0]:
                    client_word_parameters['features'][feature]['value'][0] = -float('inf')
                if not client_word_parameters['features'][feature]['value'][1]:
                    client_word_parameters['features'][feature]['value'][1] = float('inf')

                if not float(client_word_parameters['features'][feature]['value'][0]) <= database_word.features[feature] <= float(client_word_parameters['features'][feature]['value'][1]):
                    return False
    return True