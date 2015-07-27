# -*- encoding: utf-8 -*-

import zipfile
import json

INFO = 0
CORRECT = 1
INCORRECT = 2

command_translation_dict = {
    "doIf" : "jos x, sitten",
    "doIfElse" : "jos x, sitten –– muuten", 
    "doUntil": "toista kunnes", 
    "doRepeat": "toista n kertaa", 
    "forward:": "liiku n askelta",
    "doPlaySoundAndWait": "soita ääni loppuun",
    "nextCostume": "seuraava asuste",
    "turnRight:": "käänny myötäpäivään",
    "turnLeft:": "käänny vastapäivään",
    "mousePressed": "onko hiiren nappi painettu?",
    "changeGraphicEffect:by:": "muuta tehostetta määrällä",
    "xpos" : "x-sijainti",
    "ypos" : "y-sijainti",
    "xpos:" : "aseta x:lle arvo",
    "ypos:" : "aseta y:lle arvo",
    "getAttribute:of:" : "jonkin of jotain",
    "gotoX:y:": "mene kohtaan x y",
    "heading:": "osoita suuntaan",
    "changeXposBy:": "muuta x:n arvoa",
    "changeYposBy:": "muuta y:n arvoa",
    "lookLike:": "vaihda asusteeksi",
    "bounceOffEdge": "pomppaa reunasta",
    "touching:": "koskettaako?",
    "playDrum": "soita rumpua",
    "whenGreenFlag": "kun klikataan lippua",
    "wait:elapsed:from:": "odota kunnes",
    "setVar:to:": "aseta muuttuja arvoon",
    "doForever": "ikuisesti",
    "changeVar:by:": "muuta muuttujan arvoa",
    "lineCountOfList:": "listan pituus",
    "getLine:ofList:": "listan alkio",
    "deleteLine:ofList:": "poista listasta",
    "doAsk": "kysy ja odota",
    "append:toList:": "lisää listaan",
    "say:duration:elapsed:from:": "sano n sekunnin ajan",
    "insert:at:ofList:": "lisää kohtaan listassa",
    "randomFrom:to:": "valitse satunnaisluku väliltä",
    "list:contains:": "sisältää",
    "setGraphicEffect:to:": "aseta tehoste kohteeseen",
    "procDef": "määrittele",
    "call": "kutsu",
    "concatenate:with:": "yhdistä",
    "stringLength:": "muuttujan pituus",
}

ctr = command_translation_dict

class ProjectError(Exception):
    pass
    
class Highlight(object): 
    
    def __init__(self, span):
        self.span = span
            
def setup_output():
    pass

def output(verb, correct, data=None):    
    print(verb)
    if type(data) == list:
        for item in data:
            print(ctr.get(item, item))
    elif type(data) == str:
        print(ctr.get(data, data))
            
def open_project(zf_name):
    try:
        zf = zipfile.ZipFile(zf_name)
    except zipfile.BadZipfile:
        output("Tiedosto on väärää muotoa", INCORRECT)
        raise ProjectError
    stem = zf_name.rsplit(".", 1)[0]
    zf.extractall(path=stem)
    try:
        pf = open("%s/project.json" % stem)
    except IOError:
        output("Tiedostoa ei löytynyt", INCORRECT)
        raise ProjectError
        
    try:
        project = json.load(pf)               
    except ValueError:
        output("Tiedosto on väärää muotoa", INCORRECT)
        raise ProjectError
            
    try:
        return project["children"]
    except KeyError:
        output("Projektissa ei ole sisältöä!", INCORRECT)
        raise ProjectError



# Convenience functions:

def get_objects(project):
    """
    Turns the list of objects into a dictionary of objects. Useful when 
    checking a project with more than one object. 
    """

    objs = {}
    for obj in project:
        try:
            objs[obj["objName"]] = obj
        except KeyError:
            pass
    
    return objs
        
def get_scripts(obj):
    """
    Finds all script instances from an object and returns the script
    contents without the positional information
    """
    
    try:
        return [script[2] for script in obj["scripts"]]
    except KeyError:
        output("Koodinpätkiä ei löytynyt!", INCORRECT)
        return []
   
def get_instructions(branch, names_only=False):
    """
    Returns the list of instructions inside one branch in the script
    i.e. one loop, conditional statement or just a single block
    
    If the optional argument names_only is used, the listing will only contain 
    names of blocks in the branch.
    
    The first element in the return value is the block starter itself, i.e.
    doUntil, doRepeat, doIf etc. The remaining elements are instructions that 
    are inside the block.
    
    Note: to get further into the structure, get both the full instruction 
    listing and the names listing (calling this function once with names_only=False
    and once with True). Then find the index of your desired inner block using 
    the names only list, and call this function passing that index of the full 
    listing as the first argument. Example:
    
    full = get_instructions(branch)
    names = get_instructions(branch, True)
    idx = names.index("doRepeat")
    inner_full = get_instructions(full[idx])
    inner_names = get_instructions(full[idx], True)
    ...
    """
    
    if type(branch[-1]) != list:
        instructions = [branch]
    else:
        instructions = []
        instructions.append(branch[:-1])
        for elem in branch[-1]:
            instructions.append(elem)
            
    if names_only: 
        return [instr[0] for instr in instructions]
    else:
        return instructions

