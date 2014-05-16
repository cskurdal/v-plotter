__author__ = 'caleb'
#!/usr/bin/python

import xml.etree.ElementTree as ET

class VPlotterSVG:

    def __init__(self, file_xml = 'svg.xml'):
        tree = ET.parse(file_xml)
        self._root = tree.getroot()

        for child in root:
            print child.tag, child.attrib

    def get_c(self):
        try:
            self._root.find('c')
        except Exception:
            return -1

    def get_path(self):
        path = []
        try:
            for line in self._root.findall('line'):
                path.append([line.x1, line.y1], [line.x2, line.y2])
        except Exception:
            path = []

        return path