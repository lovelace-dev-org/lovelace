# -*- coding: utf-8 -*-

class Node:
    def __init__(self, data):
        self.data = data

    def __unicode__(self):
        return u"%s" % (self.data)
    def __str__(self):
        return self.__unicode__()
    def __repr__(self):
        return self.__unicode__()

class Edge:
    def __init__(self, node_from, node_to, directed=True):
        self.node_from = node_from
        self.node_to = node_to
        self.directed = directed

    def relation_symbol(self):
        if self.directed:
            return u"->"
        else:
            return u"--"

    def __unicode__(self):
        return u"%s %s %s" % (self.node_from, self.relation_symbol(), self.node_to)
    def __str__(self):
        return self.__unicode__()
    def __repr__(self):
        return self.__unicode__()    

class Graph:
    def __init__(self, nodes, edges):
        self.nodes = nodes
        self.edges = edges
        self.index = len(edges)

    def __iter__(self):
        return self

    def next(self):
        if self.index == 0:
            raise StopIteration
        self.index -= 1
        return self.edges[self.index]

if __name__ == "__main__":
    nodes = []
    edges = []
    for i in range(1, 11):
        nodes.append(Node(i))
        if len(nodes) >= 2:
            edges.append(Edge(nodes[-1], nodes[-2]))
            edges = [e for e in reversed(edges)]
            graph = Graph(nodes, edges)
    print "digraph generated {"
    for rel in graph:
        print "    %s" % (rel)
    print "}"

