#!/usr/bin/env python3
# coding: utf-8
import os
import ahocorasick


class EntityExtractor:
    def __init__(self):
        cur_dir = '/'.join(os.path.abspath(__file__).split('/')[:-1])
        # 路径
        self.vocab_path = os.path.join(cur_dir, 'DATA/vocab.txt')
        self.stopwords_path = os.path.join(cur_dir, 'DATA/stop_words.utf8')
        self.word2vec_path = os.path.join(cur_dir, 'DATA/merge_sgns_bigram_char300.txt')
        self.stopwords = [w.strip() for w in open(self.stopwords_path, 'r', encoding='utf8') if w.strip()]

        self.disease_path = os.path.join(cur_dir, 'DATA/disease_vocab.txt')
        self.symptom_path = os.path.join(cur_dir, 'DATA/symptom_vocab.txt')
        self.alias_path = os.path.join(cur_dir, 'DATA/alias_vocab.txt')
        self.complication_path = os.path.join(cur_dir, 'DATA/complications_vocab.txt')

        self.disease_entities = [w.strip() for w in open(self.disease_path, encoding='utf8') if w.strip()]
        self.symptom_entities = [w.strip() for w in open(self.symptom_path, encoding='utf8') if w.strip()]
        self.alias_entities = [w.strip() for w in open(self.alias_path, encoding='utf8') if w.strip()]
        self.complication_entities = [w.strip() for w in open(self.complication_path, encoding='utf8') if w.strip()]

        self.region_words = list(set(self.disease_entities+self.alias_entities+self.symptom_entities))

        # 构造领域actree
        self.disease_tree = self.build_actree(list(set(self.disease_entities)))
        self.alias_tree = self.build_actree(list(set(self.alias_entities)))
        self.symptom_tree = self.build_actree(list(set(self.symptom_entities)))
        self.complication_tree = self.build_actree(list(set(self.complication_entities)))

        self.symptom_qwds = ['症状', '表征', '现象', '症候', '表现', '行为', '状况']  # 询问症状
        self.cureway_qwds = ['药', '药品', '用药', '胶囊', '口服液', '炎片', '吃什么药', '用什么药', '怎么办',
                             '买什么药', '怎么治疗', '如何医治', '怎么医治', '怎么治', '怎么医', '如何治',
                             '医治方式', '疗法', '咋治', '咋办', '咋治']  # 询问治疗方法
        self.lasttime_qwds = ['周期', '多久', '多长时间', '多少时间', '几天', '几年', '多少天', '多少小时',
                              '几个小时', '多少年', '多久能好', '痊愈', '康复']  # 询问治疗周期
        self.cureprob_qwds = ['多大概率能治好', '多大几率能治好', '治好希望大么', '几率', '几成', '比例',
                              '可能性', '能治', '可治', '可以治', '可以医', '能治好吗', '可以治好吗']  # 询问治愈率
        self.check_qwds = ['检查', '检查项目', '查出', '项目', '测出', '试出', '查看', '化验', '体检']  # 询问检查项目
        self.belong_qwds = ['属于什么科', '属于', '什么科', '科室', '挂', '挂哪个', '哪个科', '科']  # 询问科室
        self.disase_qwds = ['什么病', '啥病', '得了什么', '得了哪种', '怎么回事', '咋回事', '回事',
                            '什么情况', '情况', '问题',' 什么问题', '毛病', '什么毛病', '啥毛病']  # 询问疾病

    def build_actree(self, wordlist):
        """
        构造actree，加速过滤
        :param wordlist:
        :return:
        """
        actree = ahocorasick.Automaton()
        # 向树中添加单词
        for index, word in enumerate(wordlist):
            actree.add_word(word, (index, word))
        actree.make_automaton()
        return actree

    def entity_reg(self, question):
        """
        模式匹配, 得到匹配的词和类型。如疾病，疾病别名，并发症，症状
        :param question:str
        :return:
        """
        self.result = {}

        for i in self.disease_tree.iter(question):
            word = i[1][1]
            if "Disease" not in self.result:
                self.result["Disease"] = [word]
            else:
                self.result["Disease"].append(word)

        for i in self.alias_tree.iter(question):
            word = i[1][1]
            if "Alias" not in self.result:
                self.result["Alias"] = [word]
            else:
                self.result["Alias"].append(word)

        for i in self.symptom_tree.iter(question):
            wd = i[1][1]
            if "Symptom" not in self.result:
                self.result["Symptom"] = [wd]
            else:
                self.result["Symptom"].append(wd)

        for i in self.complication_tree.iter(question):
            wd = i[1][1]
            if "Complication" not in self.result:
                self.result["Complication"] = [wd]
            else:
                self.result["Complication"] .append(wd)

        return self.result

    def find_sim_words(self, question):
        """
        当全匹配失败时，就采用相似度计算来找相似的词
        :param question:
        :return:
        """
        import re
        import string
        import jieba
        from gensim.models.word2vec import KeyedVectors

        jieba.load_userdict(self.vocab_path)
        self.model = KeyedVectors.load_word2vec_format(self.word2vec_path, binary=False)

        sentence = re.sub("[{}]", re.escape(string.punctuation), question)
        sentence = re.sub("[，。‘’；：？、！【】]", " ", sentence)
        sentence = sentence.strip()

        words = [w.strip() for w in jieba.cut(sentence) if w.strip() not in self.stopwords and len(w.strip()) >= 2]

        alist = []

        for word in words:
            temp = [self.disease_entities, self.alias_entities, self.symptom_entities, self.complication_entities]
            for i in range(len(temp)):
                flag = ''
                if i == 0:
                    flag = "Disease"
                elif i == 1:
                    flag = "Alias"
                elif i == 2:
                    flag = "Symptom"
                else:
                    flag = "Complication"
                scores = self.simCal(word, temp[i], flag)
                alist.extend(scores)
        temp = sorted(alist, key=lambda k: k[1], reverse=True)

        self.result[temp[0][2]] = [temp[0][0]]

        #return self.result

    def simCal(self, word, entities, flag):
        """
        计算词语和字典中的词的相似度
        相同字符的个数/min(|A|,|B|)   +  余弦相似度
        :param word: str
        :param entities:List
        :return:
        """
        a = len(word)

        scores = []
        for entity in entities:
            sim_num = 0
            b = len(entity)
            for w in word:
                if w in entity:
                    sim_num += 1
            if sim_num != 0:
                score1 = sim_num / min(a, b)
            else:
                score1 = 0
            try:
                score2 = self.model.similarity(word, entity)
            except:
                score2 = 0
            if score1 and score2:
                score = (score1 + score2) / 2
                if score >= 0.6:
                    scores.append((entity, score, flag))

        scores.sort(key=lambda k: k[1], reverse=True)
        return scores

    def check_words(self, wds, sent):
        """
        基于特征词分类
        :param wds:
        :param sent:
        :return:
        """
        for wd in wds:
            if wd in sent:
                return True
        return False

    # 实体抽取主函数
    def extractor(self, question):
        self.entity_reg(question)
        if not self.result:
            self.find_sim_words(question)

        types = []  # 实体类型
        for v in self.result.keys():
            types.append(v)

        intentions = []  # 查询意图
        #intention = ''

        # 已知疾病，查询症状
        if self.check_words(self.symptom_qwds, question) and ('Disease' in types or 'Alia' in types):
            intention = "query_symptom"
            intentions.append(intention)
        # 已知疾病或症状，查询治疗方法
        if self.check_words(self.cureway_qwds, question) and \
                ('Disease' in types or 'Symptom' in types or 'Alias' in types or 'Complication' in types):
            intention = "query_cureway"
            intentions.append(intention)
        # 已知疾病或症状，查询治疗周期
        if self.check_words(self.lasttime_qwds, question) and \
                ('Disease' in types or 'Symptom' in types or 'Alia' in types or 'Complication' in types):
            intention = "query_period"
            intentions.append(intention)
        # 已知疾病或症状，查询治愈率
        if self.check_words(self.cureprob_qwds, question) and \
                ('Disease' in types or 'Symptom' in types or 'Alias' in types or 'Complication' in types):
            intention = "query_rate"
            intentions.append(intention)
        # 已知疾病或症状，查询检查项目
        if self.check_words(self.check_qwds, question) and \
                ('Disease' in types or 'Symptom' in types or 'Alias' in types or 'Complication' in types):
            intention = "query_checklist"
            intentions.append(intention)
        # 查询科室
        if self.check_words(self.belong_qwds, question) and \
                ('Disease' in types or 'Symptom' in types or 'Alias' in types or 'Complication' in types):
            intention = "query_department"
            intentions.append(intention)
        # 已知症状，查询疾病
        if self.check_words(self.disase_qwds, question) and ("Symptom" in types or "Complication" in types):
            intention = "query_disease"
            intentions.append(intention)

        # 若没有检测到意图，且已知疾病，则返回疾病的描述
        if not intentions and ('Disease' in types or 'Alias' in types or "Symptom" in types
                               or "Complication" in types):
            intention = "disease_describe"
            intentions.append(intention)

        self.result["intentions"] = intentions

        return self.result


# if __name__ == "__main__":
#     handler = EntityExtractor()
#     res = handler.entity_reg("肚子一直痛该怎么办")
#     if not res:
#         res = handler.find_sim_words("肚子一直痛该怎么办")
#     print(res)
