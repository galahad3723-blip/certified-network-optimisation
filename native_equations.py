"""Convert TeX displays through Pandoc's native Word equation writer."""
from copy import deepcopy
from pathlib import Path
import subprocess
import zipfile
import re
from lxml import etree

MATH_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/math'


def prepare_equations(equations, destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    displays = []
    keys = []
    for key, tex in equations.items():
        tex = re.sub(r'\{\\rm ([A-Za-z]+)\}', lambda m: r'{\mathrm{'+m.group(1)+'}}', tex)
        # LibreOffice misrenders empty alignment cells in Pandoc's eqArr.
        # Separate nonempty native displays preserve every continuation row.
        if tex.startswith(r'\begin{aligned}') or tex.startswith(r'\begin{gathered}'):
            environment = 'aligned' if tex.startswith(r'\begin{aligned}') else 'gathered'
            tex = tex.removeprefix(r'\begin{'+environment+'}').removesuffix(r'\end{'+environment+'}')
            rows = [row.replace('&','').strip() for row in tex.split(r'\\')]
        else:
            rows = [tex]
        displays.extend(rows)
        keys.extend([key]*len(rows))
    markdown = '\n\n'.join('$$\n'+tex+'\n$$' for tex in displays)
    target = destination / 'native_equations.docx'
    command = ['pandoc', '-f', 'markdown+tex_math_dollars', '-t', 'docx', '-o', str(target)]
    result = subprocess.run(command, input=markdown, text=True, capture_output=True, check=True)
    if result.stderr.strip():
        raise RuntimeError('Equation conversion warning: '+result.stderr)
    with zipfile.ZipFile(target) as archive:
        root = etree.fromstring(archive.read('word/document.xml'))
    nodes = root.findall('.//{'+MATH_NS+'}oMathPara')
    for node in nodes:
        for accent in node.findall('.//{'+MATH_NS+'}acc'):
            prop = accent.find('{'+MATH_NS+'}accPr')
            char = prop.find('{'+MATH_NS+'}chr') if prop is not None else None
            if char is not None and char.get('{'+MATH_NS+'}val') == '\u203e':
                accent.tag = '{'+MATH_NS+'}bar'
                prop.tag = '{'+MATH_NS+'}barPr'
                prop.remove(char)
                position = etree.Element('{'+MATH_NS+'}pos')
                position.set('{'+MATH_NS+'}val','top')
                prop.insert(0,position)
    if len(nodes) != len(displays):
        raise ValueError(f'Expected {len(displays)} native displays, found {len(nodes)}')
    output = {key:[] for key in equations}
    for key,node in zip(keys,nodes):
        output[key].append(deepcopy(node))
    return output
