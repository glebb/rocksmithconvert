def shortenFolder(folder):
    if len(folder) > 25:
        folder = "... " + folder[-25:]
    return folder