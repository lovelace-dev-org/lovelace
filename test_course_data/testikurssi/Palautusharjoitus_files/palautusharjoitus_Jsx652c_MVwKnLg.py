# -*- encoding: utf-8 -*-

import scratch_core as core
import sys

try:
    project = core.open_project(sys.argv[1])
except core.ProjectError:
    pass
else:
    core.output("Projektin palautus onnistui!", core.CORRECT)
    core.output("Tutkitaan ohjelmaa...", core.INFO)
    core.output("Projektin palautus onnistui!", core.CORRECT)
    core.output("Tutkitaan ohjelmaa...", core.INFO)
    objects = core.get_objects(project)
    core.output("Tutkitaan löytyykö kissahahmoa...", core.INFO)
    try:
        sprite = objects["Sprite1"]
        core.output("Löytyi!", core.CORRECT)
    except:
        core.output("Ei löytynyt! Kissahahmon nimi pitäisi olla Sprite1!", core.INCORRECT)
        sys.exit()
    scripts = core.get_scripts(sprite)
    
    if len(scripts) == 1:
        if not core.check_branch(core.get_names(scripts[0]), ["doRepeat"]):
            sys.exit()
    
        loops = core.get_inner(scripts[0], "doRepeat")
        if len(loops) == 1:
            core.output("Tutkitaan toista n kertaa -rakennetta...", core.INFO)
            core.output("Tutkitaan toistorakenteen komentoja...", core.INFO)
            if not core.check_branch(core.get_names(loops[0]), ["forward:", "doPlaySoundAndWait", "nextCostume"]):
                sys.exit()
            core.output("Tarkistetaan, onko toistojen määrä oikein...", core.INFO)
            
            loop = core.get_instr(scripts[0], "doRepeat")
            core.check_instruction(loop[0], [8], show_expected=False)
    elif len(scripts) > 1:
        core.output("Ohjelmassasi on liian monta koodinpätkää! Yksi riittää!", core.INCORRECT)
        