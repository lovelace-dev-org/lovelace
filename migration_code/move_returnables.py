for uf in uploads:
    old = uf.fileinfo.path
    ordinal = os.path.dirname(old).split("/")[-1]
    
    instance = uf.answer.instance
    if instance is None:
        islug = "removed-instance"
    else:
        islug = instance.slug

    exercise = uf.answer.exercise
    if exercise is None:
        eslug = "removed-exercise"
    else:
        eslug = exercise.slug

    new = os.path.join(
        "returnables",
        islug,
        uf.answer.user.username,
        eslug,
        ordinal,
        os.path.basename(old)
    )
    os.renames(old, os.path.join(settings.PRIVATE_STORAGE_FS_PATH, new))
    uf.fileinfo.name = new