def get_inner(branch, name, names_only=False):
    match = []
    for block in branch:
        if block[0] == name:
            if name == "doIfElse":
                match.extend((block[-2], block[-1]))
            else:
                match.append(block[-1])
    
    return match
    
def get_instr(branch, name):
    match = []
    if branch is None:
        return match
    for block in branch:
        if block[0] == name:
            match.append(block[1:])
            
    return match
        
def get_names(branch):
    if branch is None:
        return []
    return [item[0] if item else "" for item in branch]
       
def get_params(branch, instr_idx):
    """
    Returns the parameters of one specific instruction within a top level branch
    """

    sub_branch = branch[instr_idx]
    return sub_branch[1:]

# Basic tests

def check_branch(branch, expected, sort_branch=False, ignore_extra={}, check_only={}, silent=False):
    """
    Compares a set of instructions within a branch to a set of expected instructions. 
    If sort_branch parameter is set, this test uses instruction names only for comparison, 
    and assumes that order of instructions doesn't matter.
    
    This also expects a branch that has a loop or a conditional statement; name of the
    loop/statement should be the first item in the list of expected items. 
    """
    
    if ignore_extra:
        branch = filter(lambda item: item not in ignore_extra, branch)
        
    if check_only:
        branch = filter(lambda item: item in check_only, branch)
    
    if sorted(branch) == sorted(expected):
        if not sort_branch and branch != expected:
            if not silent:
                output("Oikeat komennot löytyivät mutta väärässä järjestyksessä!", INCORRECT)
            return False
        if not silent:
            output("Oikeat komennot löytyivät.", CORRECT)
        return True
    else:
        exp_set = set(expected)
        found = set(branch)
        extra = found.difference(exp_set)
        missing = exp_set.difference(found)
        
        if not missing:
            if not silent:
                output("Kaikki oikeat komennot löytyivät", CORRECT)
        else:
            if not silent:
                output("Nämä komennot puuttuivat:", INCORRECT, [ctr.get(item, item) for item in list(missing)])
            return False
            
        if extra:
            if not silent:
                output("Näitä ei pitäisi olla:", INCORRECT, [ctr.get(item, item) for item in list(extra)])
        elif len(branch) < len(expected):
            if not silent:
                output("Jokin oikeista komennoista ei ole mukana tarpeeksi monta kertaa!", INCORRECT)
        else:
            if not silent:
                output("Jokin oikeista komennoista on mukana liian monta kertaa!", INCORRECT)
        return False
        
def check_branches(branch, expected, sort_branch=False, ignore_extra={}, check_only={}, silent=False):
    gen = (check_branch(branch, exp, sort_branch, ignore_extra, check_only, silent) for exp in expected)
    if any(gen):
        return True
    return False  
    
def check_instruction(instr, expected, tests=None, show_expected=True, silent=False, check_len=False):
    """
    Performs a check on a single instruction block. By default compares equality with the 
    expected block. The optional tests argument can be provided to perform custom test functions
    for each parameter (use None to compare equality). 
    
    Every None in the expected argument is treated as 'don't care', which allows you to ignore
    values of certain parameters without providing specific test functions. 
    
    The optional argument show_expected can be used to hide the correct value of a parameter 
    (it is shown by default). The optional argument silent can be used if you don't want the 
    default outputs. The optional argument check_len can be used if the instruction block
    should be exactly of same length as the expected block.
    
    returns True if the instruction is acceptable
    """
    
    result = []
    
    if check_len:
        if len(instr) > len(expected):
            if not silent:
                output("Komennossa on ylimääräisiä arvoja!", INCORRECT)
            return False
        elif len(instr) < len(expected):
            if not silent:
                output("Komennosta puuttuu arvoja!", INCORRECT)
            return False
    
    if tests:
        triplets = zip(instr, expected, tests)
        for cur, exp, test in triplets:
            if exp == None:
                result.append(True)
            elif test:
                result.append(test(cur, exp))
            else: 
                result.append(cur == exp)
    else:
        pairs = zip(instr, expected)    
        for cur, exp in pairs:
            if exp == None:
                result.append(True)
            else:
                result.append(cur == exp)
        
            
    if not result[0]:
        if not silent:
            output("Komennon arvot olivat väärin!", INCORRECT)
        return False
    else:
        if all(result):
            if not silent:
                output("Komennon arvot olivat oikein", CORRECT)
            return True
        else:
            if not silent: 
                output("Osa arvoista oli väärin", INCORRECT)
            return False
                 
def check_instructions(instr, expected, tests=None, show_expected=True, silent=False, check_len=False):
    gen = (check_instruction(instr, exp, tests, show_expected, silent, check_len) for exp in expected)
    if any(gen):
        return True
    return False                  
                    
if __name__ == "__main__":
    project = open_project("t23.sb2")
    scripts = get_scripts(project[0])
    loop = get_inner(scripts[0], "doUntil")
    print(loop)
    names = get_inner(scripts[0], "doUntil", True)
    print(names)
    cond = get_inner(loop[0], "doIfElse")
    print(cond)
    names = get_inner(loop[0], "doIfElse", True)
    print(names)
    move = get_inner(cond[0], "forward:")
    print(move)
