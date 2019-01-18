#!/usr/bin/env python3
# coding: utf-8
from py2neo import Graph, Node, Relationship
import pandas as pd
import re
import os


class MedicalGraph:
    def __init__(self):
        cur_dir = '/'.join(os.path.abspath(__file__).split('/')[:-1])
        self.data_path = os.path.join(cur_dir, 'DATA/disease.csv')
        self.graph = Graph("http://localhost:7474", username="neo4j", password="123456789")

    def read_file(self):
        """
        读取文件，获得实体，实体关系
        :return:
        """
        # cols = ["name", "alias", "part", "age", "infection", "insurance", "department", "checklist", "symptom",
        #         "complication", "treatment", "drug", "period", "rate", "money"]
        # 实体
        diseases = []  # 疾病
        aliases = []  # 别名
        symptoms = []  # 症状
        parts = []  # 部位
        departments = []  # 科室
        complications = []  # 并发症
        drugs = []  # 药品

        # 疾病的属性：age, infection, insurance, checklist, treatment, period, rate, money
        diseases_infos = []
        # 关系
        disease_to_symptom = []  # 疾病与症状关系
        disease_to_alias = []  # 疾病与别名关系
        diseases_to_part = []  # 疾病与部位关系
        disease_to_department = []  # 疾病与科室关系
        disease_to_complication = []  # 疾病与并发症关系
        disease_to_drug = []  # 疾病与药品关系

        all_data = pd.read_csv(self.data_path, encoding='gb18030').loc[:, :].values
        for data in all_data:
            disease_dict = {}  # 疾病信息
            # 疾病
            disease = str(data[0]).replace("...", " ").strip()
            disease_dict["name"] = disease
            # 别名
            line = re.sub("[，、；,.;]", " ", str(data[1])) if str(data[1]) else "未知"
            for alias in line.strip().split():
                aliases.append(alias)
                disease_to_alias.append([disease, alias])
            # 部位
            part_list = str(data[2]).strip().split() if str(data[2]) else "未知"
            for part in part_list:
                parts.append(part)
                diseases_to_part.append([disease, part])
            # 年龄
            age = str(data[3]).strip()
            disease_dict["age"] = age
            # 传染性
            infect = str(data[4]).strip()
            disease_dict["infection"] = infect
            # 医保
            insurance = str(data[5]).strip()
            disease_dict["insurance"] = insurance
            # 科室
            department_list = str(data[6]).strip().split()
            for department in department_list:
                departments.append(department)
                disease_to_department.append([disease, department])
            # 检查项
            check = str(data[7]).strip()
            disease_dict["checklist"] = check
            # 症状
            symptom_list = str(data[8]).replace("...", " ").strip().split()[:-1]
            for symptom in symptom_list:
                symptoms.append(symptom)
                disease_to_symptom.append([disease, symptom])
            # 并发症
            complication_list = str(data[9]).strip().split()[:-1] if str(data[9]) else "未知"
            for complication in complication_list:
                complications.append(complication)
                disease_to_complication.append([disease, complication])
            # 治疗方法
            treat = str(data[10]).strip()[:-4]
            disease_dict["treatment"] = treat
            # 药品
            drug_string = str(data[11]).replace("...", " ").strip()
            for drug in drug_string.split()[:-1]:
                drugs.append(drug)
                disease_to_drug.append([disease, drug])
            # 治愈周期
            period = str(data[12]).strip()
            disease_dict["period"] = period
            # 治愈率
            rate = str(data[13]).strip()
            disease_dict["rate"] = rate
            # 费用
            money = str(data[14]).strip() if str(data[14]) else "未知"
            disease_dict["money"] = money

            diseases_infos.append(disease_dict)

        return set(diseases), set(symptoms), set(aliases), set(parts), set(departments), set(complications), \
                set(drugs), disease_to_alias, disease_to_symptom, diseases_to_part, disease_to_department, \
                disease_to_complication, disease_to_drug, diseases_infos

    def create_node(self, label, nodes):
        """
        创建节点
        :param label: 标签
        :param nodes: 节点
        :return:
        """
        count = 0
        for node_name in nodes:
            node = Node(label, name=node_name)
            self.graph.create(node)
            count += 1
            print(count, len(nodes))
        return

    def create_diseases_nodes(self, disease_info):
        """
        创建疾病节点的属性
        :param disease_info: list(Dict)
        :return:
        """
        count = 0
        for disease_dict in disease_info:
            node = Node("Disease", name=disease_dict['name'], age=disease_dict['age'],
                        infection=disease_dict['infection'], insurance=disease_dict['insurance'],
                        treatment=disease_dict['treatment'], checklist=disease_dict['checklist'],
                        period=disease_dict['period'], rate=disease_dict['rate'],
                        money=disease_dict['money'])
            self.graph.create(node)
            count += 1
            print(count)
        return

    def create_graphNodes(self):
        """
        创建知识图谱实体
        :return:
        """
        disease, symptom, alias, part, department, complication, drug, rel_alias, rel_symptom, rel_part, \
        rel_department, rel_complication, rel_drug, rel_infos = self.read_file()
        self.create_diseases_nodes(rel_infos)
        self.create_node("Symptom", symptom)
        self.create_node("Alias", alias)
        self.create_node("Part", part)
        self.create_node("Department", department)
        self.create_node("Complication", complication)
        self.create_node("Drug", drug)

        return

    def create_graphRels(self):
        disease, symptom, alias, part, department, complication, drug, rel_alias, rel_symptom, rel_part, \
        rel_department, rel_complication, rel_drug, rel_infos = self.read_file()

        self.create_relationship("Disease", "Alias", rel_alias, "ALIAS_IS", "别名")
        self.create_relationship("Disease", "Symptom", rel_symptom, "HAS_SYMPTOM", "症状")
        self.create_relationship("Disease", "Part", rel_part, "PART_IS", "发病部位")
        self.create_relationship("Disease", "Department", rel_department, "DEPARTMENT_IS", "所属科室")
        self.create_relationship("Disease", "Complication", rel_complication, "HAS_COMPLICATION", "并发症")
        self.create_relationship("Disease", "Drug", rel_drug, "HAS_DRUG", "药品")

    def create_relationship(self, start_node, end_node, edges, rel_type, rel_name):
        """
        创建实体关系边
        :param start_node:
        :param end_node:
        :param edges:
        :param rel_type:
        :param rel_name:
        :return:
        """
        count = 0
        # 去重处理
        set_edges = []
        for edge in edges:
            set_edges.append('###'.join(edge))
        all = len(set(set_edges))
        for edge in set(set_edges):
            edge = edge.split('###')
            p = edge[0]
            q = edge[1]
            query = "match(p:%s),(q:%s) where p.name='%s'and q.name='%s' create (p)-[rel:%s{name:'%s'}]->(q)" % (
                start_node, end_node, p, q, rel_type, rel_name)
            try:
                self.graph.run(query)
                count += 1
                print(rel_type, count, all)
            except Exception as e:
                print(e)
        return


if __name__ == "__main__":
    handler = MedicalGraph()
    handler.create_graphNodes()
    handler.create_graphRels()
